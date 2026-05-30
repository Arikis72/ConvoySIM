import unittest

from convoysim.gui import _bulk_chart_point_is_selected, _bulk_number_label, _wrapped_bulk_heading, playback_delay_ms
from convoysim.gui_helpers import (
    SCENARIO_IMAGE_EVENT_OPTIONS,
    display_cell_value,
    display_log_rows,
    display_output_columns,
    help_row_matches_filter,
    is_scenario_image_event_column,
    log_state_icon,
    log_truck_order,
    output_column_group,
    output_header_label,
    parameter_category,
    parameter_row_matches_filter,
    preferred_column_width,
    table_column_anchor,
    state_machine_help_from_markdown,
    wrap_header,
)
from convoysim.simulation import SimulationLogRow


class GuiHelpersTest(unittest.TestCase):
    def test_playback_delay_decreases_as_speed_increases(self) -> None:
        self.assertEqual(playback_delay_ms(1.0), 100)
        self.assertGreater(playback_delay_ms(0.3), playback_delay_ms(0.6))
        self.assertGreater(playback_delay_ms(0.6), playback_delay_ms(1.0))
        self.assertLess(playback_delay_ms(2.0), playback_delay_ms(1.0))

    def test_bulk_chart_labels_use_plain_numbers_and_wrapped_headers(self) -> None:
        self.assertEqual(_bulk_number_label(6010.0), "6010")
        self.assertEqual(_bulk_number_label(12.5), "12.5")
        self.assertEqual(_wrapped_bulk_heading("Total_Weighted_Cost"), "Total Weighted\nCost")
        selected = (8.0, "Accidents", "cost")
        self.assertTrue(_bulk_chart_point_is_selected(selected, 8.0, "Accidents", "cost"))
        self.assertFalse(_bulk_chart_point_is_selected(selected, 8.0, "Red braking count", "cost"))

    def test_state_machine_help_merges_state_meaning_and_command_tables(self) -> None:
        markdown = """### 17.1 Required states

| State | Meaning |
|---|---|
| STOPPED_WAITING | Waiting |
| SAFETY_LOCK | Locked |

### 17.2 State transitions

| From state | Condition | To state |
|---|---|---|
| STOPPED_WAITING | Truck ahead velocity > 0 | START_DELAY_COUNTING |

### 17.3 State-to-command mapping

| State | Command |
|---|---|
| STOPPED_WAITING | Hold velocity at 0 |
| SAFETY_LOCK | Apply parking brakes |

### 17.4 Visualization help labels

| Label group | Label | Meaning |
|---|---|---|
| Command/action or violation | Hold stopped | Follower remains stopped |
| Tracking/status state | Image identification loss | Tracking is lost |
| Command/action or violation | Orange braking | Orange deceleration |
"""

        help_data = state_machine_help_from_markdown(markdown)

        self.assertEqual(help_data.state_command_headers, ("State", "Meaning", "Command"))
        self.assertEqual(help_data.state_command_rows[0], ("STOPPED_WAITING", "Waiting", "Hold velocity at 0"))
        self.assertEqual(help_data.state_command_rows[1], ("SAFETY_LOCK", "Locked", "Apply parking brakes"))
        self.assertEqual(help_data.transition_rows[0][1], "Truck ahead velocity > 0")
        self.assertEqual(help_data.visualization_label_headers, ("Label group", "Label", "Meaning"))
        labels = [row[1] for row in help_data.visualization_label_rows]
        self.assertIn("Hold stopped", labels)
        self.assertIn("Image identification loss", labels)

    def test_log_rows_sort_by_time_and_truck_order(self) -> None:
        rows = display_log_rows(
            (
                SimulationLogRow(2.0, "INFO", "General", "No truck"),
                SimulationLogRow(1.0, "INFO", "Event", "Truck #3 orange braking"),
                SimulationLogRow(1.0, "INFO", "Event", "Truck #2 image loss"),
            )
        )

        self.assertEqual([row.truck_order for row in rows], [2, 3, 4])
        self.assertEqual(rows[0].tag, "truck2")
        self.assertEqual(rows[0].icon, "..")
        self.assertEqual(rows[1].icon, "--")

    def test_log_truck_order_and_icon_classification(self) -> None:
        self.assertEqual(log_truck_order("Event", "Truck2 message"), 2)
        self.assertEqual(log_truck_order("Event", "General message"), 4)
        self.assertEqual(log_state_icon("Event", "Truck #3 red braking"), "==")
        self.assertEqual(log_state_icon("Event", "Truck #2 image lost"), "..")

    def test_output_columns_are_grouped_by_truck(self) -> None:
        ordered = display_output_columns(
            (
                "Truck3_Command",
                "Truck1_Position_m",
                "Time_s",
                "Truck2_State",
                "Other",
            )
        )

        self.assertEqual(ordered[:4], ("Time_s", "Truck1_Position_m", "Truck2_State", "Truck3_Command"))
        self.assertEqual(ordered[-1], "Other")

    def test_table_display_formatting_helpers(self) -> None:
        self.assertEqual(display_cell_value("1.234"), "1.2")
        self.assertEqual(display_cell_value("Yes"), "Yes")
        self.assertEqual(table_column_anchor("Value", "parameters"), "center")
        self.assertEqual(table_column_anchor("Notes", "scenario"), "w")
        self.assertEqual(output_column_group("Truck2_State"), "truck2")
        self.assertEqual(output_header_label("Communication_Message"), "Comm Msg")
        self.assertEqual(output_header_label("Truck2_Loss_Target_Rear_m"), "T2 Target")
        self.assertLess(
            preferred_column_width("Communication_Message", ("", ""), min_width=48, include_header=False),
            60,
        )
        self.assertIn("\n", wrap_header("Truck2_Relative_Velocity_kph", max_part_length=12))

    def test_scenario_image_event_columns_use_controlled_options(self) -> None:
        self.assertTrue(is_scenario_image_event_column("Truck2_Image_Event"))
        self.assertTrue(is_scenario_image_event_column("Truck3_Image_Event"))
        self.assertFalse(is_scenario_image_event_column("Truck1_Velocity_kph"))
        self.assertEqual(SCENARIO_IMAGE_EVENT_OPTIONS, ("", "Loss", "Resume", "FORT activated"))

    def test_parameter_category_and_filter_helpers(self) -> None:
        self.assertEqual(parameter_category("Truck length"), "Geometry and initial conditions")
        self.assertEqual(parameter_category("Communication latency"), "Communication")
        self.assertEqual(parameter_category("Orange braking mode"), "Dynamic limits and gap thresholds")
        self.assertEqual(parameter_category("Simulation time step"), "Simulation timing")
        row = ("Truck image identification loss distance", "20", "m", "Tracking is lost if gap exceeds this value")
        self.assertTrue(parameter_row_matches_filter(row, "loss"))
        self.assertTrue(parameter_row_matches_filter(row, "tracking"))
        self.assertFalse(parameter_row_matches_filter(row, "latency"))

    def test_help_row_matches_filter_searches_all_columns(self) -> None:
        row = ("Command/action or violation", "Hold stopped", "Follower remains stopped")

        self.assertTrue(help_row_matches_filter(row, "hold"))
        self.assertTrue(help_row_matches_filter(row, "follower"))
        self.assertFalse(help_row_matches_filter(row, "orange"))


if __name__ == "__main__":
    unittest.main()
