"""Stage C straight-line convoy visualization helpers and Tk renderer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import math
import tkinter as tk
from typing import Callable

from convoysim.simulation import SimulationRow

CHART_LEFT_PX = 70.0
CHART_RIGHT_MARGIN_PX = 30.0
TRUCK_WHEEL_RADIUS_PX = 8.0
TRUCK_BODY_HEIGHT_PX = 28.5
STATUS_RECT_HEIGHT_PX = 17.0
TRUCK_IDENTITY_COLORS = {
    2: "#111111",
    1: "#1f77b4",
    0: "#2ca02c",
}
ORANGE_STATUS_COLOR = "#d77a00"
RED_STATUS_COLOR = "#b00020"


@dataclass(frozen=True)
class PositionScale:
    min_position_m: float
    max_position_m: float
    left_px: float
    right_px: float

    def x_for(self, position_m: float) -> float:
        span_m = self.max_position_m - self.min_position_m
        if span_m <= 0:
            return (self.left_px + self.right_px) / 2.0
        return self.left_px + ((position_m - self.min_position_m) / span_m) * (self.right_px - self.left_px)


@dataclass(frozen=True)
class TruckVisualStyle:
    fill: str
    outline: str
    width: int
    dash: tuple[int, int] | None = None


@dataclass(frozen=True)
class GapArrow:
    start_x: float
    end_x: float
    y: float
    label_x: float
    label_y: float


@dataclass(frozen=True)
class LostTargetMarker:
    follower: str
    target_front_m: float
    loss_source: str = ""


@dataclass(frozen=True)
class ChartSeries:
    label: str
    color: str
    value_for_row: Callable[[SimulationRow], float]
    is_dotted_for_row: Callable[[SimulationRow], bool] = lambda _row: False
    width_for_row: Callable[[SimulationRow], int] = lambda _row: 2
    segment_style_for_rows: Callable[[SimulationRow, SimulationRow], "ChartSegmentStyle"] | None = None


@dataclass(frozen=True)
class ChartSegmentStyle:
    color: str
    width: int = 2
    dash: tuple[int, int] | None = None


def position_scale_for_rows(
    rows: tuple[SimulationRow, ...],
    truck_length_m: float,
    canvas_width: int,
    margin_px: int = 60,
    right_margin_px: int | None = None,
) -> PositionScale:
    right_margin = margin_px if right_margin_px is None else right_margin_px
    if not rows:
        return PositionScale(0.0, 1.0, margin_px, canvas_width - right_margin)

    min_rear_m = min(
        min(row.truck1_position_m, row.truck2_position_m, row.truck3_position_m) - truck_length_m for row in rows
    )
    max_front_m = max(max(row.truck1_position_m, row.truck2_position_m, row.truck3_position_m) for row in rows)
    padding_m = max(5.0, (max_front_m - min_rear_m) * 0.05)
    return PositionScale(
        min_position_m=min_rear_m - padding_m,
        max_position_m=max_front_m + padding_m,
        left_px=margin_px,
        right_px=canvas_width - right_margin,
    )


def nearest_row_index(rows: tuple[SimulationRow, ...], time_s: float) -> int:
    if not rows:
        return 0
    best_index = 0
    best_delta = abs(rows[0].time_s - time_s)
    for index, row in enumerate(rows[1:], start=1):
        delta = abs(row.time_s - time_s)
        if delta < best_delta:
            best_index = index
            best_delta = delta
    return best_index


def marker_x_for_time(rows: tuple[SimulationRow, ...], time_s: float, left_px: float, right_px: float) -> float:
    if not rows:
        return left_px
    start_time = rows[0].time_s
    end_time = rows[-1].time_s
    if end_time <= start_time:
        return (left_px + right_px) / 2.0
    clamped_time = max(start_time, min(end_time, time_s))
    return left_px + ((clamped_time - start_time) / (end_time - start_time)) * (right_px - left_px)


def y_tick_values(y_max: float, tick_count: int = 5) -> tuple[float, ...]:
    bounded_y_max = max(y_max, 1.0)
    bounded_tick_count = max(tick_count, 2)
    step = _nice_integer_tick_step(bounded_y_max / bounded_tick_count)
    values: list[float] = []
    value = 0.0
    while value <= bounded_y_max + 1e-9:
        values.append(value)
        value += step
    if len(values) < 2:
        values.append(step)
    return tuple(values)


def distance_tick_values(min_position_m: float, max_position_m: float, step_m: int = 10) -> tuple[float, ...]:
    if max_position_m < min_position_m:
        return ()
    step = max(1, step_m)
    start = math.ceil(min_position_m / step) * step
    values: list[float] = []
    value = float(start)
    while value <= max_position_m + 1e-9:
        values.append(value)
        value += step
    return tuple(values)


def format_y_tick(value: float) -> str:
    return f"{value:.0f}"


def time_tick_values(start_time_s: float, end_time_s: float, tick_count: int = 5) -> tuple[float, ...]:
    if end_time_s <= start_time_s:
        return (start_time_s,)
    step = 1.0
    values: list[float] = []
    value = math.ceil(start_time_s)
    if value > start_time_s + 1e-9:
        values.append(start_time_s)
    while value <= end_time_s + 1e-9:
        values.append(float(value))
        value += step
    if abs(values[-1] - end_time_s) > 1e-9:
        values.append(end_time_s)
    return tuple(values)


def format_time_tick(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) > 1e-9 or rounded % 10 != 0:
        return ""
    return f"{value:.0f}" if abs(value - round(value)) < 1e-9 else f"{value:.1f}"


def _nice_integer_tick_step(raw_step: float) -> int:
    if raw_step <= 1.0:
        return 1
    magnitude = 10 ** math.floor(math.log10(raw_step))
    normalized = raw_step / magnitude
    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10
    return int(nice * magnitude)


def chart_stroke_width(state: str, command: str) -> int:
    combined = f"{state} {command}".lower()
    if "red" in combined or "fort" in combined or "emergency" in combined:
        return 6
    if "orange" in combined or "communication_request_stop" in combined or "communication stop" in combined:
        return 4
    return 2


def is_red_status(state: str, command: str, violation_type: str) -> bool:
    combined = f"{state} {command} {violation_type}".lower()
    return "red" in combined or "fort" in combined or "emergency" in combined or "collision" in combined or "minimum gap violation" in combined


def is_orange_status(state: str, command: str) -> bool:
    combined = f"{state} {command}".lower()
    return "orange" in combined or "communication_request_stop" in combined or "communication stop" in combined


def truck_body_style(label_lane: int) -> TruckVisualStyle:
    color = truck_color_for_label(label_lane)
    return TruckVisualStyle(fill=color, outline=color, width=2)


def truck_text_color(label_lane: int) -> str:
    return "#ffffff" if label_lane == 2 else "#111111"


def status_indicator_style(label_lane: int, state: str, command: str, tracking_status: str, violation_type: str) -> TruckVisualStyle:
    fill = truck_color_for_label(label_lane)
    outline = fill
    width = 2
    dash = (5, 3) if tracking_status == "Lost" else None
    if is_red_status(state, command, violation_type):
        fill = RED_STATUS_COLOR
        outline = RED_STATUS_COLOR
        width = 3
    elif is_orange_status(state, command):
        fill = ORANGE_STATUS_COLOR
        outline = ORANGE_STATUS_COLOR
        width = 3
    return TruckVisualStyle(fill=fill, outline=outline, width=width, dash=dash)


def follower_chart_segment_style(follower: str, start: SimulationRow, end: SimulationRow, default_dashed_for_truck2: bool = False) -> ChartSegmentStyle:
    if follower == "Truck2":
        normal_color = truck_color_for_label(1)
        start_state, end_state = start.truck2_state, end.truck2_state
        start_command, end_command = start.truck2_command, end.truck2_command
        start_tracking, end_tracking = start.truck2_tracking_status, end.truck2_tracking_status
        start_violation, end_violation = start.violation_type_truck2, end.violation_type_truck2
    elif follower == "Truck3":
        normal_color = truck_color_for_label(0)
        start_state, end_state = start.truck3_state, end.truck3_state
        start_command, end_command = start.truck3_command, end.truck3_command
        start_tracking, end_tracking = start.truck3_tracking_status, end.truck3_tracking_status
        start_violation, end_violation = start.violation_type_truck3, end.violation_type_truck3
    else:
        normal_color = truck_color_for_label(2)
        start_state, end_state = start.truck1_state, end.truck1_state
        start_command, end_command = start.truck1_command, end.truck1_command
        start_tracking = end_tracking = ""
        start_violation = end_violation = ""

    color = normal_color
    width = 2
    if is_red_status(f"{start_state} {end_state}", f"{start_command} {end_command}", f"{start_violation} {end_violation}"):
        color = RED_STATUS_COLOR
        width = 3
    elif is_orange_status(f"{start_state} {end_state}", f"{start_command} {end_command}"):
        color = ORANGE_STATUS_COLOR
        width = 3

    # Determine dash pattern
    is_loss = start_tracking == "Lost" or end_tracking == "Lost"
    if is_loss:
        dash = (2, 3)  # dotted pattern for loss
    elif default_dashed_for_truck2 and follower == "Truck2":
        dash = (6, 3)  # dashed pattern for Truck2 velocity by default
    else:
        dash = None

    return ChartSegmentStyle(color=color, width=width, dash=dash)


def gap_arrow_coordinates(
    scale: PositionScale,
    follower_front_m: float,
    leading_front_m: float,
    truck_length_m: float,
    y: float,
) -> GapArrow:
    start_x = scale.x_for(follower_front_m)
    end_x = scale.x_for(leading_front_m - truck_length_m)
    return GapArrow(
        start_x=start_x,
        end_x=end_x,
        y=y,
        label_x=(start_x + end_x) / 2.0,
        label_y=y - 12.0,
    )


def orange_trigger_gap_arrow_coordinates(
    scale: PositionScale,
    follower_front_m: float,
    orange_trigger_gap_m: float,
    y: float,
) -> GapArrow:
    start_x = scale.x_for(follower_front_m)
    end_x = scale.x_for(follower_front_m + orange_trigger_gap_m)
    return GapArrow(
        start_x=start_x,
        end_x=end_x,
        y=y,
        label_x=(start_x + end_x) / 2.0,
        label_y=y - 12.0,
    )


def gap_arrow_y_for_status_rect_top(
    road_y: float,
    truck_height: float = TRUCK_BODY_HEIGHT_PX,
    status_rect_height: float = STATUS_RECT_HEIGHT_PX,
) -> float:
    return road_y - truck_height / 2.0 - status_rect_height


def target_triangle_points(x: float, road_line_y: float) -> tuple[float, float, float, float, float, float]:
    return (x, road_line_y - 16.0, x - 8.0, road_line_y, x + 8.0, road_line_y)


def lost_target_marker_x(scale: PositionScale, marker: LostTargetMarker, truck_length_m: float) -> float:
    return scale.x_for(marker.target_front_m - truck_length_m)


def lost_target_marker_color(marker: LostTargetMarker) -> str:
    if marker.follower == "Truck2":
        return "#1f77b4"
    if marker.follower == "Truck3":
        return "#2ca02c"
    return "#6f42c1"


def truck_color_for_label(label_lane: int) -> str:
    return TRUCK_IDENTITY_COLORS.get(label_lane, "#2ca02c")


def truck_wheel_centers(rear_x: float, front_x: float, bottom_y: float) -> tuple[tuple[float, float], tuple[float, float]]:
    width = max(front_x - rear_x, 1.0)
    wheel_y = bottom_y + 9.0
    return ((rear_x + width * 0.25, wheel_y), (rear_x + width * 0.75, wheel_y))


def lost_target_markers(
    rows: tuple[SimulationRow, ...],
    index: int,
    truck_length_m: float,
) -> tuple[LostTargetMarker, ...]:
    if not rows:
        return ()
    active_truck2_target: float | None = None
    active_truck3_target: float | None = None
    active_truck2_source = ""
    active_truck3_source = ""
    bounded_index = max(0, min(index, len(rows) - 1))

    for row_index, row in enumerate(rows[: bounded_index + 1]):
        if row.truck2_tracking_status == "Lost":
            if active_truck2_target is None:
                target_rear_m = row.truck2_loss_target_rear_m
                active_truck2_target = (target_rear_m + truck_length_m) if target_rear_m is not None else row.truck1_position_m
                active_truck2_source = row.truck2_loss_source or "Scenario"
            if row.truck2_position_m >= active_truck2_target - truck_length_m:
                active_truck2_target = None
                active_truck2_source = ""
        else:
            active_truck2_target = None
            active_truck2_source = ""

        if row.truck3_tracking_status == "Lost":
            if active_truck3_target is None:
                target_rear_m = row.truck3_loss_target_rear_m
                active_truck3_target = (target_rear_m + truck_length_m) if target_rear_m is not None else row.truck2_position_m
                active_truck3_source = row.truck3_loss_source or "Scenario"
            if row.truck3_position_m >= active_truck3_target - truck_length_m:
                active_truck3_target = None
                active_truck3_source = ""
        else:
            active_truck3_target = None
            active_truck3_source = ""

    markers: list[LostTargetMarker] = []
    if active_truck2_target is not None:
        markers.append(LostTargetMarker("Truck2", active_truck2_target, active_truck2_source))
    if active_truck3_target is not None:
        markers.append(LostTargetMarker("Truck3", active_truck3_target, active_truck3_source))
    return tuple(markers)


def follower_style(state: str, command: str, tracking_status: str, violation_type: str) -> TruckVisualStyle:
    combined = f"{state} {command} {violation_type}".lower()
    if "collision" in combined or "minimum gap violation" in combined or "red" in combined or "fort" in combined or "emergency" in combined:
        return TruckVisualStyle(fill="#ffd6d6", outline="#b00020", width=4)
    if "orange" in combined or "communication_request_stop" in combined or "communication stop" in combined:
        dash = (5, 3) if tracking_status == "Lost" else None
        return TruckVisualStyle(fill="#ffe8bf", outline="#d77a00", width=3, dash=dash)
    if tracking_status == "Lost":
        return TruckVisualStyle(fill="#fff3bf", outline="#8a6d00", width=3, dash=(5, 3))
    return TruckVisualStyle(fill="#dff5df", outline="#237a23", width=2)


def leader_style(row: SimulationRow) -> TruckVisualStyle:
    if row.communication_message and "Truck1" in row.communication_message:
        return TruckVisualStyle(fill="#e3ddff", outline="#5f3dc4", width=3)
    return TruckVisualStyle(fill="#e6eef8", outline="#24527a", width=2)


def label_y_positions(road_y: float, label_lane: int) -> tuple[float, float, float]:
    top_bubble_y = road_y - 132 + label_lane * 28
    bottom_bubble_y = road_y + 78 + label_lane * 30
    return top_bubble_y, bottom_bubble_y, bottom_bubble_y + 20


def origin_label_positions(road_y: float) -> tuple[tuple[str, float, float]]:
    x = CHART_LEFT_PX - 42.0
    return (("status / command / violation", x, road_y + 115.0),)


def compact_status(state: str, tracking_status: str) -> str:
    if not state and not tracking_status:
        return ""
    labels = {
        "STOPPED_WAITING": "Stopped waiting",
        "START_DELAY_COUNTING": "Start delay",
        "FOLLOWING_ACCELERATING": "Tracking: Accelerate",
        "FOLLOWING_MATCHING_SPEED": "Tracking: Match speed",
        "FOLLOWING_ORANGE_DECEL": "Tracking: Orange braking",
        "FOLLOWING_RED_BRAKING_TO_STOP": "Tracking: Red braking",
        "FORT_EMERGENCY_DECEL": "FORT emergency",
        "TRACKING_LOST_TO_LAST_POSITION": "Image identification loss",
        "TRACKING_RESUME_PENDING": "Resume pending",
        "COMMUNICATION_REQUEST_STOP": "Communication stop request",
        "IMMEDIATE_STOP_AFTER_LOSS_TIMEOUT": "Image resume timeout",
        "SAFETY_LOCK": "Safety Lock",
        "VIOLATION_STATE": "Violation state",
        "SIMULATION_FROZEN": "Simulation frozen",
        "LEADER_STOPPED": "Leader stopped",
        "LEADER_ACCELERATING": "Leader accelerating",
        "LEADER_DECELERATING": "Leader decelerating",
        "LEADER_CRUISING": "Leader cruising",
        "LEADER_COMMUNICATION_STOP": "Leader communication stop",
    }
    if state in labels:
        return labels[state]
    if not state:
        return tracking_status
    state_text = state.replace("FOLLOWING_", "").replace("TRACKING_", "").replace("_", " ").title()
    return f"{tracking_status}: {state_text}" if tracking_status else state_text


def compact_command(command: str, violation: str) -> str:
    if violation:
        return violation
    replacements = {
        "Match front-truck speed": "Match speed",
        "Accelerate to close gap": "Accelerate",
        "Accelerate after start delay": "Accelerate",
        "Accelerate initial start": "Accelerate",
        "Accelerate from stopped": "Accelerate",
        "Orange deceleration": "Orange braking",
        "Orange hold target speed": "Orange hold",
        "FORT emergency deceleration": "FORT emergency",
        "Red brake to stop": "Red braking",
        "Communication stop request": "Comm stop",
        "Lost tracking safe velocity": "Lost: safe velocity",
        "Lost tracking hold velocity": "Lost: hold velocity",
        "Lost tracking target stop": "Lost: target stop",
        "Lost tracking orange deceleration": "Lost: orange braking",
        "Follow leader profile acceleration": "Leader accelerating",
        "Follow leader profile deceleration": "Leader decelerating",
        "Follow leader profile speed": "Leader cruising",
        "Apply parking brakes": "Apply parking brakes",
    }
    return replacements.get(command, command)


def merged_status_label(state: str, tracking_status: str, command: str, violation: str) -> str:
    """Merge tracking/status, command, and violation into a single label."""
    # Violations take priority
    if violation:
        return violation

    # Tracking/status state information
    status_part = compact_status(state, tracking_status)

    # Command information
    command_part = compact_command(command, violation)

    # If both status and command are available, show status (it's more important)
    # If only command, show that
    if status_part:
        return status_part
    return command_part


def load_simulation_rows_csv(path: str | Path) -> tuple[SimulationRow, ...]:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        return tuple(_row_from_csv(row) for row in csv.DictReader(csv_file))


class ConvoyPlaybackCanvas:
    def __init__(
        self,
        parent: tk.Widget,
        width: int = 1100,
        height: int = 360,
        orange_distance_m: float | None = None,
        red_distance_m: float | None = None,
        loss_distance_m: float | None = None,
        resume_distance_m: float | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(parent, width=width, height=height, background="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self.rows: tuple[SimulationRow, ...] = ()
        self.truck_length_m = 8.0
        self.current_index = 0
        self.orange_distance_m = orange_distance_m
        self.red_distance_m = red_distance_m
        self.loss_distance_m = loss_distance_m
        self.resume_distance_m = resume_distance_m

    def _on_resize(self, event: tk.Event) -> None:
        self.width = max(1, int(event.width))
        self.height = max(220, int(event.height))
        if self.rows:
            self.draw_frame(self.current_index)

    def set_rows(self, rows: tuple[SimulationRow, ...], truck_length_m: float) -> None:
        self.rows = rows
        self.truck_length_m = truck_length_m
        self.draw_frame(0)

    def set_braking_distances(
        self,
        orange_distance_m: float | None,
        red_distance_m: float | None,
        loss_distance_m: float | None = None,
        resume_distance_m: float | None = None,
    ) -> None:
        self.orange_distance_m = orange_distance_m
        self.red_distance_m = red_distance_m
        self.loss_distance_m = loss_distance_m
        self.resume_distance_m = resume_distance_m
        self.draw_frame(self.current_index)

    def draw_frame(self, index: int) -> None:
        self.canvas.delete("all")
        if not self.rows:
            self.canvas.create_text(self.width / 2, self.height / 2, text="Run a simulation to view Stage C playback.")
            return

        index = max(0, min(index, len(self.rows) - 1))
        self.current_index = index
        row = self.rows[index]
        scale = position_scale_for_rows(
            self.rows,
            self.truck_length_m,
            self.width,
            margin_px=int(CHART_LEFT_PX),
            right_margin_px=int(CHART_RIGHT_MARGIN_PX),
        )
        road_y = max(100.0, min(160.0, self.height * 0.40))
        truck_height = TRUCK_BODY_HEIGHT_PX
        road_line_y = road_y + truck_height / 2 + 18
        gap_y = gap_arrow_y_for_status_rect_top(road_y, truck_height)

        self.canvas.create_line(CHART_LEFT_PX, road_line_y, self.width - CHART_RIGHT_MARGIN_PX, road_line_y, fill="#888", width=2)
        self._draw_distance_ticks(scale, road_line_y)
        self._draw_origin_labels(road_y)
        truck2_orange_gap_y = gap_y - 40.0
        truck3_orange_gap_y = gap_y - 60.0
        self._draw_orange_trigger_gap(
            scale,
            row.truck2_position_m,
            row.truck2_orange_trigger_gap_m,
            truck2_orange_gap_y,
            label_below=True,
        )
        self._draw_orange_trigger_gap(
            scale,
            row.truck3_position_m,
            row.truck3_orange_trigger_gap_m,
            truck3_orange_gap_y,
            label_below=True,
        )
        self._draw_gap(scale, row.truck2_position_m, row.truck1_position_m, row.truck2_gap_m, gap_y)
        self._draw_gap(scale, row.truck3_position_m, row.truck2_position_m, row.truck3_gap_m, gap_y)
        self._draw_truck(scale, row.truck3_position_m, road_y, row.truck3_velocity_kph, row.truck3_tracking_status, row.truck3_state, row.truck3_command, row.violation_type_truck3, label_lane=0)
        self._draw_truck(scale, row.truck2_position_m, road_y, row.truck2_velocity_kph, row.truck2_tracking_status, row.truck2_state, row.truck2_command, row.violation_type_truck2, label_lane=1)
        self._draw_truck(scale, row.truck1_position_m, road_y, row.truck1_velocity_kph, "", row.truck1_state, row.truck1_command, "", label_lane=2)
        self._draw_lost_target_markers(scale, lost_target_markers(self.rows, index, self.truck_length_m), road_line_y)
        self._draw_header(row)

    def _draw_header(self, row: SimulationRow) -> None:
        if row.communication_message:
            text = f"Communication: {row.communication_status} — {row.communication_message}"
            self.canvas.create_text(16, 14, anchor="w", text=text, font=("Arial", 10))

    def _draw_distance_ticks(self, scale: PositionScale, road_line_y: float) -> None:
        for value in distance_tick_values(scale.min_position_m, scale.max_position_m):
            x = scale.x_for(value)
            self.canvas.create_line(x, road_line_y, x, road_line_y + 7, fill="#777")
            self.canvas.create_text(x, road_line_y + 18, text=f"{value:.0f}", font=("Arial", 7), fill="#555")

    def _draw_braking_distances(self, row: SimulationRow, road_line_y: float) -> None:
        if (
            self.orange_distance_m is None
            and self.red_distance_m is None
            and self.loss_distance_m is None
            and self.resume_distance_m is None
        ):
            return
        if row.orange_braking_mode == 1:
            orange_text = "Orange mode: TimeHeadway"
        else:
            orange_text = "Orange distance: n/a" if self.orange_distance_m is None else f"Orange distance: {self.orange_distance_m:.1f} m"
        red_text = "Red distance: n/a" if self.red_distance_m is None else f"Red distance: {self.red_distance_m:.1f} m"
        loss_text = "ID loss distance: n/a" if self.loss_distance_m is None else f"ID loss distance: {self.loss_distance_m:.1f} m"
        resume_text = "ID resume distance: n/a" if self.resume_distance_m is None else f"ID resume distance: {self.resume_distance_m:.1f} m"
        # Position legend below the x-axis line
        legend_offset = 50
        self.canvas.create_text(
            self.width - CHART_RIGHT_MARGIN_PX - 8,
            road_line_y + legend_offset,
            anchor="ne",
            text=orange_text,
            font=("Arial", 10, "bold"),
            fill="#d77a00",
        )
        self.canvas.create_text(
            self.width - CHART_RIGHT_MARGIN_PX - 8,
            road_line_y + legend_offset + 18,
            anchor="ne",
            text=red_text,
            font=("Arial", 10, "bold"),
            fill="#b00020",
        )
        self.canvas.create_text(
            self.width - CHART_RIGHT_MARGIN_PX - 8,
            road_line_y + legend_offset + 36,
            anchor="ne",
            text=loss_text,
            font=("Arial", 10, "bold"),
            fill="#444",
        )
        self.canvas.create_text(
            self.width - CHART_RIGHT_MARGIN_PX - 8,
            road_line_y + legend_offset + 54,
            anchor="ne",
            text=resume_text,
            font=("Arial", 10, "bold"),
            fill="#444",
        )

    def _draw_origin_labels(self, road_y: float) -> None:
        for text, x, y in origin_label_positions(road_y):
            clamped_y = min(y, self.height - 80)
            self.canvas.create_text(x, clamped_y, text=text, angle=90, font=("Arial", 8), fill="#555")

    def _draw_truck(
        self,
        scale: PositionScale,
        front_m: float,
        road_y: float,
        velocity_kph: float,
        tracking_status: str,
        state: str,
        command: str,
        violation: str,
        label_lane: int,
    ) -> None:
        front_x = scale.x_for(front_m)
        rear_x = scale.x_for(front_m - self.truck_length_m)
        half_height = TRUCK_BODY_HEIGHT_PX / 2.0
        top_y = road_y - half_height
        bottom_y = road_y + half_height
        body_style = truck_body_style(label_lane)
        status_style = status_indicator_style(label_lane, state, command, tracking_status, violation)
        self.canvas.create_rectangle(
            rear_x,
            top_y - STATUS_RECT_HEIGHT_PX,
            front_x,
            top_y - 5,
            fill=status_style.fill,
            outline=status_style.outline,
            width=status_style.width,
            dash=status_style.dash,
        )
        self.canvas.create_rectangle(
            rear_x,
            top_y,
            front_x,
            bottom_y,
            fill=body_style.fill,
            outline=body_style.outline,
            width=body_style.width,
        )
        wheel_color = truck_color_for_label(label_lane)
        for wheel_x, wheel_y in truck_wheel_centers(rear_x, front_x, bottom_y):
            radius = TRUCK_WHEEL_RADIUS_PX
            self.canvas.create_oval(
                wheel_x - radius,
                wheel_y - radius,
                wheel_x + radius,
                wheel_y + radius,
                fill=wheel_color,
                outline="#222",
            )
        center_x = (rear_x + front_x) / 2.0
        top_bubble_y, bottom_bubble_y, _detail_y = label_y_positions(road_y, label_lane)
        self.canvas.create_text(
            center_x,
            (top_y + bottom_y) / 2.0,
            text=f"{velocity_kph:.1f}",
            font=("Arial", 9, "bold"),
            fill=truck_text_color(label_lane),
        )
        # Show single merged label combining status, command, and violation
        label = merged_status_label(state, tracking_status, command, violation)
        if label:
            self._draw_bubble(center_x, bottom_bubble_y, label, status_style.outline)

    def _draw_gap(self, scale: PositionScale, follower_front_m: float, front_truck_front_m: float, gap_m: float, y: float) -> None:
        arrow = gap_arrow_coordinates(scale, follower_front_m, front_truck_front_m, self.truck_length_m, y)
        self.canvas.create_line(arrow.start_x, arrow.y, arrow.end_x, arrow.y, fill="#444", arrow=tk.BOTH)
        self.canvas.create_text(arrow.label_x, arrow.label_y, text=f"{gap_m:.1f} m", font=("Arial", 9))

    def _draw_orange_trigger_gap(
        self,
        scale: PositionScale,
        follower_front_m: float,
        orange_trigger_gap_m: float,
        y: float,
        label_below: bool,
    ) -> None:
        arrow = orange_trigger_gap_arrow_coordinates(scale, follower_front_m, orange_trigger_gap_m, y)
        self.canvas.create_line(arrow.start_x, arrow.y, arrow.end_x, arrow.y, fill=ORANGE_STATUS_COLOR, arrow=tk.BOTH)
        label_y = arrow.y + 12.0 if label_below else arrow.label_y
        self.canvas.create_text(
            arrow.label_x,
            label_y,
            text=f"{orange_trigger_gap_m:.1f} m",
            font=("Arial", 8, "bold"),
            fill=ORANGE_STATUS_COLOR,
        )

    def _draw_bubble(self, center_x: float, center_y: float, text: str, outline: str) -> None:
        half_width = min(150.0, max(48.0, len(text) * 3.7))
        self.canvas.create_rectangle(
            center_x - half_width,
            center_y - 10,
            center_x + half_width,
            center_y + 10,
            fill="#ffffff",
            outline=outline,
            width=1,
        )
        self.canvas.create_text(center_x, center_y, text=text, font=("Arial", 8))

    def _draw_lost_target_markers(self, scale: PositionScale, markers: tuple[LostTargetMarker, ...], road_line_y: float) -> None:
        for marker in markers:
            x = lost_target_marker_x(scale, marker, self.truck_length_m)
            color = lost_target_marker_color(marker)
            fill = color if marker.loss_source == "Distance" else "#ffffff"
            self.canvas.create_polygon(*target_triangle_points(x, road_line_y), outline=color, fill=fill, width=2)


class ConvoyTimelineChart:
    def __init__(
        self,
        parent: tk.Widget,
        title: str = "Gap vs Time",
        y_label: str = "Gap (m)",
        series: tuple[ChartSeries, ...] | None = None,
        width: int = 1100,
        height: int = 120,
        y_max_cap: float | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.title = title
        self.y_label = y_label
        self.y_max_cap = y_max_cap
        self.series = series or (
            ChartSeries(
                "Truck2 gap",
                "#1f77b4",
                lambda row: row.truck2_gap_m,
                lambda row: row.truck2_tracking_status == "Lost",
                lambda row: chart_stroke_width(row.truck2_state, row.truck2_command),
            ),
            ChartSeries(
                "Truck3 gap",
                "#ff7f0e",
                lambda row: row.truck3_gap_m,
                lambda row: row.truck3_tracking_status == "Lost",
                lambda row: chart_stroke_width(row.truck3_state, row.truck3_command),
            ),
        )
        self.canvas = tk.Canvas(parent, width=width, height=height, background="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self.rows: tuple[SimulationRow, ...] = ()
        self.current_index = 0

    def _on_resize(self, event: tk.Event) -> None:
        self.width = max(1, int(event.width))
        self.height = max(80, int(event.height))
        if self.rows:
            self.draw(self.current_index)

    def set_rows(self, rows: tuple[SimulationRow, ...]) -> None:
        self.rows = rows
        self.draw(0)

    def draw(self, index: int) -> None:
        self.canvas.delete("all")
        if not self.rows:
            self.canvas.create_text(self.width / 2, self.height / 2, text="Gap chart appears after simulation.")
            return

        self.current_index = max(0, min(index, len(self.rows) - 1))
        left_px = CHART_LEFT_PX
        right_px = self.width - CHART_RIGHT_MARGIN_PX
        top_px = 22.0
        bottom_px = self.height - 42.0
        raw_y_max = max(max(series.value_for_row(row) for series in self.series) for row in self.rows) or 1.0
        if self.y_max_cap is not None:
            y_max = max(min(raw_y_max * 1.2, self.y_max_cap), 1.0)
        else:
            y_max = raw_y_max
        self.canvas.create_line(left_px, bottom_px, right_px, bottom_px, fill="#777")
        self.canvas.create_line(left_px, top_px, left_px, bottom_px, fill="#777")
        self.canvas.create_text(left_px, 10, anchor="w", text=self.title, font=("Arial", 9, "bold"))
        self.canvas.create_text(14, (top_px + bottom_px) / 2, text=self.y_label, angle=90, font=("Arial", 8))
        self._draw_y_ticks(y_max, left_px, right_px, top_px, bottom_px)
        self._draw_x_ticks(left_px, bottom_px, right_px)
        for series in self.series:
            self._draw_series(series, y_max, left_px, right_px, top_px, bottom_px)
        current_row = self.rows[self.current_index]
        marker_x = marker_x_for_time(self.rows, current_row.time_s, left_px, right_px)
        self.canvas.create_line(marker_x, top_px, marker_x, bottom_px, fill="#111", width=2)
        legend = ", ".join(f"{series.label}" for series in self.series)
        self.canvas.create_text(right_px, 10, anchor="e", text=legend, font=("Arial", 8))
        self.canvas.create_text((left_px + right_px) / 2.0, self.height - 8, anchor="center", text="Time (s)", font=("Arial", 8))

    def _draw_y_ticks(self, y_max: float, left_px: float, right_px: float, top_px: float, bottom_px: float) -> None:
        for value in y_tick_values(y_max):
            y = bottom_px - (value / max(y_max, 1.0)) * (bottom_px - top_px)
            self.canvas.create_line(left_px - 4, y, left_px, y, fill="#777")
            self.canvas.create_line(left_px, y, right_px, y, fill="#eeeeee")
            self.canvas.create_text(left_px - 8, y, anchor="e", text=format_y_tick(value), font=("Arial", 8))

    def _draw_x_ticks(self, left_px: float, bottom_px: float, right_px: float) -> None:
        if not self.rows:
            return
        for value in time_tick_values(self.rows[0].time_s, self.rows[-1].time_s):
            x = marker_x_for_time(self.rows, value, left_px, right_px)
            self.canvas.create_line(x, bottom_px, x, bottom_px + 4, fill="#777")
            self.canvas.create_line(x, bottom_px, x, 22.0, fill="#eeeeee")
            label = format_time_tick(value)
            if label:
                self.canvas.create_text(x, bottom_px + 15, anchor="center", text=label, font=("Arial", 8))

    def _draw_series(self, series: ChartSeries, y_max: float, left_px: float, right_px: float, top_px: float, bottom_px: float) -> None:
        if len(self.rows) < 2:
            return
        for index in range(len(self.rows) - 1):
            start = self.rows[index]
            end = self.rows[index + 1]
            start_x = marker_x_for_time(self.rows, start.time_s, left_px, right_px)
            end_x = marker_x_for_time(self.rows, end.time_s, left_px, right_px)
            start_y = bottom_px - (series.value_for_row(start) / y_max) * (bottom_px - top_px)
            end_y = bottom_px - (series.value_for_row(end) / y_max) * (bottom_px - top_px)
            if series.segment_style_for_rows is not None:
                style = series.segment_style_for_rows(start, end)
                color = style.color
                width = style.width
                dash = style.dash
            else:
                color = series.color
                dash = (5, 4) if series.is_dotted_for_row(start) or series.is_dotted_for_row(end) else None
                width = max(series.width_for_row(start), series.width_for_row(end))
            self.canvas.create_line(start_x, start_y, end_x, end_y, fill=color, width=width, dash=dash)


def _row_from_csv(row: dict[str, str]) -> SimulationRow:
    return SimulationRow(
        time_s=_float(row, "Time_s"),
        truck1_position_m=_float(row, "Truck1_Position_m"),
        truck2_position_m=_float(row, "Truck2_Position_m"),
        truck3_position_m=_float(row, "Truck3_Position_m"),
        truck2_gap_m=_float(row, "Truck2_Gap_m"),
        truck3_gap_m=_float(row, "Truck3_Gap_m"),
        gap2_violation=_bool(row, "Gap2_Violation"),
        gap3_violation=_bool(row, "Gap3_Violation"),
        truck1_velocity_kph=_float(row, "Truck1_Velocity_kph"),
        truck2_velocity_kph=_float(row, "Truck2_Velocity_kph"),
        truck3_velocity_kph=_float(row, "Truck3_Velocity_kph"),
        truck1_acceleration_mps2=_float(row, "Truck1_Acceleration_mps2"),
        truck2_acceleration_mps2=_float(row, "Truck2_Acceleration_mps2"),
        truck3_acceleration_mps2=_float(row, "Truck3_Acceleration_mps2"),
        truck2_state=row.get("Truck2_State", ""),
        truck3_state=row.get("Truck3_State", ""),
        truck2_command=row.get("Truck2_Command", ""),
        truck3_command=row.get("Truck3_Command", ""),
        truck2_actual_gap_m=_float(row, "Truck2_Actual_Gap_m"),
        truck2_measured_gap_m=_float(row, "Truck2_Measured_Gap_m"),
        truck3_actual_gap_m=_float(row, "Truck3_Actual_Gap_m"),
        truck3_measured_gap_m=_float(row, "Truck3_Measured_Gap_m"),
        truck2_tracking_status=row.get("Truck2_Tracking_Status", ""),
        truck3_tracking_status=row.get("Truck3_Tracking_Status", ""),
        truck2_relative_velocity_kph=_float(row, "Truck2_Relative_Velocity_kph"),
        truck3_relative_velocity_kph=_float(row, "Truck3_Relative_Velocity_kph"),
        communication_message=row.get("Communication_Message", ""),
        communication_status=row.get("Communication_Status", ""),
        violation_type_truck2=row.get("Violation_Type_Truck2", ""),
        violation_type_truck3=row.get("Violation_Type_Truck3", ""),
        stop_reason_truck2=row.get("Stop_Reason_Truck2", ""),
        stop_reason_truck3=row.get("Stop_Reason_Truck3", ""),
        truck1_state=row.get("Truck1_State", ""),
        truck1_command=row.get("Truck1_Command", ""),
        truck2_loss_source=row.get("Truck2_Loss_Source", ""),
        truck3_loss_source=row.get("Truck3_Loss_Source", ""),
        truck2_loss_target_rear_m=_optional_float(row, "Truck2_Loss_Target_Rear_m"),
        truck3_loss_target_rear_m=_optional_float(row, "Truck3_Loss_Target_Rear_m"),
        truck2_orange_trigger_gap_m=_float(row, "Truck2_Orange_Trigger_Gap_m"),
        truck3_orange_trigger_gap_m=_float(row, "Truck3_Orange_Trigger_Gap_m"),
        orange_braking_mode=int(_float(row, "Orange_Braking_Mode")),
    )


def _float(row: dict[str, str], key: str) -> float:
    return float(row.get(key, "0") or 0.0)


def _optional_float(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    return None if value == "" else float(value)


def _bool(row: dict[str, str], key: str) -> bool:
    return row.get(key, "").strip().lower() == "yes"
