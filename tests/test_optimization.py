import csv
import math
import tempfile
import unittest
from pathlib import Path

from convoysim.optimization import (
    bulk_cost_function_names,
    bulk_parameter_names,
    generate_parameter_values,
    load_cost_function_weights_csv,
    load_optimization_candidates_csv,
    mean_convoy_gap,
    rms_follower_acceleration,
    rms_gap_error,
    rms_relative_speed,
    run_bulk_simulations_from_files,
    run_stage_b_optimization_from_files,
    ttc_violation_count,
)
from convoysim.simulation import SimulationResult, SimulationRow


EXAMPLE_PARAMETERS = Path("Inputs/stage_a_example_inputs/parameters.csv")
EXAMPLE_TIMELINE = Path("Inputs/stage_a_example_inputs/Nominal.csv")
EXAMPLE_BRAKING_TABLE = Path("Inputs/stage_a_example_inputs/braking_distance_table.csv")
EXAMPLE_SWEEP = Path("Inputs/stage_b_parameter_sweep.csv")
EXAMPLE_WEIGHTS = Path("CostFunctionWeights.csv")


class OptimizationTest(unittest.TestCase):
    def test_loads_example_optimization_candidates(self) -> None:
        candidates = load_optimization_candidates_csv(EXAMPLE_SWEEP)

        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0].name, "Baseline")
        self.assertGreater(candidates[0].orange_distance_m, 0.0)

    def test_runs_stage_b_optimization_and_writes_ranked_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "stage_b_optimization.csv"
            result = run_stage_b_optimization_from_files(
                EXAMPLE_PARAMETERS,
                EXAMPLE_TIMELINE,
                EXAMPLE_SWEEP,
                output_path,
                EXAMPLE_BRAKING_TABLE,
            )
            with output_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(result.rows), 3)
        self.assertEqual(len(rows), 3)
        self.assertIn("Score", rows[0])
        self.assertLessEqual(result.rows[0].score, result.rows[-1].score)

    def test_generates_inclusive_parameter_values(self) -> None:
        self.assertEqual(generate_parameter_values(1.0, 2.0, 0.5), (1.0, 1.5, 2.0))

    def test_loads_cost_function_weights(self) -> None:
        weights = load_cost_function_weights_csv(EXAMPLE_WEIGHTS)

        self.assertEqual(weights["Red braking count"], 200.0)
        self.assertEqual(weights["Accidents"], 200.0)

    def test_runs_bulk_simulations_and_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_bulk_simulations_from_files(
                EXAMPLE_PARAMETERS,
                (EXAMPLE_TIMELINE,),
                bulk_parameter_names()[0],
                1.0,
                1.5,
                0.5,
                bulk_cost_function_names()[0],
                EXAMPLE_BRAKING_TABLE,
                output_root=directory,
            )
            with result.results_csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))
            run_outputs_exist = all(Path(row.run_output_csv).exists() for row in result.rows)

        self.assertEqual(len(result.rows), 2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(result.results_csv_path.name.endswith("Bulk_Results.csv"))
        self.assertEqual({row.status for row in result.rows}, {"Completed"})
        self.assertTrue(run_outputs_exist)
        self.assertIn("Total_Weighted_Cost", rows[0])
        self.assertIn("Total_Red_Braking_Count", rows[0])
        self.assertIn("Total_Accident_Count", rows[0])

    def test_runs_bulk_simulations_with_accidents_cost_function(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_bulk_simulations_from_files(
                EXAMPLE_PARAMETERS,
                (EXAMPLE_TIMELINE,),
                bulk_parameter_names()[0],
                1.0,
                1.0,
                1.0,
                "Accidents",
                EXAMPLE_BRAKING_TABLE,
                output_root=directory,
            )
            with result.results_csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(result.rows), 1)
        self.assertIn("Accidents", bulk_cost_function_names())
        self.assertEqual(result.rows[0].cost_function, "Accidents")
        self.assertEqual(float(rows[0]["Total_Weighted_Cost"]), result.rows[0].total_accident_count * 200.0)

    def test_runs_bulk_simulations_with_multiple_cost_functions(self) -> None:
        cost_functions = bulk_cost_function_names()
        with tempfile.TemporaryDirectory() as directory:
            result = run_bulk_simulations_from_files(
                EXAMPLE_PARAMETERS,
                (EXAMPLE_TIMELINE,),
                bulk_parameter_names()[0],
                1.0,
                1.0,
                1.0,
                cost_functions,
                EXAMPLE_BRAKING_TABLE,
                output_root=directory,
            )
            with result.results_csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))
            weights_copy_exists = (result.output_dir / "CostFunctionWeights_Used.csv").exists()

        self.assertEqual(result.cost_functions, cost_functions)
        self.assertEqual(result.rows[0].cost_function, ", ".join(cost_functions))
        row = result.rows[0]
        expected_weighted_cost = (
            row.total_red_braking_count * 1.0
            + row.total_accident_count * 200.0
            + row.rms_gap_error_m * 1.0
            + row.ttc_violation_count * 1.0
            + row.rms_relative_speed_kph * 1.0
            + row.mean_convoy_gap_m * 1.0
            + row.rms_follower_acceleration_mps2 * 1.0
        )
        self.assertAlmostEqual(result.rows[0].total_weighted_cost, expected_weighted_cost, places=9)
        self.assertIn("Total_Red_Braking_Count", rows[0])
        self.assertIn("Total_Accident_Count", rows[0])
        self.assertTrue(weights_copy_exists)

    def test_bulk_weighted_cost_uses_only_selected_cost_functions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            weights_path = Path(directory) / "weights.csv"
            weights_path.write_text("Cost_Function,Weight\nRed braking count,3.0\nAccidents,1000.0\n", encoding="utf-8")
            result = run_bulk_simulations_from_files(
                EXAMPLE_PARAMETERS,
                (EXAMPLE_TIMELINE,),
                bulk_parameter_names()[0],
                1.0,
                1.0,
                1.0,
                "Red braking count",
                EXAMPLE_BRAKING_TABLE,
                weights_path,
                output_root=directory,
            )

        self.assertEqual(result.rows[0].total_weighted_cost, result.rows[0].total_red_braking_count * 3.0)

    def test_bulk_missing_selected_cost_weight_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            weights_path = Path(directory) / "weights.csv"
            weights_path.write_text("Cost_Function,Weight\nRed braking count,1.0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Accidents"):
                run_bulk_simulations_from_files(
                    EXAMPLE_PARAMETERS,
                    (EXAMPLE_TIMELINE,),
                    bulk_parameter_names()[0],
                    1.0,
                    1.0,
                    1.0,
                    ("Red braking count", "Accidents"),
                    EXAMPLE_BRAKING_TABLE,
                    weights_path,
                    output_root=directory,
                )

    def test_bulk_failed_run_writes_failure_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_scenario = Path(directory) / "missing.csv"
            result = run_bulk_simulations_from_files(
                EXAMPLE_PARAMETERS,
                (missing_scenario,),
                bulk_parameter_names()[0],
                1.0,
                1.0,
                1.0,
                bulk_cost_function_names()[0],
                EXAMPLE_BRAKING_TABLE,
                output_root=directory,
            )
            with result.results_csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(result.rows[0].status, "Failed")
        self.assertIn("Failure_Reason", rows[0])
        self.assertTrue(rows[0]["Failure_Reason"])


