"""Basic Stage A simulation runner."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
import csv

from convoysim.braking import BrakingDistanceTable, BrakingType
from convoysim.leader_profile import LeaderProfile
from convoysim.models import InitialConditions, SimulationParameters
from convoysim.parameters import load_parameters_csv
from convoysim.physics import MotionState, step_motion
from convoysim.scenario_timeline import ImageEvent, ScenarioTimeline
from convoysim.units import kph_to_mps, mps_to_kph, ms_to_seconds
from convoysim.validation import validate_initial_conditions, validate_leader_profile, validate_parameters


class FollowerState(StrEnum):
    STOPPED_WAITING = "STOPPED_WAITING"
    START_DELAY_COUNTING = "START_DELAY_COUNTING"
    FOLLOWING_ACCELERATING = "FOLLOWING_ACCELERATING"
    FOLLOWING_MATCHING_SPEED = "FOLLOWING_MATCHING_SPEED"
    FOLLOWING_ORANGE_DECEL = "FOLLOWING_ORANGE_DECEL"
    FOLLOWING_RED_BRAKING_TO_STOP = "FOLLOWING_RED_BRAKING_TO_STOP"
    TRACKING_LOST_TO_LAST_POSITION = "TRACKING_LOST_TO_LAST_POSITION"
    TRACKING_RESUME_PENDING = "TRACKING_RESUME_PENDING"
    COMMUNICATION_REQUEST_STOP = "COMMUNICATION_REQUEST_STOP"
    FORT_EMERGENCY_DECEL = "FORT_EMERGENCY_DECEL"
    IMMEDIATE_STOP_AFTER_LOSS_TIMEOUT = "IMMEDIATE_STOP_AFTER_LOSS_TIMEOUT"
    SAFETY_LOCK = "SAFETY_LOCK"


@dataclass(frozen=True)
class TruckSnapshot:
    time_s: float
    position_m: float
    velocity_mps: float


@dataclass(frozen=True)
class TruckCommand:
    state: FollowerState
    acceleration_mps2: float
    command: str


@dataclass(frozen=True)
class CommunicationDirective:
    leader_stop_requested: bool = False
    truck2_stop_requested: bool = False
    message: str = ""
    status: str = "Disabled"


@dataclass(frozen=True)
class SimulationLogRow:
    time_s: float
    severity: str
    event: str
    message: str


@dataclass
class SimulationLogContext:
    rows: list[SimulationLogRow]
    braking_fallback_keys: set[tuple[str, str]]

    def add(self, time_s: float, severity: str, event: str, message: str) -> None:
        self.rows.append(SimulationLogRow(time_s=time_s, severity=severity, event=event, message=message))


@dataclass(frozen=True)
class FollowerControl:
    state: FollowerState = FollowerState.STOPPED_WAITING
    tracking: bool = True
    red_braking_to_stop: bool = False
    start_delay_started_at_s: float | None = None
    loss_started_at_s: float | None = None
    earliest_resume_at_s: float | None = None
    frozen_target_front_m: float | None = None
    stopped_at_loss_target_since_s: float | None = None
    stop_reason: str = ""
    loss_source: str = ""
    orange_target_velocity_mps: float | None = None
    initial_movement_started: bool = False
    fort_activated: bool = False
    resume_from_stop_blocked: bool = False


@dataclass(frozen=True)
class SimulationRow:
    time_s: float
    truck1_position_m: float
    truck2_position_m: float
    truck3_position_m: float
    truck2_gap_m: float
    truck3_gap_m: float
    gap2_violation: bool
    gap3_violation: bool
    truck1_velocity_kph: float
    truck2_velocity_kph: float
    truck3_velocity_kph: float
    truck1_acceleration_mps2: float
    truck2_acceleration_mps2: float
    truck3_acceleration_mps2: float
    truck2_state: str
    truck3_state: str
    truck2_command: str
    truck3_command: str
    truck2_actual_gap_m: float
    truck2_measured_gap_m: float
    truck3_actual_gap_m: float
    truck3_measured_gap_m: float
    truck2_tracking_status: str
    truck3_tracking_status: str
    truck2_relative_velocity_kph: float
    truck3_relative_velocity_kph: float
    communication_message: str
    communication_status: str
    violation_type_truck2: str
    violation_type_truck3: str
    stop_reason_truck2: str
    stop_reason_truck3: str
    truck1_state: str = ""
    truck1_command: str = ""
    truck2_loss_source: str = ""
    truck3_loss_source: str = ""
    truck2_loss_target_rear_m: float | None = None
    truck3_loss_target_rear_m: float | None = None
    truck2_orange_trigger_gap_m: float = 0.0
    truck3_orange_trigger_gap_m: float = 0.0
    orange_braking_mode: int = 0


@dataclass(frozen=True)
class SimulationResult:
    rows: tuple[SimulationRow, ...]
    logs: tuple[SimulationLogRow, ...] = ()

    def write_csv(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(_OUTPUT_COLUMNS))
            writer.writeheader()
            for row in self.rows:
                writer.writerow(_row_to_csv(row))

    def write_log_csv(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=["Time_s", "Severity", "Event", "Message"])
            writer.writeheader()
            for row in self.logs:
                writer.writerow(
                    {
                        "Time_s": f"{row.time_s:.3f}",
                        "Severity": row.severity,
                        "Event": row.event,
                        "Message": row.message,
                    }
                )


def run_basic_simulation(
    initial: InitialConditions,
    parameters: SimulationParameters,
    timeline: ScenarioTimeline,
    braking_table: BrakingDistanceTable | None = None,
) -> SimulationResult:
    _raise_if_invalid(initial, parameters, timeline.leader_profile())

    dt_s = parameters.simulation_time_step_s
    output_resolution_s = parameters.output_resolution_s
    truck1_front_m, truck2_front_m, truck3_front_m = initial.initial_front_positions()
    truck1 = MotionState(position_m=truck1_front_m, velocity_mps=kph_to_mps(initial.truck1_velocity_kph))
    truck2 = MotionState(position_m=truck2_front_m, velocity_mps=kph_to_mps(initial.truck2_velocity_kph))
    truck3 = MotionState(position_m=truck3_front_m, velocity_mps=kph_to_mps(initial.truck3_velocity_kph))
    control2 = FollowerControl(initial_movement_started=truck2.velocity_mps > 1e-9)
    control3 = FollowerControl(initial_movement_started=truck3.velocity_mps > 1e-9)
    profile = timeline.leader_profile()
    truck1_events = {event.time_s: event.event for event in timeline.truck1_events()}
    truck2_events = {event.time_s: event.event for event in timeline.truck2_image_events()}
    truck3_events = {event.time_s: event.event for event in timeline.truck3_image_events()}
    history1 = [TruckSnapshot(0.0, truck1.position_m, truck1.velocity_mps)]
    history2 = [TruckSnapshot(0.0, truck2.position_m, truck2.velocity_mps)]
    history3 = [TruckSnapshot(0.0, truck3.position_m, truck3.velocity_mps)]
    rows: list[SimulationRow] = []
    log_context = SimulationLogContext(rows=[], braking_fallback_keys=set())
    truck1_fort_latched = False  # Once FORT activates it never releases; truck brakes to stop and holds

    time_s = 0.0
    output_index = 0
    communication = _communication_directive(parameters, control2, control3, time_s)
    while time_s <= timeline.end_time_s + 1e-9:
        if _is_output_time(time_s, output_resolution_s, output_index):
            delayed_time_s = max(0.0, time_s - ms_to_seconds(parameters.distance_identification_delay_ms))
            delayed1 = _snapshot_at(history1, delayed_time_s)
            delayed2 = _snapshot_at(history2, delayed_time_s)
            delayed3 = _snapshot_at(history3, delayed_time_s)
            rows.append(
                _build_output_row(
                    time_s,
                    truck1,
                    truck2,
                    truck3,
                    acceleration1_mps2=0.0,
                    acceleration2_mps2=0.0,
                    acceleration3_mps2=0.0,
                    control2=control2,
                    control3=control3,
                    command2="",
                    command3="",
                    delayed1=delayed1,
                    delayed2=delayed2,
                    delayed3=delayed3,
                    communication=communication,
                    parameters=parameters,
                    truck_length_m=initial.truck_length_m,
                    truck1_in_fort=False,
                )
            )
            output_index += 1

        if time_s >= timeline.end_time_s:
            break

        next_time_s = min(time_s + dt_s, timeline.end_time_s)
        step_s = next_time_s - time_s
        control2 = _apply_image_event(
            control2,
            truck2_events.get(round(next_time_s, 10)),
            "Truck2",
            next_time_s,
            truck1.position_m,
            truck2.velocity_mps,
            log_context,
        )
        control3 = _apply_image_event(
            control3,
            truck3_events.get(round(next_time_s, 10)),
            "Truck3",
            next_time_s,
            truck2.position_m,
            truck3.velocity_mps,
            log_context,
        )
        delayed_time_s = max(0.0, time_s - ms_to_seconds(parameters.distance_identification_delay_ms))
        delayed1 = _snapshot_at(history1, delayed_time_s)
        delayed2 = _snapshot_at(history2, delayed_time_s)
        delayed3 = _snapshot_at(history3, delayed_time_s)

        command2, control2 = _choose_follower_command(
            time_s=time_s,
            dt_s=step_s,
            follower=truck2,
            delayed_follower=delayed2,
            delayed_front=delayed1,
            actual_front=truck1,
            control=control2,
            parameters=parameters,
            braking_table=braking_table,
            log_context=log_context,
            truck_length_m=initial.truck_length_m,
        )
        command3, control3 = _choose_follower_command(
            time_s=time_s,
            dt_s=step_s,
            follower=truck3,
            delayed_follower=delayed3,
            delayed_front=delayed2,
            actual_front=truck2,
            control=control3,
            parameters=parameters,
            braking_table=braking_table,
            log_context=log_context,
            truck_length_m=initial.truck_length_m,
        )

        communication = _communication_directive(parameters, control2, control3, time_s)
        _log_communication(time_s, communication, log_context)
        if communication.truck2_stop_requested:
            command2 = _communication_stop_command(truck2, parameters, braking_table, time_s, log_context)

        # Check for FORT event on Truck #1 — latches permanently once triggered
        truck1_fort_event = truck1_events.get(round(next_time_s, 10))
        if truck1_fort_event == ImageEvent.FORT_ACTIVATED and not truck1_fort_latched:
            truck1_fort_latched = True
            log_context.add(time_s, "WARNING", "FORT activated", "Truck1 FORT activated. Emergency braking until stopped.")
        truck1_in_fort = truck1_fort_latched
        if truck1_in_fort:
            # _emergency_deceleration returns 0 once velocity reaches 0, holding the truck stopped
            acceleration1_mps2 = _emergency_deceleration(truck1, parameters)
        elif communication.leader_stop_requested:
            acceleration1_mps2 = _communication_stop_acceleration(truck1, parameters, braking_table, time_s, log_context)
        else:
            target_leader_velocity_mps = kph_to_mps(profile.velocity_at(next_time_s))
            acceleration1_mps2 = (target_leader_velocity_mps - truck1.velocity_mps) / step_s
        truck1 = step_motion(
            truck1,
            acceleration1_mps2,
            step_s,
        )
        truck2 = step_motion(
            truck2,
            command2.acceleration_mps2,
            step_s,
            max_velocity_mps=kph_to_mps(parameters.max_velocity_kph),
        )
        truck3 = step_motion(
            truck3,
            command3.acceleration_mps2,
            step_s,
            max_velocity_mps=kph_to_mps(parameters.max_velocity_kph),
        )

        time_s = next_time_s
        history1.append(TruckSnapshot(time_s, truck1.position_m, truck1.velocity_mps))
        history2.append(TruckSnapshot(time_s, truck2.position_m, truck2.velocity_mps))
        history3.append(TruckSnapshot(time_s, truck3.position_m, truck3.velocity_mps))

        if _is_output_time(time_s, output_resolution_s, output_index):
            delayed_time_s = max(0.0, time_s - ms_to_seconds(parameters.distance_identification_delay_ms))
            delayed1 = _snapshot_at(history1, delayed_time_s)
            delayed2 = _snapshot_at(history2, delayed_time_s)
            delayed3 = _snapshot_at(history3, delayed_time_s)
            rows.append(
                _build_output_row(
                    time_s,
                    truck1,
                    truck2,
                    truck3,
                    acceleration1_mps2=acceleration1_mps2,
                    acceleration2_mps2=command2.acceleration_mps2,
                    acceleration3_mps2=command3.acceleration_mps2,
                    control2=control2,
                    control3=control3,
                    command2=command2.command,
                    command3=command3.command,
                    delayed1=delayed1,
                    delayed2=delayed2,
                    delayed3=delayed3,
                    communication=communication,
                    parameters=parameters,
                    truck_length_m=initial.truck_length_m,
                    truck1_in_fort=truck1_in_fort,
                )
            )
            output_index += 1

    _log_violations(rows, log_context)
    return SimulationResult(rows=tuple(rows), logs=tuple(log_context.rows))


def run_basic_simulation_from_files(
    parameters_path: str | Path,
    scenario_path: str | Path,
    output_path: str | Path,
    braking_table_path: str | Path | None = None,
    log_output_path: str | Path | None = None,
) -> SimulationResult:
    loaded = load_parameters_csv(parameters_path)
    timeline = ScenarioTimeline.from_csv(scenario_path)
    braking_table = BrakingDistanceTable.from_csv(braking_table_path) if braking_table_path is not None else None
    result = run_basic_simulation(loaded.initial_conditions, loaded.simulation_parameters, timeline, braking_table)
    result.write_csv(output_path)
    if log_output_path is not None:
        result.write_log_csv(log_output_path)
    return result


def _choose_follower_command(
    time_s: float,
    dt_s: float,
    follower: MotionState,
    delayed_follower: TruckSnapshot,
    delayed_front: TruckSnapshot,
    actual_front: MotionState,
    control: FollowerControl,
    parameters: SimulationParameters,
    braking_table: BrakingDistanceTable | None,
    log_context: SimulationLogContext,
    truck_length_m: float,
) -> tuple[TruckCommand, FollowerControl]:
    actual_gap_m = actual_front.position_m - truck_length_m - follower.position_m
    if control.tracking and actual_gap_m > parameters.image_identification_loss_distance_m:
        control = replace(
            control,
            tracking=False,
            loss_started_at_s=time_s,
            earliest_resume_at_s=time_s,
            frozen_target_front_m=actual_front.position_m,
            stopped_at_loss_target_since_s=None,
            stop_reason="",
            loss_source="Distance",
            orange_target_velocity_mps=None,
            resume_from_stop_blocked=False,
        )
        log_context.add(time_s, "WARNING", "Image identification loss", "Tracking lost because gap exceeded image-identification loss distance.")

    if not control.tracking:
        return _lost_tracking_command(
            time_s,
            follower,
            control,
            parameters,
            braking_table,
            log_context,
            truck_length_m,
            dt_s,
            actual_gap_m,
        )

    perceived_gap_m = delayed_front.position_m - truck_length_m - delayed_follower.position_m
    orange_trigger_gap_m = _orange_trigger_gap(follower.velocity_mps, parameters)

    if control.fort_activated:
        control = replace(
            control,
            fort_activated=False,
            state=FollowerState.FORT_EMERGENCY_DECEL,
            orange_target_velocity_mps=None,
        )
        return TruckCommand(control.state, _emergency_deceleration(follower, parameters), "FORT emergency deceleration"), control

    if control.red_braking_to_stop:
        if follower.velocity_mps <= 1e-9:
            control = replace(
                control,
                red_braking_to_stop=False,
                state=FollowerState.STOPPED_WAITING,
                orange_target_velocity_mps=None,
            )
            return TruckCommand(control.state, 0.0, "Hold stopped"), control
        control = replace(control, state=FollowerState.FOLLOWING_RED_BRAKING_TO_STOP, orange_target_velocity_mps=None)
        return TruckCommand(
            control.state,
            _red_braking_acceleration(parameters, braking_table, mps_to_kph(follower.velocity_mps), time_s, log_context),
            "Red brake to stop",
        ), control

    if perceived_gap_m <= parameters.red_distance_m:
        control = replace(
            control,
            red_braking_to_stop=True,
            state=FollowerState.FOLLOWING_RED_BRAKING_TO_STOP,
            orange_target_velocity_mps=None,
        )
        return TruckCommand(
            control.state,
            _red_braking_acceleration(parameters, braking_table, mps_to_kph(follower.velocity_mps), time_s, log_context),
            "Red brake to stop",
        ), control

    if follower.velocity_mps <= 1e-9:
        if control.resume_from_stop_blocked:
            control = replace(control, start_delay_started_at_s=None, state=FollowerState.STOPPED_WAITING)
            return TruckCommand(control.state, 0.0, "Hold stopped after resume"), control
        if delayed_front.velocity_mps <= 1e-9:
            control = replace(control, start_delay_started_at_s=None, state=FollowerState.STOPPED_WAITING)
            return TruckCommand(control.state, 0.0, "Hold stopped"), control

        if not control.initial_movement_started:
            if perceived_gap_m > parameters.start_moving_gap_m and delayed_front.velocity_mps > 1.0:
                control = replace(
                    control,
                    start_delay_started_at_s=None,
                    state=FollowerState.FOLLOWING_ACCELERATING,
                    initial_movement_started=True,
                    resume_from_stop_blocked=False,
                )
                return TruckCommand(control.state, _positive_acceleration(parameters), "Accelerate initial start"), control
            control = replace(control, start_delay_started_at_s=None, state=FollowerState.STOPPED_WAITING)
            return TruckCommand(control.state, 0.0, "Wait for initial start conditions"), control

        if perceived_gap_m >= parameters.start_moving_gap_m:
            control = replace(
                control,
                start_delay_started_at_s=None,
                state=FollowerState.FOLLOWING_ACCELERATING,
            )
            return TruckCommand(control.state, _positive_acceleration(parameters), "Accelerate from stopped"), control

        control = replace(control, start_delay_started_at_s=None, state=FollowerState.STOPPED_WAITING)
        return TruckCommand(control.state, 0.0, "Hold stopped"), control

    if control.state == FollowerState.TRACKING_RESUME_PENDING:
        started_at = control.start_delay_started_at_s if control.start_delay_started_at_s is not None else time_s
        delay_s = ms_to_seconds(parameters.start_moving_identification_delay_ms)
        if time_s - started_at < delay_s:
            control = replace(control, start_delay_started_at_s=started_at)
            return TruckCommand(control.state, 0.0, "Wait for resume identification delay"), control
        control = replace(control, start_delay_started_at_s=None)

    if perceived_gap_m <= orange_trigger_gap_m:
        orange_target_velocity_mps = control.orange_target_velocity_mps
        if orange_target_velocity_mps is None:
            orange_target_velocity_mps = follower.velocity_mps * 0.75
        control = replace(
            control,
            state=FollowerState.FOLLOWING_ORANGE_DECEL,
            orange_target_velocity_mps=orange_target_velocity_mps,
        )
        if follower.velocity_mps <= orange_target_velocity_mps + 1e-9:
            return TruckCommand(control.state, 0.0, "Orange hold target speed"), control
        return TruckCommand(
            control.state,
            _orange_braking_acceleration(parameters, braking_table, mps_to_kph(follower.velocity_mps), time_s, log_context),
            "Orange deceleration",
        ), control

    if perceived_gap_m > orange_trigger_gap_m:
        control = replace(control, state=FollowerState.FOLLOWING_ACCELERATING, orange_target_velocity_mps=None)
        return TruckCommand(control.state, _positive_acceleration(parameters), "Accelerate to close gap"), control

    acceleration_mps2 = _clamp(
        (delayed_front.velocity_mps - follower.velocity_mps) / dt_s,
        _orange_braking_acceleration(parameters, braking_table, mps_to_kph(follower.velocity_mps), time_s, log_context),
        parameters.max_acceleration_mps2,
    )
    control = replace(control, state=FollowerState.FOLLOWING_MATCHING_SPEED, orange_target_velocity_mps=None)
    return TruckCommand(control.state, acceleration_mps2, "Match front-truck speed"), control


def _lost_tracking_command(
    time_s: float,
    follower: MotionState,
    control: FollowerControl,
    parameters: SimulationParameters,
    braking_table: BrakingDistanceTable | None,
    log_context: SimulationLogContext,
    truck_length_m: float,
    dt_s: float,
    actual_gap_m: float,
) -> tuple[TruckCommand, FollowerControl]:
    target_front_m = control.frozen_target_front_m or follower.position_m
    target_rear_m = target_front_m - truck_length_m
    distance_to_target_m = target_rear_m - follower.position_m

    if control.state == FollowerState.SAFETY_LOCK:
        return TruckCommand(control.state, 0.0, "Safety Lock parking brakes"), control

    earliest_resume_at_s = control.earliest_resume_at_s or time_s
    if (
        (parameters.resume_by_distance or control.loss_source == "Distance")
        and actual_gap_m <= parameters.image_identification_resume_distance_m
        and time_s >= earliest_resume_at_s
    ):
        control = replace(
            control,
            tracking=True,
            loss_started_at_s=None,
            earliest_resume_at_s=None,
            frozen_target_front_m=None,
            stopped_at_loss_target_since_s=None,
            loss_source="",
            state=FollowerState.TRACKING_RESUME_PENDING,
        )
        return TruckCommand(control.state, 0.0, "Tracking resume pending"), control

    if distance_to_target_m <= 1e-6 or follower.velocity_mps <= 1e-9:
        stopped_since_s = control.stopped_at_loss_target_since_s
        if stopped_since_s is None:
            stopped_since_s = time_s
        if time_s - stopped_since_s >= 30.0:
            stop_reason = "Safety Lock"
            control = replace(
                control,
                state=FollowerState.SAFETY_LOCK,
                stopped_at_loss_target_since_s=stopped_since_s,
                stop_reason=stop_reason,
            )
            log_context.add(time_s, "WARNING", "Stop reason", stop_reason)
            return TruckCommand(control.state, 0.0, "Safety Lock parking brakes"), control

        control = replace(
            control,
            state=FollowerState.TRACKING_LOST_TO_LAST_POSITION,
            stopped_at_loss_target_since_s=stopped_since_s,
        )
        return TruckCommand(control.state, 0.0, "Hold at lost target"), control

    acceleration_mps2 = _target_stop_acceleration(follower.velocity_mps, distance_to_target_m)
    command = "Lost tracking target stop"
    if acceleration_mps2 >= 0.0:
        acceleration_mps2 = 0.0
        command = "Lost tracking hold velocity"
    control = replace(
        control,
        state=FollowerState.TRACKING_LOST_TO_LAST_POSITION,
        stopped_at_loss_target_since_s=None,
    )
    return TruckCommand(control.state, acceleration_mps2, command), control


def _apply_image_event(
    control: FollowerControl,
    event: ImageEvent | None,
    truck_name: str,
    time_s: float,
    front_position_m: float,
    follower_velocity_mps: float,
    log_context: SimulationLogContext,
) -> FollowerControl:
    if event == ImageEvent.LOSS:
        log_context.add(time_s, "WARNING", "Image identification loss", f"{truck_name} image identification lost.")
        return replace(
            control,
            tracking=False,
            loss_started_at_s=time_s,
            earliest_resume_at_s=time_s + 2.0,
            frozen_target_front_m=front_position_m,
            stopped_at_loss_target_since_s=None,
            stop_reason="",
            loss_source="Scenario",
            orange_target_velocity_mps=None,
            resume_from_stop_blocked=False,
        )
    if event == ImageEvent.RESUME:
        log_context.add(time_s, "INFO", "Image identification resume", f"{truck_name} image identification resumed.")
        return replace(
            control,
            tracking=True,
            loss_started_at_s=None,
            earliest_resume_at_s=None,
            frozen_target_front_m=None,
            stopped_at_loss_target_since_s=None,
            loss_source="",
            state=FollowerState.TRACKING_RESUME_PENDING,
            start_delay_started_at_s=None,
            orange_target_velocity_mps=None,
            resume_from_stop_blocked=follower_velocity_mps <= 1e-9,
        )
    if event == ImageEvent.FORT_ACTIVATED:
        log_context.add(time_s, "WARNING", "FORT activated", f"{truck_name} FORT activated.")
        return replace(control, fort_activated=True, orange_target_velocity_mps=None)
    return control


def _raise_if_invalid(initial: InitialConditions, parameters: SimulationParameters, profile: LeaderProfile) -> None:
    validations = (
        validate_initial_conditions(initial),
        validate_parameters(parameters),
        validate_leader_profile(profile, parameters),
    )
    errors = [message.message for result in validations for message in result.errors]
    if errors:
        raise ValueError("Simulation input validation failed: " + "; ".join(errors))


def _snapshot_at(history: list[TruckSnapshot], time_s: float) -> TruckSnapshot:
    for snapshot in reversed(history):
        if snapshot.time_s <= time_s + 1e-9:
            return snapshot
    return history[0]


def _is_output_time(time_s: float, output_resolution_s: float, output_index: int) -> bool:
    return time_s + 1e-9 >= output_index * output_resolution_s


def _positive_acceleration(parameters: SimulationParameters) -> float:
    return min(parameters.green_acceleration_mps2, parameters.optimal_acceleration_mps2, parameters.max_acceleration_mps2)


def _orange_trigger_gap(follower_velocity_mps: float, parameters: SimulationParameters) -> float:
    if parameters.orange_braking_mode == 1:
        return follower_velocity_mps * parameters.time_headway_s + parameters.minimum_gap_m
    return parameters.orange_distance_m


def _emergency_deceleration(follower: MotionState, parameters: SimulationParameters) -> float:
    if follower.velocity_mps <= 1e-9:
        return 0.0
    return -parameters.emergency_deceleration_mps2


def _target_stop_acceleration(velocity_mps: float, distance_m: float) -> float:
    if velocity_mps <= 1e-9 or distance_m <= 1e-9:
        return 0.0
    return -(velocity_mps**2) / (2.0 * distance_m)


def _communication_directive(
    parameters: SimulationParameters,
    control2: FollowerControl,
    control3: FollowerControl,
    time_s: float,
) -> CommunicationDirective:
    if not parameters.trucks_communicating:
        return CommunicationDirective(status="Disabled")

    messages: list[str] = []
    leader_stop_requested = False
    truck2_stop_requested = False
    if not control2.tracking:
        messages.append("Truck2 lost; request Truck1 stop")
        leader_stop_requested = True
    if not control3.tracking:
        messages.append("Truck3 lost; request Truck1 and Truck2 stop")
        leader_stop_requested = True
        truck2_stop_requested = True

    if not messages:
        return CommunicationDirective(status="Enabled")

    loss_started_times = [
        control.loss_started_at_s
        for control in (control2, control3)
        if not control.tracking and control.loss_started_at_s is not None
    ]
    elapsed_s = 0.0 if not loss_started_times else max(0.0, time_s - min(loss_started_times))
    message = "; ".join(messages)

    if parameters.communication_reliability_percent <= 0:
        if elapsed_s < 0.4:
            return CommunicationDirective(message=message, status="Sent")
        if elapsed_s < 0.8:
            return CommunicationDirective(message=message, status="Retried")
        return CommunicationDirective(message=message, status="Failed fallback")

    if parameters.communication_reliability_percent < 100:
        if elapsed_s < 0.4:
            return CommunicationDirective(message=message, status="Sent")
        if elapsed_s < 0.8:
            return CommunicationDirective(message=message, status="Retried")

    return CommunicationDirective(
        leader_stop_requested=leader_stop_requested,
        truck2_stop_requested=truck2_stop_requested,
        message=message,
        status="Approved",
    )


def _communication_stop_command(
    truck: MotionState,
    parameters: SimulationParameters,
    braking_table: BrakingDistanceTable | None,
    time_s: float,
    log_context: SimulationLogContext,
) -> TruckCommand:
    return TruckCommand(
        FollowerState.COMMUNICATION_REQUEST_STOP,
        _communication_stop_acceleration(truck, parameters, braking_table, time_s, log_context),
        "Communication stop request",
    )


def _communication_stop_acceleration(
    truck: MotionState,
    parameters: SimulationParameters,
    braking_table: BrakingDistanceTable | None,
    time_s: float,
    log_context: SimulationLogContext,
) -> float:
    under_loss_velocity_mps = kph_to_mps(parameters.under_loss_leading_velocity_kph)
    if truck.velocity_mps <= 1e-9:
        return 0.0
    if truck.velocity_mps < under_loss_velocity_mps:
        return 0.0
    return _orange_braking_acceleration(parameters, braking_table, mps_to_kph(truck.velocity_mps), time_s, log_context)


def _red_braking_acceleration(
    parameters: SimulationParameters,
    braking_table: BrakingDistanceTable | None,
    velocity_kph: float,
    time_s: float,
    log_context: SimulationLogContext,
) -> float:
    if braking_table is None:
        return -parameters.max_red_deceleration_mps2

    acceleration_mps2 = braking_table.deceleration_for(parameters.road_type, BrakingType.RED, velocity_kph)
    if acceleration_mps2 is None:
        _log_braking_fallback(time_s, "Red", velocity_kph, log_context)
        return -parameters.max_red_deceleration_mps2
    return acceleration_mps2


def _orange_braking_acceleration(
    parameters: SimulationParameters,
    braking_table: BrakingDistanceTable | None,
    velocity_kph: float,
    time_s: float,
    log_context: SimulationLogContext,
) -> float:
    if braking_table is None:
        return -parameters.orange_deceleration_mps2

    acceleration_mps2 = braking_table.deceleration_for(parameters.road_type, BrakingType.ORANGE, velocity_kph)
    if acceleration_mps2 is None:
        _log_braking_fallback(time_s, "Orange", velocity_kph, log_context)
        return -parameters.orange_deceleration_mps2
    return acceleration_mps2


def _log_braking_fallback(
    time_s: float,
    braking_type: str,
    velocity_kph: float,
    log_context: SimulationLogContext,
) -> None:
    key = (braking_type, f"{velocity_kph:.1f}")
    if key in log_context.braking_fallback_keys:
        return
    log_context.braking_fallback_keys.add(key)
    log_context.add(
        time_s,
        "WARNING",
        "Braking fallback",
        f"{braking_type} braking table lookup unavailable at {velocity_kph:.1f} kph; using configured fallback deceleration.",
    )


def _log_communication(
    time_s: float,
    communication: CommunicationDirective,
    log_context: SimulationLogContext,
) -> None:
    if not communication.message:
        return
    log_context.add(time_s, "INFO", "Communication", f"{communication.status}: {communication.message}")


def _log_violations(rows: list[SimulationRow], log_context: SimulationLogContext) -> None:
    seen: set[tuple[float, str, str]] = set()
    for row in rows:
        for truck_name, violation in (
            ("Truck2", row.violation_type_truck2),
            ("Truck3", row.violation_type_truck3),
        ):
            if not violation:
                continue
            key = (row.time_s, truck_name, violation)
            if key in seen:
                continue
            seen.add(key)
            log_context.add(row.time_s, "WARNING", "Violation", f"{truck_name}: {violation}")


def _gap(front: MotionState, follower: MotionState, truck_length_m: float) -> float:
    return front.position_m - truck_length_m - follower.position_m


def _tracking_status(control: FollowerControl) -> str:
    return "Tracking" if control.tracking else "Lost"


def _violation_type(gap_m: float, parameters: SimulationParameters, tracking: bool, stop_reason: str) -> str:
    violations: list[str] = []
    if gap_m <= 0:
        violations.append("Collision")
    elif gap_m < parameters.minimum_gap_m:
        violations.append("Minimum gap violation")
    if gap_m > parameters.maximum_gap_m:
        violations.append("Maximum gap violation")
    if not tracking:
        violations.append("Image identification loss")
    if stop_reason == "Image resume timeout":
        violations.append("Image resume timeout")
    if stop_reason == "Safety Lock":
        violations.append("Safety Lock")
    return "; ".join(violations)


def _gap_violation(gap_m: float, parameters: SimulationParameters) -> bool:
    return gap_m <= 0 or gap_m < parameters.minimum_gap_m or gap_m > parameters.maximum_gap_m


def _leader_state(truck: MotionState, acceleration_mps2: float, communication: CommunicationDirective) -> str:
    if communication.leader_stop_requested:
        return "LEADER_COMMUNICATION_STOP"
    if truck.velocity_mps <= 1e-9:
        return "LEADER_STOPPED"
    if acceleration_mps2 > 1e-9:
        return "LEADER_ACCELERATING"
    if acceleration_mps2 < -1e-9:
        return "LEADER_DECELERATING"
    return "LEADER_CRUISING"


def _leader_command(truck: MotionState, acceleration_mps2: float, communication: CommunicationDirective) -> str:
    if communication.leader_stop_requested:
        return "Communication stop request"
    if truck.velocity_mps <= 1e-9:
        return "Hold stopped"
    if acceleration_mps2 > 1e-9:
        return "Follow leader profile acceleration"
    if acceleration_mps2 < -1e-9:
        return "Follow leader profile deceleration"
    return "Follow leader profile speed"


def _build_output_row(
    time_s: float,
    truck1: MotionState,
    truck2: MotionState,
    truck3: MotionState,
    acceleration1_mps2: float,
    acceleration2_mps2: float,
    acceleration3_mps2: float,
    control2: FollowerControl,
    control3: FollowerControl,
    command2: str,
    command3: str,
    delayed1: TruckSnapshot,
    delayed2: TruckSnapshot,
    delayed3: TruckSnapshot,
    communication: CommunicationDirective,
    parameters: SimulationParameters,
    truck_length_m: float,
    truck1_in_fort: bool = False,
) -> SimulationRow:
    gap2_m = _gap(truck1, truck2, truck_length_m)
    gap3_m = _gap(truck2, truck3, truck_length_m)
    measured_gap2_m = delayed1.position_m - truck_length_m - delayed2.position_m
    measured_gap3_m = delayed2.position_m - truck_length_m - delayed3.position_m
    violation2 = _violation_type(gap2_m, parameters, control2.tracking, control2.stop_reason)
    violation3 = _violation_type(gap3_m, parameters, control3.tracking, control3.stop_reason)
    return SimulationRow(
        time_s=time_s,
        truck1_position_m=truck1.position_m,
        truck2_position_m=truck2.position_m,
        truck3_position_m=truck3.position_m,
        truck2_gap_m=gap2_m,
        truck3_gap_m=gap3_m,
        gap2_violation=_gap_violation(gap2_m, parameters),
        gap3_violation=_gap_violation(gap3_m, parameters),
        truck1_velocity_kph=mps_to_kph(truck1.velocity_mps),
        truck2_velocity_kph=mps_to_kph(truck2.velocity_mps),
        truck3_velocity_kph=mps_to_kph(truck3.velocity_mps),
        truck1_acceleration_mps2=acceleration1_mps2,
        truck2_acceleration_mps2=acceleration2_mps2,
        truck3_acceleration_mps2=acceleration3_mps2,
        truck2_state=control2.state.value,
        truck3_state=control3.state.value,
        truck2_command=command2,
        truck3_command=command3,
        truck2_actual_gap_m=gap2_m,
        truck2_measured_gap_m=measured_gap2_m,
        truck3_actual_gap_m=gap3_m,
        truck3_measured_gap_m=measured_gap3_m,
        truck2_tracking_status=_tracking_status(control2),
        truck3_tracking_status=_tracking_status(control3),
        truck2_relative_velocity_kph=mps_to_kph(truck2.velocity_mps - truck1.velocity_mps),
        truck3_relative_velocity_kph=mps_to_kph(truck3.velocity_mps - truck2.velocity_mps),
        communication_message=communication.message,
        communication_status=communication.status,
        violation_type_truck2=violation2,
        violation_type_truck3=violation3,
        stop_reason_truck2=control2.stop_reason,
        stop_reason_truck3=control3.stop_reason,
        truck1_state="FORT_EMERGENCY_DECEL" if truck1_in_fort else _leader_state(truck1, acceleration1_mps2, communication),
        truck1_command="FORT emergency deceleration" if truck1_in_fort else _leader_command(truck1, acceleration1_mps2, communication),
        truck2_loss_source=control2.loss_source,
        truck3_loss_source=control3.loss_source,
        truck2_loss_target_rear_m=_loss_target_rear(control2, truck_length_m),
        truck3_loss_target_rear_m=_loss_target_rear(control3, truck_length_m),
        truck2_orange_trigger_gap_m=_orange_trigger_gap(truck2.velocity_mps, parameters),
        truck3_orange_trigger_gap_m=_orange_trigger_gap(truck3.velocity_mps, parameters),
        orange_braking_mode=parameters.orange_braking_mode,
    )


def _row_to_csv(row: SimulationRow) -> dict[str, str]:
    return {
        "Time_s": f"{row.time_s:.3f}",
        "Truck1_Position_m": f"{row.truck1_position_m:.3f}",
        "Truck2_Position_m": f"{row.truck2_position_m:.3f}",
        "Truck3_Position_m": f"{row.truck3_position_m:.3f}",
        "Truck2_Gap_m": f"{row.truck2_gap_m:.3f}",
        "Truck3_Gap_m": f"{row.truck3_gap_m:.3f}",
        "Gap2_Violation": _yes_no(row.gap2_violation),
        "Gap3_Violation": _yes_no(row.gap3_violation),
        "Truck1_Velocity_kph": f"{row.truck1_velocity_kph:.3f}",
        "Truck2_Velocity_kph": f"{row.truck2_velocity_kph:.3f}",
        "Truck3_Velocity_kph": f"{row.truck3_velocity_kph:.3f}",
        "Truck1_Acceleration_mps2": f"{row.truck1_acceleration_mps2:.3f}",
        "Truck2_Acceleration_mps2": f"{row.truck2_acceleration_mps2:.3f}",
        "Truck3_Acceleration_mps2": f"{row.truck3_acceleration_mps2:.3f}",
        "Truck1_State": row.truck1_state,
        "Truck2_State": row.truck2_state,
        "Truck3_State": row.truck3_state,
        "Truck1_Command": row.truck1_command,
        "Truck2_Command": row.truck2_command,
        "Truck3_Command": row.truck3_command,
        "Truck2_Loss_Source": row.truck2_loss_source,
        "Truck3_Loss_Source": row.truck3_loss_source,
        "Truck2_Loss_Target_Rear_m": _optional_float_csv(row.truck2_loss_target_rear_m),
        "Truck3_Loss_Target_Rear_m": _optional_float_csv(row.truck3_loss_target_rear_m),
        "Truck2_Orange_Trigger_Gap_m": f"{row.truck2_orange_trigger_gap_m:.3f}",
        "Truck3_Orange_Trigger_Gap_m": f"{row.truck3_orange_trigger_gap_m:.3f}",
        "Orange_Braking_Mode": str(row.orange_braking_mode),
        "Truck2_Actual_Gap_m": f"{row.truck2_actual_gap_m:.3f}",
        "Truck2_Measured_Gap_m": f"{row.truck2_measured_gap_m:.3f}",
        "Truck3_Actual_Gap_m": f"{row.truck3_actual_gap_m:.3f}",
        "Truck3_Measured_Gap_m": f"{row.truck3_measured_gap_m:.3f}",
        "Truck2_Tracking_Status": row.truck2_tracking_status,
        "Truck3_Tracking_Status": row.truck3_tracking_status,
        "Truck2_Relative_Velocity_kph": f"{row.truck2_relative_velocity_kph:.3f}",
        "Truck3_Relative_Velocity_kph": f"{row.truck3_relative_velocity_kph:.3f}",
        "Communication_Message": row.communication_message,
        "Communication_Status": row.communication_status,
        "Violation_Type_Truck2": row.violation_type_truck2,
        "Violation_Type_Truck3": row.violation_type_truck3,
        "Stop_Reason_Truck2": row.stop_reason_truck2,
        "Stop_Reason_Truck3": row.stop_reason_truck3,
    }


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _optional_float_csv(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}"


def _loss_target_rear(control: FollowerControl, truck_length_m: float) -> float | None:
    if control.tracking or control.frozen_target_front_m is None:
        return None
    return control.frozen_target_front_m - truck_length_m


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


_OUTPUT_COLUMNS = (
    "Time_s",
    "Truck1_Position_m",
    "Truck2_Position_m",
    "Truck3_Position_m",
    "Truck2_Gap_m",
    "Truck3_Gap_m",
    "Gap2_Violation",
    "Gap3_Violation",
    "Truck1_Velocity_kph",
    "Truck2_Velocity_kph",
    "Truck3_Velocity_kph",
    "Truck1_Acceleration_mps2",
    "Truck2_Acceleration_mps2",
    "Truck3_Acceleration_mps2",
    "Truck1_State",
    "Truck2_State",
    "Truck3_State",
    "Truck1_Command",
    "Truck2_Command",
    "Truck3_Command",
    "Truck2_Loss_Source",
    "Truck3_Loss_Source",
    "Truck2_Loss_Target_Rear_m",
    "Truck3_Loss_Target_Rear_m",
    "Truck2_Orange_Trigger_Gap_m",
    "Truck3_Orange_Trigger_Gap_m",
    "Orange_Braking_Mode",
    "Truck2_Actual_Gap_m",
    "Truck2_Measured_Gap_m",
    "Truck3_Actual_Gap_m",
    "Truck3_Measured_Gap_m",
    "Truck2_Tracking_Status",
    "Truck3_Tracking_Status",
    "Truck2_Relative_Velocity_kph",
    "Truck3_Relative_Velocity_kph",
    "Communication_Message",
    "Communication_Status",
    "Violation_Type_Truck2",
    "Violation_Type_Truck3",
    "Stop_Reason_Truck2",
    "Stop_Reason_Truck3",
)
