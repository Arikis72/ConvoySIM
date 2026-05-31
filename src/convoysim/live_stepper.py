"""Live simulation stepper for the Online Visualization leader-control feature.

Provides LiveSimStepper, which holds mutable simulation state and advances
one second at a time under user-supplied leader commands.  Supports undo so
the user can step backward through their own interventions.

The simulation logic (follower state machine, physics, output-row building) is
reused unchanged from simulation.py; only the leader acceleration source
changes from the pre-calculated scenario profile to LiveLeaderCommand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from convoysim.braking import BrakingDistanceTable
from convoysim.models import InitialConditions, SimulationParameters
from convoysim.physics import MotionState, step_motion
from convoysim.scenario_timeline import ImageEvent, ScenarioTimeline
from convoysim.simulation import (
    CommunicationDirective,
    FollowerControl,
    SimulationLogContext,
    SimulationRow,
    TruckSnapshot,
    _apply_image_event,
    _build_output_row,
    _choose_follower_command,
    _communication_directive,
    _communication_stop_acceleration,
    _emergency_deceleration,
    _is_output_time,
    _snapshot_at,
)
from convoysim.units import kph_to_mps, ms_to_seconds


@dataclass(frozen=True)
class LiveLeaderCommand:
    """A single leader-control command applied for one simulated second."""

    kind: Literal["hold", "accelerate", "decelerate", "orange_brake", "red_brake", "fort_brake"]
    rate_mps2: float = 0.0  # used for "accelerate" and "decelerate" kinds only


# Convenience constructors
HOLD = LiveLeaderCommand(kind="hold")
ORANGE_BRAKE = LiveLeaderCommand(kind="orange_brake")
RED_BRAKE = LiveLeaderCommand(kind="red_brake")
FORT_BRAKE = LiveLeaderCommand(kind="fort_brake")


def accelerate(rate_mps2: float) -> LiveLeaderCommand:
    return LiveLeaderCommand(kind="accelerate", rate_mps2=rate_mps2)


def decelerate(rate_mps2: float) -> LiveLeaderCommand:
    return LiveLeaderCommand(kind="decelerate", rate_mps2=rate_mps2)


@dataclass
class _StepperState:
    """Mutable snapshot of all simulation state needed to step forward."""

    truck1: MotionState
    truck2: MotionState
    truck3: MotionState
    control2: FollowerControl
    control3: FollowerControl
    communication: CommunicationDirective
    truck1_fort_latched: bool
    time_s: float
    output_index: int
    history1: list[TruckSnapshot]
    history2: list[TruckSnapshot]
    history3: list[TruckSnapshot]

    def copy(self) -> _StepperState:
        """Deep-copy all mutable fields (histories are lists and must be copied)."""
        return _StepperState(
            truck1=self.truck1,
            truck2=self.truck2,
            truck3=self.truck3,
            control2=self.control2,
            control3=self.control3,
            communication=self.communication,
            truck1_fort_latched=self.truck1_fort_latched,
            time_s=self.time_s,
            output_index=self.output_index,
            history1=list(self.history1),
            history2=list(self.history2),
            history3=list(self.history3),
        )


class LiveSimStepper:
    """Holds mutable simulation state and steps one second at a time.

    Usage:
        stepper = LiveSimStepper(initial, parameters, timeline, braking_table, target_time_s)
        rows = stepper.advance_one_second(HOLD)          # step forward 1 s
        stepper.undo_one_second()                        # step back 1 s
    """

    def __init__(
        self,
        initial: InitialConditions,
        parameters: SimulationParameters,
        timeline: ScenarioTimeline,
        braking_table: BrakingDistanceTable | None,
        target_time_s: float,
    ) -> None:
        self._initial = initial
        self._parameters = parameters
        self._timeline = timeline
        self._braking_table = braking_table
        self._truck1_events = {event.time_s: event.event for event in timeline.truck1_events()}
        self._truck2_events = {event.time_s: event.event for event in timeline.truck2_image_events()}
        self._truck3_events = {event.time_s: event.event for event in timeline.truck3_image_events()}
        self._log = SimulationLogContext(rows=[], braking_fallback_keys=set())
        self._state = self._fast_forward_to(target_time_s)
        self._undo_stack: list[_StepperState] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def advance_one_second(self, command: LiveLeaderCommand) -> tuple[SimulationRow, ...]:
        """Advance exactly 1 simulated second under the given leader command.

        Saves a snapshot for undo before mutating state.
        Returns all output rows generated during this second.
        """
        self._undo_stack.append(self._state.copy())
        return self._step_n(command, n_steps=max(1, round(1.0 / self._parameters.simulation_time_step_s)))

    def undo_one_second(self) -> bool:
        """Restore state to just before the last advance_one_second call.

        Returns True if undo succeeded, False if nothing to undo.
        """
        if not self._undo_stack:
            return False
        self._state = self._undo_stack.pop()
        return True

    @property
    def current_time_s(self) -> float:
        return self._state.time_s

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fast_forward_to(self, target_time_s: float) -> _StepperState:
        """Silently re-run the pre-calculated simulation from t=0 to target_time_s.

        Uses the original scenario profile for the leader.  Does not produce
        output rows — only the final mutable state is retained.
        """
        params = self._parameters
        initial = self._initial
        dt_s = params.simulation_time_step_s
        profile = self._timeline.leader_profile()

        truck1_front_m, truck2_front_m, truck3_front_m = initial.initial_front_positions()
        truck1 = MotionState(position_m=truck1_front_m, velocity_mps=kph_to_mps(initial.truck1_velocity_kph))
        truck2 = MotionState(position_m=truck2_front_m, velocity_mps=kph_to_mps(initial.truck2_velocity_kph))
        truck3 = MotionState(position_m=truck3_front_m, velocity_mps=kph_to_mps(initial.truck3_velocity_kph))
        control2 = FollowerControl(initial_movement_started=truck2.velocity_mps > 1e-9)
        control3 = FollowerControl(initial_movement_started=truck3.velocity_mps > 1e-9)
        history1: list[TruckSnapshot] = [TruckSnapshot(0.0, truck1.position_m, truck1.velocity_mps)]
        history2: list[TruckSnapshot] = [TruckSnapshot(0.0, truck2.position_m, truck2.velocity_mps)]
        history3: list[TruckSnapshot] = [TruckSnapshot(0.0, truck3.position_m, truck3.velocity_mps)]
        truck1_fort_latched = False
        time_s = 0.0
        output_index = 0
        communication = _communication_directive(params, control2, control3, time_s)

        # Count the t=0 output row (mirrors run_basic_simulation pre-step check)
        if _is_output_time(time_s, params.output_resolution_s, output_index):
            output_index += 1

        while time_s < target_time_s - 1e-9:
            next_time_s = time_s + dt_s
            step_s = dt_s

            control2 = _apply_image_event(
                control2, self._truck2_events.get(round(next_time_s, 10)), "Truck2",
                next_time_s, truck1.position_m, truck2.velocity_mps, self._log,
            )
            control3 = _apply_image_event(
                control3, self._truck3_events.get(round(next_time_s, 10)), "Truck3",
                next_time_s, truck2.position_m, truck3.velocity_mps, self._log,
            )

            delayed_time_s = max(0.0, time_s - ms_to_seconds(params.distance_identification_delay_ms))
            delayed1 = _snapshot_at(history1, delayed_time_s)
            delayed2 = _snapshot_at(history2, delayed_time_s)
            delayed3 = _snapshot_at(history3, delayed_time_s)

            command2, control2 = _choose_follower_command(
                time_s=time_s, dt_s=step_s, follower=truck2, delayed_follower=delayed2,
                delayed_front=delayed1, actual_front=truck1, control=control2,
                parameters=params, braking_table=self._braking_table,
                log_context=self._log, truck_length_m=initial.truck_length_m,
            )
            command3, control3 = _choose_follower_command(
                time_s=time_s, dt_s=step_s, follower=truck3, delayed_follower=delayed3,
                delayed_front=delayed2, actual_front=truck2, control=control3,
                parameters=params, braking_table=self._braking_table,
                log_context=self._log, truck_length_m=initial.truck_length_m,
            )

            communication = _communication_directive(params, control2, control3, time_s)
            if communication.truck2_stop_requested:
                from convoysim.simulation import _communication_stop_command
                command2 = _communication_stop_command(truck2, params, self._braking_table, time_s, self._log)

            # Truck 1 FORT check
            if self._truck1_events.get(round(next_time_s, 10)) == ImageEvent.FORT_ACTIVATED and not truck1_fort_latched:
                truck1_fort_latched = True

            if truck1_fort_latched:
                acceleration1 = _emergency_deceleration(truck1, params)
            elif communication.leader_stop_requested:
                acceleration1 = _communication_stop_acceleration(truck1, params, self._braking_table, time_s, self._log)
            else:
                target_vel = kph_to_mps(profile.velocity_at(next_time_s))
                acceleration1 = (target_vel - truck1.velocity_mps) / step_s

            truck1 = step_motion(truck1, acceleration1, step_s)
            truck2 = step_motion(truck2, command2.acceleration_mps2, step_s,
                                  max_velocity_mps=kph_to_mps(params.max_velocity_kph))
            truck3 = step_motion(truck3, command3.acceleration_mps2, step_s,
                                  max_velocity_mps=kph_to_mps(params.max_velocity_kph))

            time_s = next_time_s
            history1.append(TruckSnapshot(time_s, truck1.position_m, truck1.velocity_mps))
            history2.append(TruckSnapshot(time_s, truck2.position_m, truck2.velocity_mps))
            history3.append(TruckSnapshot(time_s, truck3.position_m, truck3.velocity_mps))

            if _is_output_time(time_s, params.output_resolution_s, output_index):
                output_index += 1

        return _StepperState(
            truck1=truck1, truck2=truck2, truck3=truck3,
            control2=control2, control3=control3,
            communication=communication,
            truck1_fort_latched=truck1_fort_latched,
            time_s=time_s, output_index=output_index,
            history1=history1, history2=history2, history3=history3,
        )

    def _step_n(self, command: LiveLeaderCommand, n_steps: int) -> tuple[SimulationRow, ...]:
        """Step n_steps simulation steps with the given command; return output rows."""
        params = self._parameters
        initial = self._initial
        s = self._state
        rows: list[SimulationRow] = []

        for _ in range(n_steps):
            next_time_s = s.time_s + params.simulation_time_step_s
            step_s = params.simulation_time_step_s

            control2 = _apply_image_event(
                s.control2, self._truck2_events.get(round(next_time_s, 10)), "Truck2",
                next_time_s, s.truck1.position_m, s.truck2.velocity_mps, self._log,
            )
            control3 = _apply_image_event(
                s.control3, self._truck3_events.get(round(next_time_s, 10)), "Truck3",
                next_time_s, s.truck2.position_m, s.truck3.velocity_mps, self._log,
            )

            delayed_time_s = max(0.0, s.time_s - ms_to_seconds(params.distance_identification_delay_ms))
            delayed1 = _snapshot_at(s.history1, delayed_time_s)
            delayed2 = _snapshot_at(s.history2, delayed_time_s)
            delayed3 = _snapshot_at(s.history3, delayed_time_s)

            cmd2, control2 = _choose_follower_command(
                time_s=s.time_s, dt_s=step_s, follower=s.truck2, delayed_follower=delayed2,
                delayed_front=delayed1, actual_front=s.truck1, control=control2,
                parameters=params, braking_table=self._braking_table,
                log_context=self._log, truck_length_m=initial.truck_length_m,
            )
            cmd3, control3 = _choose_follower_command(
                time_s=s.time_s, dt_s=step_s, follower=s.truck3, delayed_follower=delayed3,
                delayed_front=delayed2, actual_front=s.truck2, control=control3,
                parameters=params, braking_table=self._braking_table,
                log_context=self._log, truck_length_m=initial.truck_length_m,
            )

            communication = _communication_directive(params, control2, control3, s.time_s)
            if communication.truck2_stop_requested:
                from convoysim.simulation import _communication_stop_command
                cmd2 = _communication_stop_command(s.truck2, params, self._braking_table, s.time_s, self._log)

            # FORT latch update (no new FORT events in live mode — already past the timeline)
            fort_latched = s.truck1_fort_latched
            if command.kind == "fort_brake" and not fort_latched:
                fort_latched = True

            # Leader acceleration from command (safety overrides take priority)
            if fort_latched:
                acceleration1 = _emergency_deceleration(s.truck1, params)
            elif communication.leader_stop_requested:
                acceleration1 = _communication_stop_acceleration(s.truck1, params, self._braking_table, s.time_s, self._log)
            else:
                acceleration1 = self._leader_acceleration(command, s.truck1, params)

            truck1 = step_motion(s.truck1, acceleration1, step_s)
            truck2 = step_motion(s.truck2, cmd2.acceleration_mps2, step_s,
                                  max_velocity_mps=kph_to_mps(params.max_velocity_kph))
            truck3 = step_motion(s.truck3, cmd3.acceleration_mps2, step_s,
                                  max_velocity_mps=kph_to_mps(params.max_velocity_kph))

            time_s = next_time_s
            s.history1.append(TruckSnapshot(time_s, truck1.position_m, truck1.velocity_mps))
            s.history2.append(TruckSnapshot(time_s, truck2.position_m, truck2.velocity_mps))
            s.history3.append(TruckSnapshot(time_s, truck3.position_m, truck3.velocity_mps))

            output_index = s.output_index
            if _is_output_time(time_s, params.output_resolution_s, output_index):
                delayed_time_s = max(0.0, time_s - ms_to_seconds(params.distance_identification_delay_ms))
                d1 = _snapshot_at(s.history1, delayed_time_s)
                d2 = _snapshot_at(s.history2, delayed_time_s)
                d3 = _snapshot_at(s.history3, delayed_time_s)
                rows.append(_build_output_row(
                    time_s, truck1, truck2, truck3,
                    acceleration1_mps2=acceleration1,
                    acceleration2_mps2=cmd2.acceleration_mps2,
                    acceleration3_mps2=cmd3.acceleration_mps2,
                    control2=control2, control3=control3,
                    command2=cmd2.command, command3=cmd3.command,
                    delayed1=d1, delayed2=d2, delayed3=d3,
                    communication=communication, parameters=params,
                    truck_length_m=initial.truck_length_m,
                    truck1_in_fort=fort_latched,
                ))
                output_index += 1

            # Update mutable state in place for next internal step
            s.truck1 = truck1
            s.truck2 = truck2
            s.truck3 = truck3
            s.control2 = control2
            s.control3 = control3
            s.communication = communication
            s.truck1_fort_latched = fort_latched
            s.time_s = time_s
            s.output_index = output_index

        return tuple(rows)

    @staticmethod
    def _leader_acceleration(command: LiveLeaderCommand, truck1: MotionState, params: SimulationParameters) -> float:
        kind = command.kind
        if kind == "hold":
            return 0.0
        if kind == "accelerate":
            return min(command.rate_mps2, params.max_acceleration_mps2)
        if kind == "decelerate":
            # step_motion handles the velocity floor (clamps to 0), so negative accel is safe
            return -command.rate_mps2
        if kind == "orange_brake":
            return -params.orange_deceleration_mps2
        if kind == "red_brake":
            return -params.max_red_deceleration_mps2
        # fort_brake: handled in _step_n before this call (fort_latched path)
        return _emergency_deceleration(truck1, params)
