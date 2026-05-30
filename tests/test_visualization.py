import tempfile
import unittest
from pathlib import Path

from convoysim.simulation import SimulationResult, SimulationRow
from convoysim.visualization import (
    ORANGE_STATUS_COLOR,
    RED_STATUS_COLOR,
    TRUCK_BODY_HEIGHT_PX,
    chart_stroke_width,
    compact_command,
    compact_status,
    distance_tick_values,
    follower_style,
    format_time_tick,
    format_y_tick,
    follower_chart_segment_style,
    gap_arrow_coordinates,
    gap_arrow_y_for_status_rect_top,
    label_y_positions,
    load_simulation_rows_csv,
    lost_target_marker_x,
    lost_target_marker_color,
    lost_target_markers,
    marker_x_for_time,
    nearest_row_index,
    origin_label_positions,
    orange_trigger_gap_arrow_coordinates,
    position_scale_for_rows,
    target_triangle_points,
    time_tick_values,
    status_indicator_style,
    truck_body_style,
    truck_color_for_label,
    truck_text_color,
    truck_wheel_centers,
    TRUCK_WHEEL_RADIUS_PX,
    y_tick_values,
)


class VisualizationTest(unittest.TestCase):
    def test_position_scale_maps_min_and_max_positions(self) -> None:
        rows = (_row(time_s=0.0, truck1_position_m=40.0, truck2_position_m=20.0, truck3_position_m=0.0),)

        scale = position_scale_for_rows(rows, truck_length_m=8.0, canvas_width=1000, margin_px=50)

        self.assertLess(scale.x_for(0.0), scale.x_for(20.0))
        self.assertLess(scale.x_for(20.0), scale.x_for(40.0))
        self.assertAlmostEqual(scale.left_px, 50.0)
        self.assertAlmostEqual(scale.right_px, 950.0)

    def test_nearest_row_index_finds_closest_time(self) -> None:
        rows = (
            _row(time_s=0.0),
            _row(time_s=1.0),
            _row(time_s=2.0),
        )

        self.assertEqual(nearest_row_index(rows, 1.4), 1)
        self.assertEqual(nearest_row_index(rows, 1.6), 2)

    def test_marker_x_for_time_maps_progress_to_chart_width(self) -> None:
        rows = (
            _row(time_s=0.0),
            _row(time_s=5.0),
            _row(time_s=10.0),
        )

        self.assertAlmostEqual(marker_x_for_time(rows, 0.0, 10.0, 110.0), 10.0)
        self.assertAlmostEqual(marker_x_for_time(rows, 5.0, 10.0, 110.0), 60.0)
        self.assertAlmostEqual(marker_x_for_time(rows, 20.0, 10.0, 110.0), 110.0)

    def test_y_tick_values_use_clean_integer_steps(self) -> None:
        ticks = y_tick_values(20.0)

        self.assertEqual(ticks, (0.0, 5.0, 10.0, 15.0, 20.0))
        self.assertEqual(y_tick_values(44.7), (0.0, 10.0, 20.0, 30.0, 40.0))
        self.assertEqual(format_y_tick(10.0), "10")

    def test_distance_tick_values_use_10_meter_steps(self) -> None:
        self.assertEqual(distance_tick_values(-4.0, 24.0), (0.0, 10.0, 20.0))

    def test_time_tick_values_use_clean_time_labels(self) -> None:
        self.assertEqual(time_tick_values(0.0, 10.0), (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0))
        self.assertEqual(time_tick_values(2.5, 2.5), (2.5,))
        self.assertEqual(format_time_tick(10.0), "10")
        self.assertEqual(format_time_tick(2.5), "")
        self.assertEqual(format_time_tick(5.0), "")

    def test_chart_stroke_width_matches_html_chart_rules(self) -> None:
        self.assertEqual(chart_stroke_width("FOLLOWING_MATCHING_SPEED", "Match speed"), 2)
        self.assertEqual(chart_stroke_width("FOLLOWING_ORANGE_DECEL", "Orange deceleration"), 4)
        self.assertEqual(chart_stroke_width("FOLLOWING_RED_BRAKING_TO_STOP", "Red brake to stop"), 6)

    def test_chart_segment_style_matches_truck_status_rules(self) -> None:
        normal = follower_chart_segment_style("Truck2", _row(), _row())
        lost = follower_chart_segment_style("Truck2", _row(truck2_tracking_status="Lost"), _row(truck2_tracking_status="Lost"))
        orange = follower_chart_segment_style(
            "Truck2",
            _row(truck2_state="FOLLOWING_ORANGE_DECEL", truck2_command="Orange deceleration"),
            _row(truck2_state="FOLLOWING_ORANGE_DECEL", truck2_command="Orange deceleration"),
        )
        red = follower_chart_segment_style(
            "Truck3",
            _row(truck3_state="FOLLOWING_RED_BRAKING_TO_STOP", truck3_command="Red brake to stop"),
            _row(truck3_state="FOLLOWING_RED_BRAKING_TO_STOP", truck3_command="Red brake to stop"),
        )

        self.assertEqual(normal.color, "#1f77b4")
        self.assertIsNone(normal.dash)
        self.assertEqual(lost.dash, (5, 4))
        self.assertEqual(orange.color, ORANGE_STATUS_COLOR)
        self.assertEqual(red.color, RED_STATUS_COLOR)

    def test_gap_arrow_coordinates_use_follower_front_and_leading_rear(self) -> None:
        rows = (_row(truck1_position_m=40.0, truck2_position_m=20.0),)
        scale = position_scale_for_rows(rows, truck_length_m=8.0, canvas_width=1000, margin_px=50)

        arrow = gap_arrow_coordinates(scale, follower_front_m=20.0, leading_front_m=40.0, truck_length_m=8.0, y=200.0)

        self.assertAlmostEqual(arrow.start_x, scale.x_for(20.0))
        self.assertAlmostEqual(arrow.end_x, scale.x_for(32.0))
        self.assertAlmostEqual(arrow.y, 200.0)
        self.assertAlmostEqual(arrow.label_x, (scale.x_for(20.0) + scale.x_for(32.0)) / 2.0)
        self.assertLess(arrow.label_y, arrow.y)

    def test_orange_trigger_gap_arrow_uses_required_gap_from_follower_front(self) -> None:
        rows = (_row(truck2_position_m=20.0),)
        scale = position_scale_for_rows(rows, truck_length_m=8.0, canvas_width=1000, margin_px=50)

        arrow = orange_trigger_gap_arrow_coordinates(scale, follower_front_m=20.0, orange_trigger_gap_m=10.0, y=160.0)

        self.assertAlmostEqual(arrow.start_x, scale.x_for(20.0))
        self.assertAlmostEqual(arrow.end_x, scale.x_for(30.0))
        self.assertLess(arrow.label_y, arrow.y)

    def test_gap_arrow_y_uses_upper_status_rectangle_top(self) -> None:
        self.assertEqual(TRUCK_BODY_HEIGHT_PX, 28.5)
        self.assertAlmostEqual(gap_arrow_y_for_status_rect_top(200.0), 168.75)

    def test_target_triangle_sits_on_road_line_without_label_geometry(self) -> None:
        points = target_triangle_points(x=100.0, road_line_y=240.0)

        self.assertEqual(points, (100.0, 224.0, 92.0, 240.0, 108.0, 240.0))

    def test_lost_target_marker_x_uses_frozen_leading_rear(self) -> None:
        rows = (_row(truck1_position_m=40.0, truck2_position_m=20.0),)
        scale = position_scale_for_rows(rows, truck_length_m=8.0, canvas_width=1000, margin_px=50)
        marker = lost_target_markers(
            (
                _row(time_s=0.0, truck1_position_m=40.0, truck2_position_m=20.0),
                _row(time_s=1.0, truck1_position_m=42.0, truck2_position_m=21.0, truck2_tracking_status="Lost"),
            ),
            1,
            truck_length_m=8.0,
        )[0]

        self.assertAlmostEqual(lost_target_marker_x(scale, marker, truck_length_m=8.0), scale.x_for(34.0))

    def test_lost_target_marker_uses_explicit_output_target(self) -> None:
        rows = (
            _row(time_s=0.0, truck1_position_m=40.0, truck2_position_m=20.0),
            _row(
                time_s=1.0,
                truck1_position_m=42.0,
                truck2_position_m=21.0,
                truck2_tracking_status="Lost",
                truck2_loss_target_rear_m=31.5,
            ),
        )
        scale = position_scale_for_rows(rows, truck_length_m=8.0, canvas_width=1000, margin_px=50)
        marker = lost_target_markers(rows, 1, truck_length_m=8.0)[0]

        self.assertAlmostEqual(lost_target_marker_x(scale, marker, truck_length_m=8.0), scale.x_for(31.5))

    def test_lost_target_marker_color_matches_affected_truck(self) -> None:
        marker2 = lost_target_markers(
            (
                _row(time_s=0.0, truck1_position_m=40.0, truck2_position_m=20.0),
                _row(time_s=1.0, truck1_position_m=42.0, truck2_position_m=21.0, truck2_tracking_status="Lost"),
            ),
            1,
            truck_length_m=8.0,
        )[0]
        marker3 = lost_target_markers(
            (
                _row(time_s=0.0, truck2_position_m=25.0, truck3_position_m=5.0),
                _row(time_s=1.0, truck2_position_m=27.0, truck3_position_m=6.0, truck3_tracking_status="Lost"),
            ),
            1,
            truck_length_m=8.0,
        )[0]

        self.assertEqual(lost_target_marker_color(marker2), "#1f77b4")
        self.assertEqual(lost_target_marker_color(marker3), "#ff7f0e")

    def test_follower_style_reflects_tracking_and_braking_status(self) -> None:
        normal = follower_style("FOLLOWING_MATCHING_SPEED", "Match speed", "Tracking", "")
        lost = follower_style("TRACKING_LOST_TO_LAST_POSITION", "Lost tracking safe velocity", "Lost", "")
        orange = follower_style("FOLLOWING_ORANGE_DECEL", "Orange deceleration", "Tracking", "")
        red = follower_style("FOLLOWING_RED_BRAKING_TO_STOP", "Red brake to stop", "Tracking", "")

        self.assertEqual(normal.width, 2)
        self.assertIsNone(normal.dash)
        self.assertEqual(lost.dash, (5, 3))
        self.assertEqual(orange.width, 3)
        self.assertEqual(red.width, 4)

    def test_label_y_positions_use_separate_lanes(self) -> None:
        lane0 = label_y_positions(170.0, 0)
        lane1 = label_y_positions(170.0, 1)
        lane2 = label_y_positions(170.0, 2)

        self.assertLess(lane0[0], lane1[0])
        self.assertLess(lane1[0], lane2[0])
        self.assertLess(lane0[1], lane1[1])
        self.assertLess(lane1[1], lane2[1])

    def test_origin_label_positions_describe_top_and_bottom_bubbles(self) -> None:
        top_label, bottom_label = origin_label_positions(200.0)

        self.assertEqual(top_label[0], "tracking/status state")
        self.assertEqual(bottom_label[0], "command/action or violation")
        self.assertLess(top_label[2], 200.0)
        self.assertGreater(bottom_label[2], 200.0)

    def test_compact_visualization_text_removes_long_headers(self) -> None:
        self.assertEqual(compact_status("", ""), "")
        self.assertEqual(compact_status("FOLLOWING_MATCHING_SPEED", "Tracking"), "Tracking: Match speed")
        self.assertEqual(compact_status("TRACKING_LOST_TO_LAST_POSITION", "Lost"), "Image identification loss")
        self.assertEqual(compact_command("Match front-truck speed", ""), "Match speed")
        self.assertEqual(compact_command("Hold stopped", ""), "Hold stopped")
        self.assertEqual(compact_command("Follow leader profile speed", ""), "Leader cruising")
        self.assertEqual(compact_command("Orange deceleration", ""), "Orange braking")
        self.assertEqual(compact_command("Lost tracking target stop", ""), "Lost: target stop")
        self.assertEqual(compact_command("Match front-truck speed", "Minimum gap violation"), "Minimum gap violation")

    def test_truck_body_and_status_styles_use_identity_and_status_colors(self) -> None:
        self.assertEqual(truck_body_style(2).fill, "#111111")
        self.assertEqual(truck_body_style(1).fill, "#1f77b4")
        self.assertEqual(truck_body_style(0).fill, "#ff7f0e")
        self.assertEqual(truck_text_color(2), "#ffffff")

        normal = status_indicator_style(1, "FOLLOWING_MATCHING_SPEED", "Match speed", "Tracking", "")
        lost = status_indicator_style(1, "TRACKING_LOST_TO_LAST_POSITION", "Lost tracking safe velocity", "Lost", "")
        orange = status_indicator_style(1, "FOLLOWING_ORANGE_DECEL", "Orange deceleration", "Tracking", "")
        red = status_indicator_style(1, "FOLLOWING_RED_BRAKING_TO_STOP", "Red brake to stop", "Tracking", "")

        self.assertEqual(normal.fill, "#1f77b4")
        self.assertEqual(lost.dash, (5, 3))
        self.assertEqual(orange.fill, ORANGE_STATUS_COLOR)
        self.assertEqual(red.fill, RED_STATUS_COLOR)

    def test_truck_wheel_helpers_use_consistent_truck_colors(self) -> None:
        wheels = truck_wheel_centers(10.0, 50.0, 20.0)

        self.assertEqual(wheels, ((20.0, 29.0), (40.0, 29.0)))
        self.assertEqual(TRUCK_WHEEL_RADIUS_PX, 8.0)
        self.assertEqual(truck_color_for_label(2), "#111111")
        self.assertEqual(truck_color_for_label(1), "#1f77b4")
        self.assertEqual(truck_color_for_label(0), "#ff7f0e")

    def test_lost_target_marker_appears_on_loss_and_clears_on_resume(self) -> None:
        rows = (
            _row(time_s=0.0, truck1_position_m=30.0, truck2_position_m=15.0),
            _row(time_s=1.0, truck1_position_m=32.0, truck2_position_m=17.0, truck2_tracking_status="Lost"),
            _row(time_s=2.0, truck1_position_m=34.0, truck2_position_m=19.0, truck2_tracking_status="Lost"),
            _row(time_s=3.0, truck1_position_m=36.0, truck2_position_m=21.0, truck2_tracking_status="Tracking"),
        )

        markers_during_loss = lost_target_markers(rows, 2, truck_length_m=8.0)
        markers_after_resume = lost_target_markers(rows, 3, truck_length_m=8.0)

        self.assertEqual(len(markers_during_loss), 1)
        self.assertEqual(markers_during_loss[0].follower, "Truck2")
        self.assertAlmostEqual(markers_during_loss[0].target_front_m, 32.0)
        self.assertEqual(markers_during_loss[0].loss_source, "Scenario")
        self.assertEqual(markers_after_resume, ())

    def test_lost_target_marker_preserves_distance_loss_source(self) -> None:
        rows = (
            _row(time_s=0.0, truck1_position_m=30.0, truck2_position_m=15.0),
            _row(
                time_s=1.0,
                truck1_position_m=32.0,
                truck2_position_m=17.0,
                truck2_tracking_status="Lost",
                truck2_loss_source="Distance",
            ),
        )

        markers = lost_target_markers(rows, 1, truck_length_m=8.0)

        self.assertEqual(markers[0].loss_source, "Distance")

    def test_lost_target_marker_clears_when_target_region_is_reached(self) -> None:
        rows = (
            _row(time_s=0.0, truck1_position_m=30.0, truck2_position_m=15.0),
            _row(time_s=1.0, truck1_position_m=32.0, truck2_position_m=17.0, truck2_tracking_status="Lost"),
            _row(time_s=2.0, truck1_position_m=34.0, truck2_position_m=24.5, truck2_tracking_status="Lost"),
        )

        self.assertEqual(lost_target_markers(rows, 2, truck_length_m=8.0), ())

    def test_loads_simulation_rows_from_output_csv(self) -> None:
        row = _row(time_s=3.0, truck1_position_m=45.0, truck2_position_m=25.0, truck3_position_m=5.0)
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "output.csv"
            SimulationResult(rows=(row,)).write_csv(output_path)

            loaded_rows = load_simulation_rows_csv(output_path)

        self.assertEqual(len(loaded_rows), 1)
        self.assertEqual(loaded_rows[0].time_s, 3.0)
        self.assertEqual(loaded_rows[0].truck1_position_m, 45.0)