def _make_row(
    truck2_gap_m: float = 10.0,
    truck3_gap_m: float = 10.0,
    truck2_relative_velocity_kph: float = 0.0,
    truck3_relative_velocity_kph: float = 0.0,
    truck2_acceleration_mps2: float = 0.0,
    truck3_acceleration_mps2: float = 0.0,
) -> SimulationRow:
    return SimulationRow(
        time_s=0.0,
        truck1_position_m=30.0,
        truck2_position_m=20.0,
        truck3_position_m=10.0,
        truck2_gap_m=truck2_gap_m,
        truck3_gap_m=truck3_gap_m,
        gap2_violation=False,
        gap3_violation=False,
        truck1_velocity_kph=10.0,
        truck2_velocity_kph=10.0,
        truck3_velocity_kph=10.0,
        truck1_acceleration_mps2=0.0,
        truck2_acceleration_mps2=truck2_acceleration_mps2,
        truck3_acceleration_mps2=truck3_acceleration_mps2,
        truck2_state="FOLLOWING_CRUISING",
        truck3_state="FOLLOWING_CRUISING",
        truck2_command="",
        truck3_command="",
        truck2_actual_gap_m=truck2_gap_m,
        truck2_measured_gap_m=truck2_gap_m,
        truck3_actual_gap_m=truck3_gap_m,
        truck3_measured_gap_m=truck3_gap_m,
        truck2_tracking_status="Tracking",
        truck3_tracking_status="Tracking",
        truck2_relative_velocity_kph=truck2_relative_velocity_kph,
        truck3_relative_velocity_kph=truck3_relative_velocity_kph,
        communication_message="",
        communication_status="",
        violation_type_truck2="",
        violation_type_truck3="",
        stop_reason_truck2="",
        stop_reason_truck3="",
    )


def _make_sim(*rows: SimulationRow) -> SimulationResult:
    return SimulationResult(rows=rows)


