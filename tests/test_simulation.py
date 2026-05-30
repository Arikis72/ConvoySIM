import csv
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from convoysim.braking import BrakingDistanceTable
from convoysim.models import InitialConditions, SimulationParameters
from convoysim.parameters import load_parameters_csv
from convoysim.scenario_timeline import ImageEvent, ScenarioTimeline, ScenarioTimelineRow
from convoysim.simulation import FollowerState, run_basic_simulation, run_basic_simulation_from_files


EXAMPLE_PARAMETERS = Path("Inputs/stage_a_example_inputs/parameters.csv")
EXAMPLE_TIMELINE = Path("Inputs/stage_a_example_inputs/scenario_timeline.csv")
TRUCK2_LONG_LOSS_TIMELINE = Path("Inputs/stage_a_example_inputs/scenario_timeline_truck2longloss.csv")
EXAMPLE_BRAKING_TABLE = Path("Inputs/stage_a_example_inputs/braking_distance_table.csv")


class SimulationTest(unittest.TestCase):
    def test_runs_basic_simulation_from_example_inputs(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        timeline = ScenarioTimeline.from_csv(EXAMPLE_TIMELINE)
        braking_table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)

        result = run_basic_simulation(loaded.initial_conditions, loaded.simulation_parameters, timeline, braking_table)

        self.assertEqual(result.rows[0].time_s, 0.0)
        self.assertEqual(result.rows[-1].time_s, 60.0)
        self.assertGreater(len(result.rows), 10)
        self.assertTrue(any(row.truck2_tracking_status == "Lost" for row in result.rows))
        self.assertTrue(any(row.truck3_tracking_status == "Lost" for row in result.rows))

    def test_writes_basic_simulation_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "stage_a_basic_output.csv"
            log_output_path = Path(directory) / "stage_a_basic_log.csv"

            result = run_basic_simulation_from_files(
                EXAMPLE_PARAMETERS,
                EXAMPLE_TIMELINE,
                output_path,
                EXAMPLE_BRAKING_TABLE,
                log_output_path,
            )

            with output_path.open(newline="", encoding="utf-8") as csv_file:
                rows = list(csv.DictReader(csv_file))
            with log_output_path.open(newline="", encoding="utf-8") as csv_file:
                log_rows = list(csv.DictReader(csv_file))

        self.assertEqual(len(rows), len(result.rows))
        self.assertEqual(len(log_rows), len(result.logs))
        self.assertIn("Truck2_Gap_m", rows[0])
        self.assertIn("Truck3_State", rows[0])
        self.assertIn("Truck2_Actual_Gap_m", rows[0])
        self.assertIn("Truck2_Measured_Gap_m", rows[0])
        self.assertIn("Truck3_Actual_Gap_m", rows[0])
        self.assertIn("Truck3_Measured_Gap_m", rows[0])
        self.assertIn("Truck2_Relative_Velocity_kph", rows[0])
        self.assertIn("Truck3_Relative_Velocity_kph", rows[0])
        self.assertIn("Truck1_State", rows[0])
        self.assertIn("Truck2_State", rows[0])
        self.assertIn("Truck3_State", rows[0])
        self.assertIn("Truck1_Command", rows[0])
        self.assertIn("Truck2_Command", rows[0])
        self.assertIn("Truck3_Command", rows[0])
        self.assertIn("Truck2_Loss_Source", rows[0])
        self.assertIn("Truck3_Loss_Source", rows[0])
        self.assertIn("Truck2_Loss_Target_Rear_m", rows[0])
        self.assertIn("Truck3_Loss_Target_Rear_m", rows[0])
        self.assertIn("Stop_Reason_Truck2", rows[0])
        self.assertIn("Stop_Reason_Truck3", rows[0])
        self.assertIn("Communication_Message", rows[0])
        self.assertIn("Communication_Status", rows[0])

    def test_records_safety_lock_after_waiting_stopped_at_lost_target(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(
            loaded.initial_conditions,
            truck1_velocity_kph=10.0,
            truck2_velocity_kph=10.0,
        )
        parameters = replace(
            loaded.simulation_parameters,
            output_resolution_s=1.0,
        )
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=1.0, truck2_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=70.0, truck1_velocity_kph=10.0),
            )
        )

        result = run_basic_simulation(initial, parameters, timeline)

        self.assertTrue(any(row.stop_reason_truck2 == "Safety Lock" for row in result.rows))
        self.assertTrue(any("Safety Lock" in row.violation_type_truck2 for row in result.rows))

    def test_distance_resume_is_disabled_by_default_until_resume_event(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        parameters = replace(loaded.simulation_parameters, output_resolution_s=1.0)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=0.0),
                ScenarioTimelineRow(time_s=1.0, truck2_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=10.0, truck2_image_event=ImageEvent.RESUME),
                ScenarioTimelineRow(time_s=12.0, truck1_velocity_kph=0.0),
            )
        )

        result = run_basic_simulation(loaded.initial_conditions, parameters, timeline)
        lost_times = [row.time_s for row in result.rows if row.truck2_tracking_status == "Lost"]

        self.assertTrue(any(abs(time_s - 5.0) < 1e-6 for time_s in lost_times))
        self.assertTrue(all(row.truck2_tracking_status == "Tracking" for row in result.rows if row.time_s >= 10.0))

    def test_uploaded_long_loss_scenario_does_not_resume_by_distance_by_default(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        timeline = ScenarioTimeline.from_csv(TRUCK2_LONG_LOSS_TIMELINE)
        braking_table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)

        result = run_basic_simulation(loaded.initial_conditions, loaded.simulation_parameters, timeline, braking_table)

        self.assertTrue(any(row.truck2_tracking_status == "Lost" and row.time_s >= 21.0 for row in result.rows))

    def test_lost_tracking_target_stop_brakes_to_frozen_target(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(
            loaded.initial_conditions,
            truck1_velocity_kph=10.0,
            truck2_velocity_kph=10.0,
        )
        parameters = replace(loaded.simulation_parameters, output_resolution_s=1.0)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=1.0, truck1_velocity_kph=10.0, truck2_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=35.0, truck1_velocity_kph=10.0),
            )
        )

        result = run_basic_simulation(initial, parameters, timeline)
        lost_rows = [row for row in result.rows if row.truck2_tracking_status == "Lost"]
        stopped_rows = [row for row in lost_rows if row.truck2_velocity_kph <= 1e-6]

        self.assertTrue(lost_rows)
        self.assertEqual(lost_rows[0].truck2_command, "Lost tracking target stop")
        self.assertIsNotNone(lost_rows[0].truck2_loss_target_rear_m)
        self.assertTrue(stopped_rows)
        self.assertAlmostEqual(stopped_rows[0].truck2_position_m, stopped_rows[0].truck2_loss_target_rear_m or 0.0, places=1)

    def test_distance_loss_resumes_when_live_gap_reaches_resume_distance(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(
            loaded.initial_conditions,
            initial_gap_12_m=25.5,
            truck1_velocity_kph=0.0,
            truck2_velocity_kph=10.0,
        )
        parameters = replace(loaded.simulation_parameters, resume_by_distance=False, output_resolution_s=1.0)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=0.0),
                ScenarioTimelineRow(time_s=10.0, truck1_velocity_kph=0.0),
            )
        )

        result = run_basic_simulation(initial, parameters, timeline)

        self.assertTrue(any(row.truck2_loss_source == "Distance" for row in result.rows))
        self.assertTrue(any(row.truck2_tracking_status == "Lost" for row in result.rows))
        self.assertTrue(any(row.truck2_tracking_status == "Tracking" for row in result.rows if row.truck2_gap_m <= 15.0))

    def test_distance_loss_stays_stopped_at_target_when_gap_is_above_resume_distance(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(
            loaded.initial_conditions,
            initial_gap_12_m=25.5,
            truck1_velocity_kph=10.0,
            truck2_velocity_kph=10.0,
        )
        parameters = replace(loaded.simulation_parameters, resume_by_distance=False, output_resolution_s=1.0)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=35.0, truck1_velocity_kph=10.0),
            )
        )

        result = run_basic_simulation(initial, parameters, timeline)
        stopped_lost_rows = [
            row
            for row in result.rows
            if row.truck2_tracking_status == "Lost" and row.truck2_velocity_kph <= 1e-6 and row.truck2_gap_m > 15.0
        ]

        self.assertTrue(stopped_lost_rows)
        self.assertTrue(all(row.truck2_command == "Hold at lost target" for row in stopped_lost_rows[:3]))

    def test_safety_lock_engages_after_waiting_stopped_at_lost_target(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(
            loaded.initial_conditions,
            truck1_velocity_kph=10.0,
            truck2_velocity_kph=10.0,
        )
        parameters = replace(loaded.simulation_parameters, output_resolution_s=1.0)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=1.0, truck1_velocity_kph=10.0, truck2_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=70.0, truck1_velocity_kph=10.0),
            )
        )

        result = run_basic_simulation(initial, parameters, timeline)

        self.assertTrue(any(row.truck2_state == FollowerState.SAFETY_LOCK.value for row in result.rows))
        self.assertTrue(any(row.truck2_command == "Safety Lock parking brakes" for row in result.rows))
        self.assertTrue(any(row.stop_reason_truck2 == "Safety Lock" for row in result.rows))

    def test_distance_resume_can_be_enabled(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        parameters = replace(loaded.simulation_parameters, resume_by_distance=True, output_resolution_s=1.0)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=0.0),
                ScenarioTimelineRow(time_s=1.0, truck2_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=10.0, truck2_image_event=ImageEvent.RESUME),
                ScenarioTimelineRow(time_s=12.0, truck1_velocity_kph=0.0),
            )
        )

        result = run_basic_simulation(loaded.initial_conditions, parameters, timeline)

        self.assertTrue(any(row.truck2_tracking_status == "Lost" for row in result.rows))
        self.assertTrue(all(row.truck2_tracking_status == "Tracking" for row in result.rows if 4.0 <= row.time_s < 10.0))

    def test_max_velocity_caps_followers_but_not_leader(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        parameters = replace(
            loaded.simulation_parameters,
            max_velocity_kph=5.0,
            max_acceleration_mps2=100.0,
            max_red_deceleration_mps2=100.0,
            output_resolution_s=1.0,
        )
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=20.0),
                ScenarioTimelineRow(time_s=3.0, truck1_velocity_kph=20.0),
            )
        )

        result = run_basic_simulation(loaded.initial_conditions, parameters, timeline)

        self.assertTrue(any(row.truck1_velocity_kph > 5.0 for row in result.rows))
        self.assertTrue(all(row.truck2_velocity_kph <= 5.0 + 1e-6 for row in result.rows))
        self.assertTrue(all(row.truck3_velocity_kph <= 5.0 + 1e-6 for row in result.rows))

    def test_time_headway_sets_continuous_orange_trigger_gap(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(loaded.initial_conditions, truck1_velocity_kph=7.2, truck2_velocity_kph=7.2)
        parameters = replace(
            loaded.simulation_parameters,
            orange_braking_mode=1,
            time_headway_s=3.0,
            minimum_gap_m=4.0,
            output_resolution_s=0.1,
        )
        timeline = ScenarioTimeline.from_rows((ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=7.2), ScenarioTimelineRow(time_s=0.2, truck1_velocity_kph=7.2)))

        result = run_basic_simulation(initial, parameters, timeline)

        self.assertAlmostEqual(result.rows[0].truck2_orange_trigger_gap_m, 10.0, places=1)
        self.assertEqual(result.rows[0].orange_braking_mode, 1)

    def test_orange_braking_decelerates_to_75_percent_then_holds(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(loaded.initial_conditions, initial_gap_12_m=20.0, truck1_velocity_kph=10.0, truck2_velocity_kph=10.0)
        parameters = replace(
            loaded.simulation_parameters,
            red_distance_m=1.0,
            orange_distance_m=50.0,
            image_identification_loss_distance_m=100.0,
            maximum_gap_m=90.0,
            orange_deceleration_mps2=2.0,
            output_resolution_s=0.1,
        )
        timeline = ScenarioTimeline.from_rows((ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0), ScenarioTimelineRow(time_s=3.0, truck1_velocity_kph=10.0)))

        result = run_basic_simulation(initial, parameters, timeline)

        self.assertTrue(any(row.truck2_command == "Orange deceleration" for row in result.rows))
        hold_rows = [row for row in result.rows if row.truck2_command == "Orange hold target speed"]
        self.assertTrue(hold_rows)
        self.assertLessEqual(hold_rows[0].truck2_velocity_kph, 7.6)

    def test_fort_activated_applies_emergency_deceleration(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(loaded.initial_conditions, truck1_velocity_kph=10.0, truck2_velocity_kph=10.0)
        parameters = replace(loaded.simulation_parameters, emergency_deceleration_mps2=5.0, output_resolution_s=0.1)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=1.0, truck1_velocity_kph=10.0, truck2_image_event=ImageEvent.FORT_ACTIVATED),
                ScenarioTimelineRow(time_s=1.2, truck1_velocity_kph=10.0),
            )
        )

        result = run_basic_simulation(initial, parameters, timeline)

        self.assertTrue(any(row.truck2_state == FollowerState.FORT_EMERGENCY_DECEL.value for row in result.rows))
        self.assertTrue(any(row.truck2_command == "FORT emergency deceleration" and row.truck2_acceleration_mps2 == -5.0 for row in result.rows))

    def test_truck1_fort_latches_to_full_stop_and_does_not_resume(self) -> None:
        """FORT on Truck #1 triggers latching emergency deceleration to 0 velocity; no acceleration afterwards."""
        initial = InitialConditions(
            truck_length_m=9.0,
            initial_gap_12_m=10.0,
            initial_gap_23_m=10.0,
            truck1_velocity_kph=10.0,
            truck2_velocity_kph=10.0,
            truck3_velocity_kph=10.0,
        )
        parameters = SimulationParameters(
            max_velocity_kph=30.0,
            max_acceleration_mps2=2.0,
            max_red_deceleration_mps2=4.0,
            minimum_gap_m=3.0,
            maximum_gap_m=30.0,
            red_distance_m=6.0,
            orange_distance_m=9.0,
            start_moving_identification_delay_ms=200.0,
            distance_identification_delay_ms=100.0,
            image_identification_loss_distance_m=30.0,
            image_identification_resume_distance_m=15.0,
            under_loss_following_velocity_kph=5.0,
            under_loss_leading_velocity_kph=5.0,
            trucks_communicating=False,
            emergency_deceleration_mps2=5.0,
            simulation_time_step_s=0.1,
            output_resolution_s=0.1,
        )
        # Leader profile shows 10 kph before FORT, then specifies 20 kph after —
        # but FORT must prevent the leader from accelerating.
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=1.0, truck1_velocity_kph=10.0, truck1_event=ImageEvent.FORT_ACTIVATED),
                ScenarioTimelineRow(time_s=5.0, truck1_velocity_kph=20.0),  # must be ignored after FORT
            )
        )

        result = run_basic_simulation(initial, parameters, timeline)

        # Truck1 must decelerate to 0 after FORT
        rows_after_fort = [r for r in result.rows if r.time_s > 1.0]
        self.assertTrue(any(r.truck1_velocity_kph < 0.01 for r in rows_after_fort), "Truck1 must stop after FORT")

        # All post-FORT rows must show FORT state (no return to profile-following)
        for row in rows_after_fort:
            if row.truck1_velocity_kph < 0.01:
                self.assertEqual(row.truck1_state, "FORT_EMERGENCY_DECEL")
                self.assertEqual(row.truck1_command, "FORT emergency deceleration")

        # Truck1 must NOT resume acceleration even though the profile specifies 20 kph after FORT
        rows_at_end = [r for r in result.rows if r.time_s >= 4.0]
        self.assertTrue(all(r.truck1_velocity_kph < 0.01 for r in rows_at_end), "Truck1 must remain stopped")
        self.assertTrue(all(r.truck1_acceleration_mps2 >= -1e-9 for r in rows_at_end), "No negative accel when stopped")

    def test_initial_start_waits_for_start_gap_and_front_velocity(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        initial = replace(loaded.initial_conditions, initial_gap_12_m=7.5, truck1_velocity_kph=10.0, truck2_velocity_kph=0.0)
        parameters = replace(loaded.simulation_parameters, start_moving_gap_m=8.0, output_resolution_s=0.1)
        timeline = ScenarioTimeline.from_rows((ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=10.0), ScenarioTimelineRow(time_s=1.0, truck1_velocity_kph=10.0)))

        result = run_basic_simulation(initial, parameters, timeline)

        self.assertEqual(result.rows[1].truck2_command, "Wait for initial start conditions")
        self.assertTrue(any(row.truck2_command == "Accelerate initial start" for row in result.rows))

    def test_communication_on_requests_trucks_ahead_to_stop_after_truck3_loss(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        parameters = replace(
            loaded.simulation_parameters,
            trucks_communicating=True,
            output_resolution_s=1.0,
        )
        braking_table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=0.0),
                ScenarioTimelineRow(time_s=4.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=8.0, truck1_velocity_kph=10.0, truck3_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=12.0, truck1_velocity_kph=10.0),
            )
        )

        result = run_basic_simulation(loaded.initial_conditions, parameters, timeline, braking_table)

        self.assertTrue(any(row.communication_status == "Approved" for row in result.rows))
        self.assertTrue(any("Truck3 lost" in row.communication_message for row in result.rows))
        self.assertTrue(any(row.truck2_command == "Communication stop request" for row in result.rows))
        self.assertTrue(any(log.event == "Communication" for log in result.logs))

    def test_communication_off_does_not_send_loss_stop_request(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        parameters = replace(
            loaded.simulation_parameters,
            trucks_communicating=False,
            output_resolution_s=1.0,
        )
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=0.0),
                ScenarioTimelineRow(time_s=4.0, truck1_velocity_kph=10.0),
                ScenarioTimelineRow(time_s=8.0, truck1_velocity_kph=10.0, truck3_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=12.0, truck1_velocity_kph=10.0),
            )
        )

        result = run_basic_simulation(loaded.initial_conditions, parameters, timeline)

        self.assertTrue(all(row.communication_status == "Disabled" for row in result.rows))
        self.assertFalse(any(row.truck2_command == "Communication stop request" for row in result.rows))

    def test_communication_failure_progresses_to_fallback(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        parameters = replace(
            loaded.simulation_parameters,
            trucks_communicating=True,
            communication_reliability_percent=0.0,
            output_resolution_s=0.1,
        )
        timeline = ScenarioTimeline.from_rows(
            (
                ScenarioTimelineRow(time_s=0.0, truck1_velocity_kph=0.0),
                ScenarioTimelineRow(time_s=1.0, truck2_image_event=ImageEvent.LOSS),
                ScenarioTimelineRow(time_s=2.0, truck1_velocity_kph=0.0),
            )
        )

        result = run_basic_simulation(loaded.initial_conditions, parameters, timeline)
        statuses = {row.communication_status for row in result.rows}

        self.assertIn("Sent", statuses)
        self.assertIn("Retried", statuses)
        self.assertIn("Failed fallback", statuses)


if __name__ == "__main__":
    unittest.main()