def _row(
    time_s: float = 0.0,
    truck1_position_m: float = 30.0,
    truck2_position_m: float = 15.0,
    truck3_position_m: float = 0.0,
    truck2_tracking_status: str = "Tracking",
    truck3_tracking_status: str = "Tracking",
    truck2_state: str = "FOLLOWING_MATCHING_SPEED",
    truck3_state: str = "FOLLOWING_MATCHING_SPEED",
    truck2_command: str = "Match speed",
    truck3_command: str = "Match speed",
    truck2_loss_source: str = "",
    truck3_loss_source: str = "",
    truck2_loss_target_rear_m: float | None = None,
    truck3_loss_target_rear_m: float | None = None,
) -> SimulationRow:
    return SimulationRow(
        time_s=time_s,
        truck1_position_m=truck1_position_m,
        truck2_position_m=truck2_position_m,
        truck3_position_m=truck3_position_m,
        truck2_gap_m=7.0,
        truck3_gap_m=7.0,
        gap2_violation=False,
        gap3_violation=False,
        truck1_velocity_kph=10.0,
        truck2_velocity_kph=10.0,
        truck3_velocity_kph=10.0,
        truck1_acceleration_mps2=0.0,
        truck2_acceleration_mps2=0.0,
        truck3_acceleration_mps2=0.0,
        truck2_state=truck2_state,
        truck3_state=truck3_state,
        truck2_command=truck2_command,
        truck3_command=truck3_command,
        truck2_actual_gap_m=7.0,
        truck2_measured_gap_m=7.0,
        truck3_actual_gap_m=7.0,
        truck3_measured_gap_m=7.0,
        truck2_tracking_status=truck2_tracking_status,
        truck3_tracking_status=truck3_tracking_status,
        truck2_relative_velocity_kph=0.0,
        truck3_relative_velocity_kph=0.0,
        communication_message="",
        communication_status="Disabled",
        violation_type_truck2="",
        violation_type_truck3="",
        stop_reason_truck2="",
        stop_reason_truck3="",
        truck2_loss_source=truck2_loss_source,
        truck3_loss_source=truck3_loss_source,
        truck2_loss_target_rear_m=truck2_loss_target_rear_m,
        truck3_loss_target_rear_m=truck3_loss_target_rear_m,
    )


if __name__ == "__main__":
    unittest.main()