class MetricFunctionTest(unittest.TestCase):
    def test_rms_gap_error_perfect(self) -> None:
        sim = _make_sim(_make_row(truck2_gap_m=10.0, truck3_gap_m=10.0))
        self.assertAlmostEqual(rms_gap_error(sim, target_gap_m=10.0), 0.0)

    def test_rms_gap_error_constant_offset(self) -> None:
        sim = _make_sim(
            _make_row(truck2_gap_m=12.0, truck3_gap_m=12.0),
            _make_row(truck2_gap_m=12.0, truck3_gap_m=12.0),
        )
        self.assertAlmostEqual(rms_gap_error(sim, target_gap_m=10.0), 2.0)

    def test_rms_gap_error_empty(self) -> None:
        self.assertEqual(rms_gap_error(_make_sim(), target_gap_m=10.0), 0.0)

    def test_ttc_violation_count_no_closing(self) -> None:
        sim = _make_sim(_make_row(truck2_relative_velocity_kph=-2.0, truck3_relative_velocity_kph=-2.0))
        self.assertEqual(ttc_violation_count(sim), 0)

    def test_ttc_violation_count_zero_relative_speed(self) -> None:
        sim = _make_sim(_make_row(truck2_relative_velocity_kph=0.0, truck3_relative_velocity_kph=0.0))
        self.assertEqual(ttc_violation_count(sim), 0)

    def test_ttc_violation_count_fast_closing(self) -> None:
        # gap=10m, rel_v=36kph=10m/s → TTC=1.0s < 2.0s threshold → violation
        sim = _make_sim(_make_row(truck2_gap_m=10.0, truck2_relative_velocity_kph=36.0))
        self.assertGreater(ttc_violation_count(sim), 0)

    def test_ttc_violation_count_slow_closing_no_violation(self) -> None:
        # gap=10m, rel_v=3.6kph=1m/s → TTC=10s > 2.0s threshold → no violation
        sim = _make_sim(_make_row(truck2_gap_m=10.0, truck2_relative_velocity_kph=3.6))
        self.assertEqual(ttc_violation_count(sim), 0)

    def test_rms_relative_speed_zero(self) -> None:
        sim = _make_sim(_make_row(truck2_relative_velocity_kph=0.0, truck3_relative_velocity_kph=0.0))
        self.assertAlmostEqual(rms_relative_speed(sim), 0.0)

    def test_rms_relative_speed_constant(self) -> None:
        sim = _make_sim(
            _make_row(truck2_relative_velocity_kph=3.0, truck3_relative_velocity_kph=3.0),
            _make_row(truck2_relative_velocity_kph=3.0, truck3_relative_velocity_kph=3.0),
        )
        self.assertAlmostEqual(rms_relative_speed(sim), 3.0)

    def test_mean_convoy_gap_uniform(self) -> None:
        sim = _make_sim(
            _make_row(truck2_gap_m=8.0, truck3_gap_m=12.0),
            _make_row(truck2_gap_m=8.0, truck3_gap_m=12.0),
        )
        self.assertAlmostEqual(mean_convoy_gap(sim), 20.0)

    def test_mean_convoy_gap_empty(self) -> None:
        self.assertEqual(mean_convoy_gap(_make_sim()), 0.0)

    def test_rms_follower_acceleration_zero(self) -> None:
        sim = _make_sim(_make_row(truck2_acceleration_mps2=0.0, truck3_acceleration_mps2=0.0))
        self.assertAlmostEqual(rms_follower_acceleration(sim), 0.0)

    def test_rms_follower_acceleration_constant(self) -> None:
        sim = _make_sim(
            _make_row(truck2_acceleration_mps2=2.0, truck3_acceleration_mps2=2.0),
            _make_row(truck2_acceleration_mps2=2.0, truck3_acceleration_mps2=2.0),
        )
        self.assertAlmostEqual(rms_follower_acceleration(sim), 2.0)

    def test_bulk_results_csv_has_new_metric_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = run_bulk_simulations_from_files(
                EXAMPLE_PARAMETERS,
                (EXAMPLE_TIMELINE,),
                bulk_parameter_names()[0],
                1.0,
                1.0,
                1.0,
                bulk_cost_function_names()[0],
                EXAMPLE_BRAKING_TABLE,
                output_root=directory,
            )
            with result.results_csv_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertIn("RMS_Gap_Error_m", rows[0])
        self.assertIn("TTC_Violation_Count", rows[0])
        self.assertIn("RMS_Relative_Speed_kph", rows[0])
        self.assertIn("Mean_Convoy_Gap_m", rows[0])
        self.assertIn("RMS_Follower_Acceleration_mps2", rows[0])
        self.assertGreater(float(rows[0]["RMS_Gap_Error_m"]), 0.0)
        self.assertGreaterEqual(int(rows[0]["TTC_Violation_Count"]), 0)
        self.assertGreater(float(rows[0]["Mean_Convoy_Gap_m"]), 0.0)


if __name__ == "__main__":
    unittest.main()
