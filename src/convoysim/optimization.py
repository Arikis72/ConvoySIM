"""Stage B parameter sweep and bulk simulation optimization."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
import argparse
import csv
import re

from convoysim.braking import BrakingDistanceTable
from convoysim.models import InitialConditions, SimulationParameters
from convoysim.parameters import load_parameters_csv
from convoysim.scenario_timeline import ScenarioTimeline
from convoysim.simulation import SimulationResult, run_basic_simulation


_SWEEP_PARAMETER_MAP = {
    "Orange deceleration": "orange_deceleration_mps2",
    "Orange distance": "orange_distance_m",
    "Green acceleration": "green_acceleration_mps2",
    "Start moving gap": "start_moving_gap_m",
    "Optimal acceleration": "optimal_acceleration_mps2",
    "Target gap": "target_gap_m",
}

_COST_FUNCTION_RED_BRAKING = "Red braking count"
_COST_FUNCTION_ACCIDENTS = "Accidents"
DEFAULT_COST_FUNCTION_WEIGHTS_PATH = "CostFunctionWeights.csv"
_WEIGHTS_USED_FILENAME = "CostFunctionWeights_Used.csv"
_BULK_RESULT_COLUMNS = (
    "Parameter",
    "Parameter_Value",
    "Cost_Function",
    "Scenario",
    "Status",
    "Total_Weighted_Cost",
    "Truck2_Red_Braking_Count",
    "Truck3_Red_Braking_Count",
    "Total_Red_Braking_Count",
    "Truck2_Accident_Count",
    "Truck3_Accident_Count",
    "Total_Accident_Count",
    "Run_Output_CSV",
    "Failure_Reason",
)


@dataclass(frozen=True)
class OptimizationCandidate:
    name: str
    orange_deceleration_mps2: float
    orange_distance_m: float
    green_acceleration_mps2: float
    start_moving_gap_m: float
    optimal_acceleration_mps2: float
    target_gap_m: float

    def apply_to(self, parameters: SimulationParameters) -> SimulationParameters:
        return replace(
            parameters,
            orange_deceleration_mps2=self.orange_deceleration_mps2,
            orange_distance_m=self.orange_distance_m,
            green_acceleration_mps2=self.green_acceleration_mps2,
            start_moving_gap_m=self.start_moving_gap_m,
            optimal_acceleration_mps2=self.optimal_acceleration_mps2,
            target_gap_m=self.target_gap_m,
        )


@dataclass(frozen=True)
class OptimizationResultRow:
    candidate: OptimizationCandidate
    hard_constraints_passed: bool
    collision_count: int
    minimum_gap_violation_count: int
    full_stop_count: int
    oscillation_count: int
    score: float


@dataclass(frozen=True)
class OptimizationResult:
    rows: tuple[OptimizationResultRow, ...]

    @property
    def best_candidate(self) -> OptimizationResultRow | None:
        return self.rows[0] if self.rows else None

    def write_csv(self, path: str | Path) -> None:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(_OUTPUT_COLUMNS))
            writer.writeheader()
            for row in self.rows:
                writer.writerow(_optimization_row_to_csv(row))


@dataclass(frozen=True)
class BulkSimulationRunRow:
    parameter_name: str
    parameter_value: float
    cost_function: str
    scenario_name: str
    status: str
    total_weighted_cost: float
    truck2_red_braking_count: int
    truck3_red_braking_count: int
    total_red_braking_count: int
    truck2_accident_count: int
    truck3_accident_count: int
    total_accident_count: int
    run_output_csv: str
    failure_reason: str = ""


@dataclass(frozen=True)
class BulkSimulationResult:
    output_dir: Path
    rows: tuple[BulkSimulationRunRow, ...]
    cost_functions: tuple[str, ...] = (_COST_FUNCTION_RED_BRAKING,)
    cost_function_weights: dict[str, float] | None = None
    cancelled: bool = False

    @property
    def results_csv_path(self) -> Path:
        return self.output_dir / "Bulk_Results.csv"

    def write_csv(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with self.results_csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(_BULK_RESULT_COLUMNS))
            writer.writeheader()
            for row in self.rows:
                writer.writerow(_bulk_row_to_csv(row))
        if self.cost_function_weights is not None:
            _write_cost_function_weights_csv(self.output_dir / _WEIGHTS_USED_FILENAME, self.cost_function_weights)


def load_optimization_candidates_csv(path: str | Path) -> tuple[OptimizationCandidate, ...]:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"Scenario", *set(_SWEEP_PARAMETER_MAP)}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Optimization sweep CSV is missing required columns: {missing}.")
        return tuple(_candidate_from_row(row, index + 2) for index, row in enumerate(reader))


def run_stage_b_optimization(
    initial: InitialConditions,
    base_parameters: SimulationParameters,
    timeline: ScenarioTimeline,
    candidates: tuple[OptimizationCandidate, ...],
    braking_table: BrakingDistanceTable | None = None,
) -> OptimizationResult:
    result_rows = []
    for candidate in candidates:
        parameters = candidate.apply_to(base_parameters)
        simulation = run_basic_simulation(initial, parameters, timeline, braking_table)
        result_rows.append(_evaluate_candidate(candidate, simulation))

    ordered_rows = tuple(sorted(result_rows, key=lambda row: (not row.hard_constraints_passed, row.score, row.candidate.name)))
    return OptimizationResult(rows=ordered_rows)


def run_stage_b_optimization_from_files(
    parameters_path: str | Path,
    scenario_path: str | Path,
    sweep_path: str | Path,
    output_path: str | Path,
    braking_table_path: str | Path | None = None,
) -> OptimizationResult:
    loaded = load_parameters_csv(parameters_path)
    timeline = ScenarioTimeline.from_csv(scenario_path)
    candidates = load_optimization_candidates_csv(sweep_path)
    braking_table = BrakingDistanceTable.from_csv(braking_table_path) if braking_table_path is not None else None
    result = run_stage_b_optimization(
        loaded.initial_conditions,
        loaded.simulation_parameters,
        timeline,
        candidates,
        braking_table,
    )
    result.write_csv(output_path)
    return result


def bulk_parameter_names() -> tuple[str, ...]:
    return tuple(_SWEEP_PARAMETER_MAP)


def bulk_cost_function_names() -> tuple[str, ...]:
    return (_COST_FUNCTION_RED_BRAKING, _COST_FUNCTION_ACCIDENTS)


def load_cost_function_weights_csv(path: str | Path) -> dict[str, float]:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"Cost_Function", "Weight"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Cost function weights CSV is missing required columns: {missing}.")

        weights: dict[str, float] = {}
        supported = set(bulk_cost_function_names())
        for row_number, row in enumerate(reader, start=2):
            cost_function = row.get("Cost_Function", "").strip()
            if not cost_function:
                raise ValueError(f"Cost function weights row {row_number} must include Cost_Function.")
            if cost_function not in supported:
                raise ValueError(f"Cost function weights row {row_number} has unsupported cost function: {cost_function}.")
            if cost_function in weights:
                raise ValueError(f"Cost function weights row {row_number} duplicates {cost_function}.")
            weights[cost_function] = _cost_weight_cell(row, row_number)
        return weights


def generate_parameter_values(minimum: float, maximum: float, step: float) -> tuple[float, ...]:
    if step == 0:
        raise ValueError("Parameter step must not be zero.")
    if minimum < maximum and step < 0:
        raise ValueError("Parameter step must be positive when minimum is less than maximum.")
    if minimum > maximum and step > 0:
        raise ValueError("Parameter step must be negative when minimum is greater than maximum.")

    values: list[float] = []
    value = minimum
    epsilon = abs(step) / 1_000_000.0
    if step > 0:
        while value <= maximum + epsilon:
            values.append(round(value, 10))
            value += step
    else:
        while value >= maximum - epsilon:
            values.append(round(value, 10))
            value += step
    return tuple(values)


def run_bulk_simulations_from_files(
    parameters_path: str | Path,
    scenario_paths: tuple[str | Path, ...],
    parameter_name: str,
    minimum: float,
    maximum: float,
    step: float,
    cost_function: str | tuple[str, ...] = _COST_FUNCTION_RED_BRAKING,
    braking_table_path: str | Path | None = None,
    cost_weights_path: str | Path = DEFAULT_COST_FUNCTION_WEIGHTS_PATH,
    output_root: str | Path = "outputs",
    run_time: datetime | None = None,
    progress_callback: object | None = None,
    should_cancel: object | None = None,
) -> BulkSimulationResult:
    if parameter_name not in _SWEEP_PARAMETER_MAP:
        raise ValueError(f"Unsupported bulk simulation parameter: {parameter_name}.")
    cost_functions = _normalize_cost_functions(cost_function)
    if not scenario_paths:
        raise ValueError("Select at least one scenario for bulk simulation.")

    cost_function_weights = load_cost_function_weights_csv(cost_weights_path)
    _validate_selected_cost_weights(cost_functions, cost_function_weights)
    loaded = load_parameters_csv(parameters_path)
    braking_table = BrakingDistanceTable.from_csv(braking_table_path) if braking_table_path is not None else None
    parameter_values = generate_parameter_values(minimum, maximum, step)
    cost_name = "_".join(_safe_path_part(name) for name in cost_functions)
    output_dir = Path(output_root) / f"{cost_name}_{(run_time or datetime.now()).strftime('%d%m%y_%H%M')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows: list[BulkSimulationRunRow] = []
    total_runs = len(parameter_values) * len(scenario_paths)
    completed_runs = 0
    cancelled = False
    for parameter_value in parameter_values:
        for scenario_path in scenario_paths:
            if _callback_bool(should_cancel):
                cancelled = True
                break
            scenario = Path(scenario_path)
            run_output = output_dir / _bulk_run_output_name(scenario.stem, parameter_name, parameter_value)
            try:
                timeline = ScenarioTimeline.from_csv(scenario)
                parameters = _apply_bulk_parameter(loaded.simulation_parameters, parameter_name, parameter_value)
                simulation = run_basic_simulation(loaded.initial_conditions, parameters, timeline, braking_table)
                simulation.write_csv(run_output)
                truck2_count, truck3_count = red_braking_event_counts(simulation)
                truck2_accidents, truck3_accidents = accident_event_counts(simulation)
                total_red_braking_count = truck2_count + truck3_count
                total_accident_count = truck2_accidents + truck3_accidents
                total_weighted_cost = _total_weighted_cost(
                    cost_functions,
                    cost_function_weights,
                    total_red_braking_count,
                    total_accident_count,
                )
                rows.append(
                    BulkSimulationRunRow(
                        parameter_name=parameter_name,
                        parameter_value=parameter_value,
                        cost_function=", ".join(cost_functions),
                        scenario_name=scenario.stem,
                        status="Completed",
                        total_weighted_cost=total_weighted_cost,
                        truck2_red_braking_count=truck2_count,
                        truck3_red_braking_count=truck3_count,
                        total_red_braking_count=total_red_braking_count,
                        truck2_accident_count=truck2_accidents,
                        truck3_accident_count=truck3_accidents,
                        total_accident_count=total_accident_count,
                        run_output_csv=str(run_output),
                    )
                )
            except Exception as error:  # noqa: BLE001 - bulk runs keep going after one failed scenario.
                rows.append(
                    BulkSimulationRunRow(
                        parameter_name=parameter_name,
                        parameter_value=parameter_value,
                        cost_function=", ".join(cost_functions),
                        scenario_name=scenario.stem,
                        status="Failed",
                        total_weighted_cost=0.0,
                        truck2_red_braking_count=0,
                        truck3_red_braking_count=0,
                        total_red_braking_count=0,
                        truck2_accident_count=0,
                        truck3_accident_count=0,
                        total_accident_count=0,
                        run_output_csv="",
                        failure_reason=str(error),
                    )
                )
            completed_runs += 1
            _call_progress(progress_callback, completed_runs, total_runs, scenario.stem, parameter_value)
        if cancelled:
            break

    selected_weights = {name: cost_function_weights[name] for name in cost_functions}
    result = BulkSimulationResult(
        output_dir=output_dir,
        rows=tuple(rows),
        cost_functions=cost_functions,
        cost_function_weights=selected_weights,
        cancelled=cancelled,
    )
    result.write_csv()
    return result


def red_braking_event_counts(simulation: SimulationResult) -> tuple[int, int]:
    return (
        _red_braking_event_count(tuple(row.truck2_state for row in simulation.rows)),
        _red_braking_event_count(tuple(row.truck3_state for row in simulation.rows)),
    )


def accident_event_counts(simulation: SimulationResult) -> tuple[int, int]:
    return (
        _accident_event_count(tuple(row.truck2_gap_m for row in simulation.rows)),
        _accident_event_count(tuple(row.truck3_gap_m for row in simulation.rows)),
    )


def _candidate_from_row(row: dict[str, str], row_number: int) -> OptimizationCandidate:
    name = row["Scenario"].strip()
    if not name:
        raise ValueError(f"Optimization sweep row {row_number} must include Scenario.")
    return OptimizationCandidate(
        name=name,
        orange_deceleration_mps2=_float_cell(row, "Orange deceleration", row_number),
        orange_distance_m=_float_cell(row, "Orange distance", row_number),
        green_acceleration_mps2=_float_cell(row, "Green acceleration", row_number),
        start_moving_gap_m=_float_cell(row, "Start moving gap", row_number),
        optimal_acceleration_mps2=_float_cell(row, "Optimal acceleration", row_number),
        target_gap_m=_float_cell(row, "Target gap", row_number),
    )


def _float_cell(row: dict[str, str], column: str, row_number: int) -> float:
    value = row.get(column, "").strip()
    if not value:
        raise ValueError(f"Optimization sweep row {row_number} is missing {column}.")
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"Optimization sweep row {row_number} column {column} must be numeric.") from error


def _cost_weight_cell(row: dict[str, str], row_number: int) -> float:
    value = row.get("Weight", "").strip()
    if not value:
        raise ValueError(f"Cost function weights row {row_number} is missing Weight.")
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"Cost function weights row {row_number} column Weight must be numeric.") from error


def _evaluate_candidate(candidate: OptimizationCandidate, simulation: SimulationResult) -> OptimizationResultRow:
    collision_count = 0
    minimum_gap_violation_count = 0
    full_stop_count = 0
    for row in simulation.rows:
        if row.truck2_gap_m <= 0 or row.truck3_gap_m <= 0:
            collision_count += 1
        if "Minimum gap violation" in row.violation_type_truck2 or "Minimum gap violation" in row.violation_type_truck3:
            minimum_gap_violation_count += 1
        if row.time_s > 0 and (row.truck2_velocity_kph <= 1e-9 or row.truck3_velocity_kph <= 1e-9):
            full_stop_count += 1

    oscillation_count = _acceleration_sign_changes(
        tuple(row.truck2_acceleration_mps2 for row in simulation.rows)
    ) + _acceleration_sign_changes(tuple(row.truck3_acceleration_mps2 for row in simulation.rows))
    hard_constraints_passed = collision_count == 0 and minimum_gap_violation_count == 0
    score = (
        collision_count * 1_000_000.0
        + minimum_gap_violation_count * 500_000.0
        + full_stop_count * 1_000.0
        + oscillation_count * 10.0
    )
    return OptimizationResultRow(
        candidate=candidate,
        hard_constraints_passed=hard_constraints_passed,
        collision_count=collision_count,
        minimum_gap_violation_count=minimum_gap_violation_count,
        full_stop_count=full_stop_count,
        oscillation_count=oscillation_count,
        score=score,
    )


def _apply_bulk_parameter(parameters: SimulationParameters, parameter_name: str, value: float) -> SimulationParameters:
    return replace(parameters, **{_SWEEP_PARAMETER_MAP[parameter_name]: value})


def _red_braking_event_count(states: tuple[str, ...]) -> int:
    count = 0
    was_red = False
    for state in states:
        is_red = state == "FOLLOWING_RED_BRAKING_TO_STOP"
        if is_red and not was_red:
            count += 1
        was_red = is_red
    return count


def _accident_event_count(gaps_m: tuple[float, ...]) -> int:
    count = 0
    was_accident = False
    for gap_m in gaps_m:
        is_accident = gap_m <= 0.0
        if is_accident and not was_accident:
            count += 1
        was_accident = is_accident
    return count


def _selected_cost_value(cost_function: str, total_red_braking_count: int, total_accident_count: int) -> int:
    if cost_function == _COST_FUNCTION_ACCIDENTS:
        return total_accident_count
    return total_red_braking_count


def bulk_row_cost_value(row: BulkSimulationRunRow, cost_function: str) -> int:
    return _selected_cost_value(cost_function, row.total_red_braking_count, row.total_accident_count)


def _total_weighted_cost(
    cost_functions: tuple[str, ...],
    cost_function_weights: dict[str, float],
    total_red_braking_count: int,
    total_accident_count: int,
) -> float:
    return sum(
        _selected_cost_value(cost_function, total_red_braking_count, total_accident_count) * cost_function_weights[cost_function]
        for cost_function in cost_functions
    )


def _validate_selected_cost_weights(cost_functions: tuple[str, ...], cost_function_weights: dict[str, float]) -> None:
    missing = [name for name in cost_functions if name not in cost_function_weights]
    if missing:
        raise ValueError(f"Cost function weights CSV is missing selected cost function weights: {', '.join(missing)}.")


def _write_cost_function_weights_csv(path: str | Path, cost_function_weights: dict[str, float]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=("Cost_Function", "Weight"))
        writer.writeheader()
        for cost_function, weight in cost_function_weights.items():
            writer.writerow({"Cost_Function": cost_function, "Weight": f"{weight:.10g}"})


def _normalize_cost_functions(cost_function: str | tuple[str, ...]) -> tuple[str, ...]:
    cost_functions = (cost_function,) if isinstance(cost_function, str) else tuple(cost_function)
    if not cost_functions:
        raise ValueError("Select at least one cost function for bulk simulation.")
    supported = set(bulk_cost_function_names())
    unsupported = [name for name in cost_functions if name not in supported]
    if unsupported:
        raise ValueError(f"Unsupported cost function: {', '.join(unsupported)}.")
    return cost_functions


def _bulk_run_output_name(scenario_name: str, parameter_name: str, parameter_value: float) -> str:
    value_text = f"{parameter_value:.6f}".rstrip("0").rstrip(".").replace("-", "minus").replace(".", "p")
    return f"{_safe_path_part(scenario_name)}_{_safe_path_part(parameter_name)}_{value_text}.csv"


def _safe_path_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip())
    return cleaned.strip("_") or "bulk"


def _bulk_row_to_csv(row: BulkSimulationRunRow) -> dict[str, str]:
    return {
        "Parameter": row.parameter_name,
        "Parameter_Value": f"{row.parameter_value:.10g}",
        "Cost_Function": row.cost_function,
        "Scenario": row.scenario_name,
        "Status": row.status,
        "Total_Weighted_Cost": f"{row.total_weighted_cost:.10g}",
        "Truck2_Red_Braking_Count": str(row.truck2_red_braking_count),
        "Truck3_Red_Braking_Count": str(row.truck3_red_braking_count),
        "Total_Red_Braking_Count": str(row.total_red_braking_count),
        "Truck2_Accident_Count": str(row.truck2_accident_count),
        "Truck3_Accident_Count": str(row.truck3_accident_count),
        "Total_Accident_Count": str(row.total_accident_count),
        "Run_Output_CSV": row.run_output_csv,
        "Failure_Reason": row.failure_reason if row.status == "Failed" else "",
    }


def _callback_bool(callback: object | None) -> bool:
    return bool(callback() if callable(callback) else False)


def _call_progress(
    callback: object | None,
    completed_runs: int,
    total_runs: int,
    scenario_name: str,
    parameter_value: float,
) -> None:
    if callable(callback):
        callback(completed_runs, total_runs, scenario_name, parameter_value)


def _acceleration_sign_changes(values: tuple[float, ...]) -> int:
    changes = 0
    previous_sign = 0
    for value in values:
        if abs(value) < 1e-9:
            continue
        current_sign = 1 if value > 0 else -1
        if previous_sign and current_sign != previous_sign:
            changes += 1
        previous_sign = current_sign
    return changes


def _optimization_row_to_csv(row: OptimizationResultRow) -> dict[str, str]:
    return {
        "Scenario": row.candidate.name,
        "Hard_Constraints_Passed": "Yes" if row.hard_constraints_passed else "No",
        "Collision_Count": str(row.collision_count),
        "Minimum_Gap_Violation_Count": str(row.minimum_gap_violation_count),
        "Full_Stop_Count": str(row.full_stop_count),
        "Oscillation_Count": str(row.oscillation_count),
        "Score": f"{row.score:.3f}",
        "Orange_Deceleration_mps2": f"{row.candidate.orange_deceleration_mps2:.3f}",
        "Orange_Distance_m": f"{row.candidate.orange_distance_m:.3f}",
        "Green_Acceleration_mps2": f"{row.candidate.green_acceleration_mps2:.3f}",
        "Start_Moving_Gap_m": f"{row.candidate.start_moving_gap_m:.3f}",
        "Optimal_Acceleration_mps2": f"{row.candidate.optimal_acceleration_mps2:.3f}",
        "Target_Gap_m": f"{row.candidate.target_gap_m:.3f}",
    }


_OUTPUT_COLUMNS = (
    "Scenario",
    "Hard_Constraints_Passed",
    "Collision_Count",
    "Minimum_Gap_Violation_Count",
    "Full_Stop_Count",
    "Oscillation_Count",
    "Score",
    "Orange_Deceleration_mps2",
    "Orange_Distance_m",
    "Green_Acceleration_mps2",
    "Start_Moving_Gap_m",
    "Optimal_Acceleration_mps2",
    "Target_Gap_m",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a Stage B ConvoySIM parameter sweep.")
    parser.add_argument("--parameters", default="Inputs/stage_a_example_inputs/parameters.csv")
    parser.add_argument("--scenario", default="Inputs/stage_a_example_inputs/scenario_timeline.csv")
    parser.add_argument("--braking-table", default="Inputs/stage_a_example_inputs/braking_distance_table.csv")
    parser.add_argument("--sweep", default="Inputs/stage_b_parameter_sweep.csv")
    parser.add_argument("--output", default="outputs/stage_b_optimization.csv")
    args = parser.parse_args()

    result = run_stage_b_optimization_from_files(
        args.parameters,
        args.scenario,
        args.sweep,
        args.output,
        args.braking_table,
    )
    best = result.best_candidate
    print(f"Wrote {len(result.rows)} optimization rows to {args.output}")
    if best is not None:
        print(f"Best candidate: {best.candidate.name} (score {best.score:.3f})")


if __name__ == "__main__":
    main()
