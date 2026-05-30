"""Parameter CSV loading for ConvoySIM examples and basic runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

from convoysim.models import InitialConditions, RoadType, SimulationParameters


@dataclass(frozen=True)
class LoadedParameters:
    initial_conditions: InitialConditions
    simulation_parameters: SimulationParameters


def load_parameters_csv(path: str | Path) -> LoadedParameters:
    values = _read_parameter_values(path)

    target_gap_m = _float_value(values, "Target gap")
    initial = InitialConditions(
        truck_length_m=_float_value(values, "Truck length"),
        initial_gap_12_m=_float_value(values, "Initial gap between Truck #1 and Truck #2"),
        initial_gap_23_m=_float_value(values, "Initial gap between Truck #2 and Truck #3"),
        truck1_velocity_kph=_float_value(values, "Initial Truck #1 velocity"),
        truck2_velocity_kph=_float_value(values, "Initial Truck #2 velocity"),
        truck3_velocity_kph=_float_value(values, "Initial Truck #3 velocity"),
    )
    parameters = SimulationParameters(
        max_velocity_kph=_float_value(values, "Max velocity"),
        max_acceleration_mps2=_float_value(values, "Max acceleration"),
        max_red_deceleration_mps2=_float_value(values, "Max red deceleration"),
        minimum_gap_m=_float_value(values, "Minimum allowed gap distance"),
        maximum_gap_m=_float_value(values, "Maximum allowed gap distance"),
        red_distance_m=_float_value(values, "Red distance"),
        orange_distance_m=_float_value(values, "Orange distance"),
        orange_braking_mode=int(_float_value(values, "Orange braking mode", default=0.0)),
        time_headway_s=_float_value(values, "TimeHeadway", default=3.0),
        emergency_deceleration_mps2=_float_value(values, "Emergency deceleration", default=_float_value(values, "Max red deceleration")),
        start_moving_identification_delay_ms=_float_value(values, "Start moving identification delay"),
        distance_identification_delay_ms=_float_value(values, "Distance identification delay"),
        image_identification_loss_distance_m=_float_value(values, "Truck image identification loss distance"),
        image_identification_resume_distance_m=_float_value(values, "Truck image identification resume distance"),
        under_loss_following_velocity_kph=_float_value(values, "Under-loss following truck velocity"),
        under_loss_leading_velocity_kph=_float_value(values, "Under-loss leading truck velocity"),
        trucks_communicating=_bool_value(values, "Trucks communicating"),
        resume_by_distance=_bool_value(values, "Resume by distance", default=False),
        communication_latency_ms=_float_value(values, "Communication latency"),
        communication_reliability_percent=_float_value(values, "Communication reliability"),
        convoy_target_speed_kph=_float_value(values, "Convoy target speed"),
        target_gap_m=target_gap_m,
        road_type=_road_type_value(values, "Road type"),
        orange_deceleration_mps2=_float_value(values, "Orange deceleration"),
        green_acceleration_mps2=_float_value(values, "Green acceleration"),
        optimal_acceleration_mps2=_float_value(values, "Optimal acceleration"),
        simulation_time_step_s=_float_value(values, "Simulation time step"),
        output_resolution_s=_float_value(values, "Output table resolution"),
        start_moving_gap_m=_float_value(values, "Start moving gap", default=target_gap_m),
    )
    return LoadedParameters(initial_conditions=initial, simulation_parameters=parameters)


def _read_parameter_values(path: str | Path) -> dict[str, str]:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"Parameter", "Value"}
        fieldnames = set(reader.fieldnames or [])
        missing_columns = required_columns - fieldnames
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Parameter CSV is missing required columns: {missing}.")

        values = {row["Parameter"].strip(): row["Value"].strip() for row in reader if row.get("Parameter", "").strip()}

    return values


def _float_value(values: dict[str, str], key: str, default: float | None = None) -> float:
    value = values.get(key)
    if value in (None, ""):
        if default is not None:
            return default
        raise ValueError(f"Missing required parameter: {key}.")

    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"Parameter {key} must be numeric.") from error


def _bool_value(values: dict[str, str], key: str, default: bool | None = None) -> bool:
    if key not in values or values.get(key, "").strip() == "":
        if default is not None:
            return default
        raise ValueError(f"Missing required parameter: {key}.")
    value = values.get(key, "").strip().lower()
    if value in {"yes", "true", "1"}:
        return True
    if value in {"no", "false", "0"}:
        return False
    raise ValueError(f"Parameter {key} must be Yes or No.")


def _road_type_value(values: dict[str, str], key: str) -> RoadType:
    value = values.get(key, "").strip()
    try:
        return RoadType(value)
    except ValueError as error:
        valid_values = ", ".join(road.value for road in RoadType)
        raise ValueError(f"Parameter {key} must be one of: {valid_values}.") from error
