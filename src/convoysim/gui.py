"""Minimal Stage A GUI for running and reviewing simulations."""

from __future__ import annotations

from pathlib import Path
import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from convoysim.charts import write_stage_a_charts_html
from convoysim.gui_helpers import (
    CsvTable,
    PARAMETER_CATEGORY_ORDER,
    SCENARIO_IMAGE_EVENT_OPTIONS,
    TRUCK_COLORS,
    display_log_rows,
    display_log_rows_from_csv,
    display_cell_value,
    display_output_columns,
    help_row_matches_filter,
    is_scenario_image_event_column,
    load_csv_table,
    load_state_machine_help,
    output_column_group,
    output_header_label,
    parameter_category,
    parameter_row_matches_filter,
    preferred_column_width,
    table_column_anchor,
    write_csv_table,
)
from convoysim.optimization import (
    BulkSimulationRunRow,
    BulkSimulationResult,
    bulk_row_cost_value,
    bulk_cost_function_names,
    bulk_parameter_names,
    generate_parameter_values,
    load_cost_function_weights_csv,
    run_bulk_simulations_from_files,
)
from convoysim.braking import BrakingDistanceTable
from convoysim.live_stepper import (
    FORT_BRAKE,
    HOLD,
    ORANGE_BRAKE,
    RED_BRAKE,
    LiveLeaderCommand,
    LiveSimStepper,
    accelerate,
    decelerate,
)
from convoysim.parameters import load_parameters_csv
from convoysim.run_config import (
    StageARunConfig,
    load_stage_a_run_config,
    output_dir_from_previous_path,
    save_stage_a_run_config,
    timestamped_stage_a_paths,
)
from convoysim.scenario_timeline import ScenarioTimeline
from convoysim.simulation import SimulationRow, run_basic_simulation_from_files
from convoysim.visualization import (
    CHART_LEFT_PX,
    CHART_RIGHT_MARGIN_PX,
    ChartSeries,
    ConvoyPlaybackCanvas,
    ConvoyTimelineChart,
    chart_stroke_width,
    follower_chart_segment_style,
    load_simulation_rows_csv,
    nearest_row_index,
    truck_color_for_label,
)

_TOTAL_WEIGHTED_COST_LABEL = "Total weighted cost"
_BULK_COST_CHART_JPG = "Bulk_Cost_Function_Totals_Chart.jpg"
_BULK_WEIGHTED_CHART_JPG = "Bulk_Total_Weighted_Cost_Chart.jpg"


def playback_delay_ms(speed: float, base_delay_ms: int = 100) -> int:
    return max(1, int(round(base_delay_ms / max(0.1, speed))))


def _wrapped_bulk_heading(column: str) -> str:
    words = column.replace("_", " ").split()
    if len(words) <= 2:
        return " ".join(words)
    midpoint = (len(words) + 1) // 2
    return f"{' '.join(words[:midpoint])}\n{' '.join(words[midpoint:])}"


def _bulk_number_label(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _bulk_chart_point_is_selected(
    selected: tuple[float, str, str] | None,
    parameter_value: float,
    cost_function: str,
    chart_id: str,
) -> bool:
    return (
        selected is not None
        and abs(selected[0] - parameter_value) < 1e-9
        and selected[1] == cost_function
        and selected[2] == chart_id
    )


class BulkVisualizationWindow:
    def __init__(
        self,
        parent: tk.Tk,
        header: str,
        rows: tuple[SimulationRow, ...],
        truck_length_m: float,
        distances: tuple[float | None, float | None, float | None, float | None],
        playback_speed: float,
        on_close: object | None = None,
    ) -> None:
        self.parent = parent
        self.rows = rows
        self.truck_length_m = truck_length_m
        self.current_frame_index = 0
        self.is_playing = False
        self.playback_after_id: str | None = None
        self.on_close = on_close
        self.window = tk.Toplevel(parent)
        self.window.title("ConvoySIM Bulk Visualization")
        self.window.geometry("1280x860")
        self.window.minsize(1000, 720)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.time_var = tk.DoubleVar(master=self.window, value=0.0)
        self.time_label_var = tk.StringVar(master=self.window, value="Time: 0.0s")
        self.playback_speed_var = tk.DoubleVar(master=self.window, value=playback_speed)
        self.playback_speed_label_var = tk.StringVar(master=self.window, value=f"Speed: x{playback_speed:.1f}")
        self.show_gap_chart_var = tk.BooleanVar(master=self.window, value=True)
        self.show_velocity_chart_var = tk.BooleanVar(master=self.window, value=True)
        self.show_truck2_velocity_var = tk.BooleanVar(master=self.window, value=True)
        self.show_truck3_velocity_var = tk.BooleanVar(master=self.window, value=True)
        self._updating_time_scale = False

        tk.Label(self.window, text=header, anchor="w", font=("Arial", 11, "bold"), fg="#333").pack(
            fill=tk.X,
            padx=8,
            pady=(6, 0),
        )
        controls = ttk.Frame(self.window)
        controls.pack(fill=tk.X, padx=6, pady=6)
        self._button(controls, ">", self.play, "play").pack(side=tk.LEFT, padx=4)
        self._button(controls, "||", self.pause, "play").pack(side=tk.LEFT, padx=4)
        self._button(controls, "[]", self.stop, "danger").pack(side=tk.LEFT, padx=4)
        self._button(controls, "<<", self.step_back, "utility").pack(side=tk.LEFT, padx=4)
        self._button(controls, ">>", self.step_forward, "utility").pack(side=tk.LEFT, padx=4)
        self._button(controls, "Toggle Legend", self.toggle_legend, "view").pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(controls, text="Show gap charts", variable=self.show_gap_chart_var, command=self._apply_chart_visibility).pack(
            side=tk.LEFT,
            padx=(14, 4),
        )
        ttk.Checkbutton(
            controls,
            text="Show velocity chart",
            variable=self.show_velocity_chart_var,
            command=self._apply_chart_visibility,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(controls, text="T2", variable=self.show_truck2_velocity_var, command=self._redraw_velocity_chart).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Checkbutton(controls, text="T3", variable=self.show_truck3_velocity_var, command=self._redraw_velocity_chart).pack(side=tk.LEFT, padx=4)
        ttk.Label(controls, textvariable=self.time_label_var).pack(side=tk.LEFT, padx=12)
        ttk.Label(controls, textvariable=self.playback_speed_label_var).pack(side=tk.LEFT, padx=(18, 4))
        ttk.Scale(
            controls,
            from_=0.3,
            to=2.0,
            orient=tk.HORIZONTAL,
            variable=self.playback_speed_var,
            command=self._on_playback_speed_changed,
            length=160,
        ).pack(side=tk.LEFT, padx=4)

        orange_distance_m, red_distance_m, loss_distance_m, resume_distance_m = distances
        self.pane = tk.PanedWindow(self.window, orient=tk.VERTICAL, sashwidth=8, sashrelief=tk.RAISED, showhandle=True)
        self.pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        visualization_frame = ttk.Frame(self.pane)
        charts_frame = ttk.Frame(self.pane)
        self.pane.add(visualization_frame, minsize=280)
        self.pane.add(charts_frame, minsize=180)
        self.visualization = ConvoyPlaybackCanvas(
            visualization_frame,
            width=1220,
            height=360,
            orange_distance_m=orange_distance_m,
            red_distance_m=red_distance_m,
            loss_distance_m=loss_distance_m,
            resume_distance_m=resume_distance_m,
        )
        self.gap12_chart = ConvoyTimelineChart(
            charts_frame,
            title="Gap1-2 vs Time",
            y_label="Gap (m)",
            series=(ChartSeries("Gap1-2", truck_color_for_label(1), lambda row: row.truck2_gap_m, segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck2", start, end)),),
            width=1220,
            height=120,
            y_max_cap=40.0,
        )
        self.gap23_chart = ConvoyTimelineChart(
            charts_frame,
            title="Gap2-3 vs Time",
            y_label="Gap (m)",
            series=(ChartSeries("Gap2-3", truck_color_for_label(0), lambda row: row.truck3_gap_m, segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck3", start, end)),),
            width=1220,
            height=120,
            y_max_cap=40.0,
        )
        velocity_series_list = [ChartSeries("Truck1 velocity", "#333333", lambda row: row.truck1_velocity_kph)]
        if self.show_truck2_velocity_var.get():
            velocity_series_list.append(
                ChartSeries(
                    "Truck2 velocity",
                    truck_color_for_label(1),
                    lambda row: row.truck2_velocity_kph,
                    lambda row: row.truck2_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck2_state, row.truck2_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck2", start, end, default_dashed_for_truck2=True),
                )
            )
        if self.show_truck3_velocity_var.get():
            velocity_series_list.append(
                ChartSeries(
                    "Truck3 velocity",
                    truck_color_for_label(0),
                    lambda row: row.truck3_velocity_kph,
                    lambda row: row.truck3_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck3_state, row.truck3_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck3", start, end),
                )
            )
        self.velocity_chart = ConvoyTimelineChart(
            charts_frame,
            title="Velocity vs Time",
            y_label="Velocity (kph)",
            series=tuple(velocity_series_list),
            width=1220,
            height=120,
        )
        self.time_scale = ttk.Scale(
            charts_frame,
            from_=0.0,
            to=rows[-1].time_s if rows else 0.0,
            orient=tk.HORIZONTAL,
            variable=self.time_var,
            command=self._on_time_scale_changed,
        )
        self.time_scale.pack(fill=tk.X, padx=(int(CHART_LEFT_PX), int(CHART_RIGHT_MARGIN_PX)), pady=(6, 8))
        self.legend_frame = self._build_legend(self.window)
        self.legend_frame.pack(fill=tk.X, padx=8, pady=(0, 8), before=self.pane)
        self.window.bind("<Left>", lambda _e: self._keyboard_jump(-1.0))
        self.window.bind("<Right>", lambda _e: self._keyboard_jump(1.0))
        self.window.bind("<Home>", lambda _e: self.stop())
        self.window.bind("<End>", lambda _e: self._keyboard_jump_to_end())
        self._apply_chart_visibility()
        self.set_rows(rows)

    def _button(self, parent: tk.Widget, text: str, command: object, role: str) -> tk.Button:
        colors = {
            "play": ("#00897b", "#ffffff"),
            "view": ("#5e35b1", "#ffffff"),
            "danger": ("#b00020", "#ffffff"),
            "utility": ("#546e7a", "#ffffff"),
        }
        background, foreground = colors[role]
        return tk.Button(parent, text=text, command=command, bg=background, fg=foreground, width=3 if len(text) <= 2 else 12)

    def _build_legend(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)
        items = (
            ("Truck #1", truck_color_for_label(2), None, 4),
            ("Truck #2 / Gap1-2", truck_color_for_label(1), None, 4),
            ("Truck #3 / Gap2-3", truck_color_for_label(0), None, 4),
            ("Image lost", truck_color_for_label(1), (5, 4), 3),
            ("Orange braking", "#d77a00", None, 4),
            ("Red braking / violation", "#b00020", None, 4),
        )
        for index, (text, color, dash, width) in enumerate(items):
            item = tk.Frame(frame)
            item.grid(row=0, column=index, sticky="w", padx=8, pady=3)
            swatch = tk.Canvas(item, width=40, height=12, highlightthickness=0)
            swatch.pack(side=tk.LEFT)
            swatch.create_line(2, 6, 38, 6, fill=color, width=width, dash=dash)
            tk.Label(item, text=text).pack(side=tk.LEFT, padx=4)
        return frame

    def set_rows(self, rows: tuple[SimulationRow, ...]) -> None:
        self.rows = rows
        if self.time_scale is not None:
            self.time_scale.configure(to=rows[-1].time_s if rows else 0.0)
        self.visualization.set_rows(rows, self.truck_length_m)
        self.gap12_chart.set_rows(rows)
        self.gap23_chart.set_rows(rows)
        self.velocity_chart.set_rows(rows)
        self.draw_frame(0)

    def _apply_chart_visibility(self) -> None:
        for chart in (self.gap12_chart, self.gap23_chart, self.velocity_chart):
            chart.canvas.pack_forget()
        self._set_chart_visible(self.gap12_chart, self.show_gap_chart_var.get())
        self._set_chart_visible(self.gap23_chart, self.show_gap_chart_var.get())
        self._set_chart_visible(self.velocity_chart, self.show_velocity_chart_var.get())

    def _set_chart_visible(self, chart: ConvoyTimelineChart, visible: bool) -> None:
        if visible:
            chart.canvas.pack(fill=tk.BOTH, expand=True, before=self.time_scale)

    def _redraw_velocity_chart(self) -> None:
        """Rebuild velocity chart with only selected truck velocity lines."""
        if not hasattr(self, 'velocity_chart') or self.velocity_chart is None:
            return

        # Store current rows to redraw
        rows = self.velocity_chart.rows
        current_index = self.velocity_chart.current_index

        # Find the parent frame where the chart is packed
        charts_frame = self.velocity_chart.canvas.master

        # Destroy old chart canvas
        self.velocity_chart.canvas.pack_forget()
        self.velocity_chart.canvas.destroy()

        # Build new series based on visibility checkboxes
        series_list = [ChartSeries("Truck1 velocity", "#333333", lambda row: row.truck1_velocity_kph)]

        if self.show_truck2_velocity_var.get():
            series_list.append(
                ChartSeries(
                    "Truck2 velocity",
                    truck_color_for_label(1),
                    lambda row: row.truck2_velocity_kph,
                    lambda row: row.truck2_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck2_state, row.truck2_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck2", start, end, default_dashed_for_truck2=True),
                )
            )

        if self.show_truck3_velocity_var.get():
            series_list.append(
                ChartSeries(
                    "Truck3 velocity",
                    truck_color_for_label(0),
                    lambda row: row.truck3_velocity_kph,
                    lambda row: row.truck3_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck3_state, row.truck3_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck3", start, end),
                )
            )

        # Create new chart with filtered series
        self.velocity_chart = ConvoyTimelineChart(
            charts_frame,
            title="Velocity vs Time",
            y_label="Velocity (kph)",
            series=tuple(series_list),
            width=1220,
            height=120,
        )

        # Restore rows and redraw
        if rows:
            self.velocity_chart.set_rows(rows)
            if current_index < len(rows):
                self.velocity_chart.draw(current_index)

        # Make chart visible if needed
        if self.show_velocity_chart_var.get():
            self._set_chart_visible(self.velocity_chart, True)

    def play(self) -> None:
        if not self.rows:
            return
        self.is_playing = True
        self._schedule_next_frame()

    def pause(self) -> None:
        self.is_playing = False
        if self.playback_after_id is not None:
            self.window.after_cancel(self.playback_after_id)
            self.playback_after_id = None

    def stop(self) -> None:
        self.pause()
        self.draw_frame(0)

    def step_back(self) -> None:
        self.pause()
        self.draw_frame(self.current_frame_index - 1)

    def step_forward(self) -> None:
        self.pause()
        self.draw_frame(self.current_frame_index + 1)

    def _keyboard_jump(self, delta_seconds: float) -> None:
        if not self.rows:
            return
        current_time = self.rows[self.current_frame_index].time_s
        self.pause()
        self.draw_frame(nearest_row_index(self.rows, current_time + delta_seconds))

    def _keyboard_jump_to_end(self) -> None:
        if not self.rows:
            return
        self.pause()
        self.draw_frame(len(self.rows) - 1)

    def toggle_legend(self) -> None:
        if self.legend_frame.winfo_ismapped():
            self.legend_frame.pack_forget()
        else:
            self.legend_frame.pack(fill=tk.X, padx=8, pady=(0, 8), before=self.pane)

    def _schedule_next_frame(self) -> None:
        if not self.is_playing:
            return
        if self.current_frame_index >= len(self.rows) - 1:
            self.pause()
            return
        self.draw_frame(self.current_frame_index + 1)
        self.playback_after_id = self.window.after(playback_delay_ms(self.playback_speed_var.get()), self._schedule_next_frame)

    def draw_frame(self, index: int) -> None:
        if not self.rows:
            self.current_frame_index = 0
            self.time_label_var.set("Time: 0.0s")
            self.visualization.draw_frame(0)
            self.gap12_chart.draw(0)
            self.gap23_chart.draw(0)
            self.velocity_chart.draw(0)
            return
        self.current_frame_index = max(0, min(index, len(self.rows) - 1))
        row = self.rows[self.current_frame_index]
        self.visualization.draw_frame(self.current_frame_index)
        self.gap12_chart.draw(self.current_frame_index)
        self.gap23_chart.draw(self.current_frame_index)
        self.velocity_chart.draw(self.current_frame_index)
        self.time_label_var.set(f"Time: {row.time_s:.1f}s")
        self._updating_time_scale = True
        self.time_var.set(row.time_s)
        self._updating_time_scale = False

    def _on_time_scale_changed(self, value: str) -> None:
        if self._updating_time_scale or not self.rows:
            return
        self.pause()
        self.draw_frame(nearest_row_index(self.rows, float(value)))

    def _on_playback_speed_changed(self, value: str) -> None:
        self.playback_speed_label_var.set(f"Speed: x{float(value):.1f}")

    def close(self) -> None:
        self.pause()
        if callable(self.on_close):
            self.on_close(self)
        self.window.destroy()


# ---------------------------------------------------------------------------
# Online Visualization — live leader-control popup
# ---------------------------------------------------------------------------

def _next_version_name(scenario_path: str) -> str:
    """Return <stem>_Ver<N+1>.csv where N is the highest existing _VerN suffix."""
    path = Path(scenario_path)
    stem = path.stem
    parent = path.parent
    existing = [p.stem for p in parent.glob(f"{stem}_Ver*.csv")]
    max_n = 0
    for name in existing:
        suffix = name[len(stem) + 4:]  # strip "<stem>_Ver"
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return str(parent / f"{stem}_Ver{max_n + 1}.csv")


def _save_online_scenario(
    scenario_path: str,
    live_entry_time_s: float,
    live_rows: tuple[SimulationRow, ...],
    save_path: str,
) -> None:
    """Write a merged scenario CSV: original rows up to live_entry_time,
    then live rows (leader velocity from simulation; Trucks 2/3 events from original)."""
    timeline = ScenarioTimeline.from_csv(scenario_path)

    # Build lookup: time → (truck1_event, truck2_event, truck3_event)
    t1_events = {e.time_s: e.event.value for e in timeline.truck1_events()}
    t2_events = {e.time_s: e.event.value for e in timeline.truck2_image_events()}
    t3_events = {e.time_s: e.event.value for e in timeline.truck3_image_events()}

    # Collect original rows up to the live-entry boundary
    original_rows = [
        row for row in timeline.rows
        if row.time_s <= live_entry_time_s + 1e-9
    ]

    output_path = Path(save_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Time_s", "Truck1_Velocity_kph", "Truck1_Event", "Truck2_Image_Event", "Truck3_Image_Event", "Notes"])
        for row in original_rows:
            writer.writerow([
                f"{row.time_s:.3f}",
                f"{row.truck1_velocity_kph:.3f}" if row.truck1_velocity_kph is not None else "",
                row.truck1_event.value if row.truck1_event is not None else "",
                row.truck2_image_event.value if row.truck2_image_event is not None else "",
                row.truck3_image_event.value if row.truck3_image_event is not None else "",
                row.notes,
            ])
        # Append live-controlled rows
        for live_row in live_rows:
            t = round(live_row.time_s, 10)
            writer.writerow([
                f"{live_row.time_s:.3f}",
                f"{live_row.truck1_velocity_kph:.3f}",
                t1_events.get(t, ""),
                t2_events.get(t, ""),
                t3_events.get(t, ""),
                "",
            ])


class OnlineVisualizationWindow:
    """Stage C visualization popup with live leader-control panel.

    Replays pre-calculated rows exactly like BulkVisualizationWindow, then
    lets the user take over the leader at any point via the control row.
    No code from open_visualization_window() or BulkVisualizationWindow is
    modified — this class is entirely standalone.
    """

    def __init__(
        self,
        parent: "ConvoySimGui",
        header: str,
        rows: tuple[SimulationRow, ...],
        parameters_path: str,
        scenario_path: str,
        braking_table_path: str,
        distances: tuple[float | None, float | None, float | None, float | None],
        truck_length_m: float,
        playback_speed: float,
        on_close: object | None = None,
    ) -> None:
        self.parent = parent
        self.rows: list[SimulationRow] = list(rows)
        self._parameters_path = parameters_path
        self._scenario_path = scenario_path
        self._braking_table_path = braking_table_path
        self.truck_length_m = truck_length_m
        self.on_close = on_close

        # Live-mode state
        self._live_mode = False
        self._live_stepper: LiveSimStepper | None = None
        self._live_entry_index = 0
        self._live_rows: list[SimulationRow] = []
        self._steps_per_second = 10  # overridden after parameters load

        self.current_frame_index = 0
        self.is_playing = False
        self.playback_after_id: str | None = None
        self._updating_time_scale = False

        self.time_var = tk.DoubleVar(value=0.0)
        self.time_label_var = tk.StringVar(value="Time: 0.0s")
        self.playback_speed_var = tk.DoubleVar(value=playback_speed)
        self.playback_speed_label_var = tk.StringVar(value=f"Speed: x{playback_speed:.1f}")
        self.show_gap_chart_var = tk.BooleanVar(value=True)
        self.show_velocity_chart_var = tk.BooleanVar(value=True)
        self._accel_rate_var = tk.StringVar(value="1.0")
        self._decel_rate_var = tk.StringVar(value="1.0")
        self._pause_btn_text = tk.StringVar(value="Pause")

        self.window = tk.Toplevel(parent)
        self.window.title("ConvoySIM Online Visualization")
        self.window.geometry("1280x900")
        self.window.minsize(1000, 760)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        # Load parameters to populate default rate fields
        try:
            loaded = load_parameters_csv(parameters_path)
            p = loaded.simulation_parameters
            self._accel_rate_var.set(f"{p.max_acceleration_mps2:.2f}")
            self._decel_rate_var.set(f"{p.orange_deceleration_mps2:.2f}")
            self._steps_per_second = max(1, round(1.0 / p.simulation_time_step_s))
        except Exception:  # noqa: BLE001
            pass

        orange_dist, red_dist, loss_dist, resume_dist = distances
        self._build_window(header, orange_dist, red_dist, loss_dist, resume_dist)
        self.set_rows(tuple(rows))

    # ------------------------------------------------------------------
    # Window construction
    # ------------------------------------------------------------------

    def _build_window(
        self,
        header: str,
        orange_dist: float | None,
        red_dist: float | None,
        loss_dist: float | None,
        resume_dist: float | None,
    ) -> None:
        tk.Label(
            self.window, text=header, anchor="w",
            font=("Arial", 11, "bold"), fg="#333",
        ).pack(fill=tk.X, padx=8, pady=(6, 0))

        # --- Playback controls row ---
        controls = ttk.Frame(self.window)
        controls.pack(fill=tk.X, padx=6, pady=4)
        self._btn(controls, ">", self.play, "play").pack(side=tk.LEFT, padx=4)
        self._btn(controls, "||", self.pause, "play").pack(side=tk.LEFT, padx=4)
        self._btn(controls, "[]", self.stop, "danger").pack(side=tk.LEFT, padx=4)
        self._btn(controls, "<<", self.step_back, "utility").pack(side=tk.LEFT, padx=4)
        self._btn(controls, ">>", self.step_forward, "utility").pack(side=tk.LEFT, padx=4)
        self._btn(controls, "Toggle Legend", self._toggle_legend, "view").pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(controls, text="Gap charts", variable=self.show_gap_chart_var, command=self._apply_chart_visibility).pack(side=tk.LEFT, padx=(12, 2))
        ttk.Checkbutton(controls, text="Velocity chart", variable=self.show_velocity_chart_var, command=self._apply_chart_visibility).pack(side=tk.LEFT, padx=2)
        ttk.Label(controls, textvariable=self.time_label_var).pack(side=tk.LEFT, padx=12)
        ttk.Label(controls, textvariable=self.playback_speed_label_var).pack(side=tk.LEFT, padx=(16, 4))
        ttk.Scale(controls, from_=0.3, to=2.0, orient=tk.HORIZONTAL, variable=self.playback_speed_var,
                  command=self._on_speed_changed, length=160).pack(side=tk.LEFT, padx=4)

        # --- Leader control row (always visible) ---
        leader_row = ttk.LabelFrame(self.window, text="Control the leader")
        leader_row.pack(fill=tk.X, padx=6, pady=(0, 2))

        self._btn(leader_row, "Pause", self._on_leader_pause, "play", text_var=self._pause_btn_text).pack(side=tk.LEFT, padx=4)
        ttk.Separator(leader_row, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self._btn(leader_row, "Accelerate", self._on_accelerate, "primary").pack(side=tk.LEFT, padx=(4, 2))
        ttk.Entry(leader_row, textvariable=self._accel_rate_var, width=6).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(leader_row, text="m/s²").pack(side=tk.LEFT)
        ttk.Separator(leader_row, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self._btn(leader_row, "Decelerate", self._on_decelerate, "edit").pack(side=tk.LEFT, padx=(4, 2))
        ttk.Entry(leader_row, textvariable=self._decel_rate_var, width=6).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(leader_row, text="m/s²").pack(side=tk.LEFT)
        ttk.Separator(leader_row, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self._btn(leader_row, "Orange Brake", self._on_orange_brake, "edit").pack(side=tk.LEFT, padx=4)
        self._btn(leader_row, "Red Brake", self._on_red_brake, "danger").pack(side=tk.LEFT, padx=4)
        self._btn(leader_row, "FORT Brake", self._on_fort_brake, "danger").pack(side=tk.LEFT, padx=4)
        ttk.Separator(leader_row, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        self._back_to_sim_btn = self._btn(leader_row, "Back to Sim", self._on_back_to_sim, "utility")
        self._back_to_sim_btn.pack(side=tk.LEFT, padx=4)
        self._back_to_sim_btn.configure(state=tk.DISABLED)
        self._save_as_btn = self._btn(leader_row, "Save As", self._on_save_as, "save")
        self._save_as_btn.pack(side=tk.LEFT, padx=4)
        self._save_as_btn.configure(state=tk.DISABLED)

        # --- PanedWindow ---
        self.pane = tk.PanedWindow(self.window, orient=tk.VERTICAL, sashwidth=8, sashrelief=tk.RAISED, showhandle=True)
        self.pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        viz_frame = ttk.Frame(self.pane)
        charts_frame = ttk.Frame(self.pane)
        self.pane.add(viz_frame, minsize=280)
        self.pane.add(charts_frame, minsize=180)

        self.visualization = ConvoyPlaybackCanvas(
            viz_frame, width=1220, height=360,
            orange_distance_m=orange_dist, red_distance_m=red_dist,
            loss_distance_m=loss_dist, resume_distance_m=resume_dist,
        )
        self.gap12_chart = ConvoyTimelineChart(
            charts_frame, title="Gap1-2 vs Time", y_label="Gap (m)",
            series=(ChartSeries("Gap1-2", truck_color_for_label(1), lambda row: row.truck2_gap_m,
                                segment_style_for_rows=lambda s, e: follower_chart_segment_style("Truck2", s, e)),),
            width=1220, height=120, y_max_cap=40.0,
        )
        self.gap23_chart = ConvoyTimelineChart(
            charts_frame, title="Gap2-3 vs Time", y_label="Gap (m)",
            series=(ChartSeries("Gap2-3", truck_color_for_label(0), lambda row: row.truck3_gap_m,
                                segment_style_for_rows=lambda s, e: follower_chart_segment_style("Truck3", s, e)),),
            width=1220, height=120, y_max_cap=40.0,
        )
        self.velocity_chart = ConvoyTimelineChart(
            charts_frame, title="Velocity vs Time", y_label="Velocity (kph)",
            series=(
                ChartSeries("Truck1", "#333333", lambda row: row.truck1_velocity_kph),
                ChartSeries("Truck2", truck_color_for_label(1), lambda row: row.truck2_velocity_kph,
                            segment_style_for_rows=lambda s, e: follower_chart_segment_style("Truck2", s, e, default_dashed_for_truck2=True)),
                ChartSeries("Truck3", truck_color_for_label(0), lambda row: row.truck3_velocity_kph,
                            segment_style_for_rows=lambda s, e: follower_chart_segment_style("Truck3", s, e)),
            ),
            width=1220, height=120,
        )
        self.time_scale = ttk.Scale(
            charts_frame, from_=0.0, to=0.0, orient=tk.HORIZONTAL,
            variable=self.time_var, command=self._on_time_scale_changed,
        )
        self.time_scale.pack(fill=tk.X, padx=(int(CHART_LEFT_PX), int(CHART_RIGHT_MARGIN_PX)), pady=(6, 8))
        self._apply_chart_visibility()

        # Legend above pane
        self._legend_frame = self._build_legend(self.window)
        self._legend_frame.pack(fill=tk.X, padx=8, pady=(0, 4), before=self.pane)

        # Keyboard shortcuts
        self.window.bind("<Left>", lambda _e: self._keyboard_back())
        self.window.bind("<Right>", lambda _e: self._keyboard_forward())
        self.window.bind("<Home>", lambda _e: self.stop())
        self.window.bind("<End>", lambda _e: self._keyboard_end())

    # ------------------------------------------------------------------
    # Playback (pre-calculated mode — identical to BulkVisualizationWindow)
    # ------------------------------------------------------------------

    def set_rows(self, rows: tuple[SimulationRow, ...]) -> None:
        self.rows = list(rows)
        max_time = rows[-1].time_s if rows else 0.0
        self.time_scale.configure(to=max_time)
        self.visualization.set_rows(rows, self.truck_length_m)
        self.gap12_chart.set_rows(rows)
        self.gap23_chart.set_rows(rows)
        self.velocity_chart.set_rows(rows)
        self.draw_frame(0)

    def play(self) -> None:
        if not self.rows:
            return
        self.is_playing = True
        self._pause_btn_text.set("Pause")
        self._schedule_next_frame()

    def pause(self) -> None:
        self.is_playing = False
        self._pause_btn_text.set("Resume")
        if self.playback_after_id is not None:
            self.window.after_cancel(self.playback_after_id)
            self.playback_after_id = None

    def stop(self) -> None:
        self.pause()
        self.draw_frame(0)

    def step_back(self) -> None:
        self.pause()
        self._keyboard_back()

    def step_forward(self) -> None:
        self.pause()
        self._keyboard_forward()

    def draw_frame(self, index: int) -> None:
        if not self.rows:
            self.current_frame_index = 0
            self.time_label_var.set("Time: 0.0s")
            self.visualization.draw_frame(0)
            self.gap12_chart.draw(0)
            self.gap23_chart.draw(0)
            self.velocity_chart.draw(0)
            return
        self.current_frame_index = max(0, min(index, len(self.rows) - 1))
        row = self.rows[self.current_frame_index]
        rows_tuple = tuple(self.rows)
        self.visualization.set_rows(rows_tuple, self.truck_length_m)
        self.visualization.draw_frame(self.current_frame_index)
        self.gap12_chart.set_rows(rows_tuple)
        self.gap12_chart.draw(self.current_frame_index)
        self.gap23_chart.set_rows(rows_tuple)
        self.gap23_chart.draw(self.current_frame_index)
        self.velocity_chart.set_rows(rows_tuple)
        self.velocity_chart.draw(self.current_frame_index)
        self.time_label_var.set(f"Time: {row.time_s:.1f}s")
        self._updating_time_scale = True
        self.time_var.set(row.time_s)
        self._updating_time_scale = False

    def _schedule_next_frame(self) -> None:
        if not self.is_playing:
            return
        if self._live_mode and self._live_stepper is not None:
            new_rows = self._live_stepper.advance_one_second(HOLD)
            if new_rows:
                self._live_rows.extend(new_rows)
                self.rows.extend(new_rows)
                self.draw_frame(len(self.rows) - 1)
                self._save_as_btn.configure(state=tk.NORMAL)
        else:
            if self.current_frame_index >= len(self.rows) - 1:
                self.pause()
                return
            self.draw_frame(self.current_frame_index + 1)
        self.playback_after_id = self.window.after(
            playback_delay_ms(self.playback_speed_var.get()), self._schedule_next_frame
        )

    def _on_time_scale_changed(self, value: str) -> None:
        if self._updating_time_scale or not self.rows:
            return
        self.pause()
        self.draw_frame(nearest_row_index(tuple(self.rows), float(value)))

    def _on_speed_changed(self, value: str) -> None:
        self.playback_speed_label_var.set(f"Speed: x{float(value):.1f}")

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _keyboard_back(self) -> None:
        self.pause()
        if self._live_mode and self._live_stepper is not None and self._live_stepper.can_undo:
            if self._live_stepper.undo_one_second():
                n = self._steps_per_second
                self._live_rows = self._live_rows[:-n]
                self.rows = self.rows[:self._live_entry_index + 1 + len(self._live_rows)]
                if not self._live_rows:
                    self._save_as_btn.configure(state=tk.DISABLED)
                    self._back_to_sim_btn.configure(state=tk.DISABLED)
                self.draw_frame(len(self.rows) - 1)
        else:
            current_time = self.rows[self.current_frame_index].time_s if self.rows else 0.0
            self.draw_frame(nearest_row_index(tuple(self.rows), current_time - 1.0))

    def _keyboard_forward(self) -> None:
        self.pause()
        if self._live_mode and self._live_stepper is not None:
            new_rows = self._live_stepper.advance_one_second(HOLD)
            if new_rows:
                self._live_rows.extend(new_rows)
                self.rows.extend(new_rows)
                self.draw_frame(len(self.rows) - 1)
                self._save_as_btn.configure(state=tk.NORMAL)
        else:
            current_time = self.rows[self.current_frame_index].time_s if self.rows else 0.0
            self.draw_frame(nearest_row_index(tuple(self.rows), current_time + 1.0))

    def _keyboard_end(self) -> None:
        self.pause()
        if self.rows:
            self.draw_frame(len(self.rows) - 1)

    # ------------------------------------------------------------------
    # Leader control
    # ------------------------------------------------------------------

    def _ensure_live_mode(self) -> bool:
        """Activate live mode from current frame.  Returns False if setup fails."""
        if self._live_mode:
            return True
        self.pause()
        try:
            loaded = load_parameters_csv(self._parameters_path)
            timeline = ScenarioTimeline.from_csv(self._scenario_path)
            braking = BrakingDistanceTable.from_csv(self._braking_table_path) if self._braking_table_path else None
            current_time = self.rows[self.current_frame_index].time_s if self.rows else 0.0
            self._live_entry_index = self.current_frame_index
            self._steps_per_second = max(1, round(1.0 / loaded.simulation_parameters.simulation_time_step_s))
            self._live_stepper = LiveSimStepper(
                loaded.initial_conditions,
                loaded.simulation_parameters,
                timeline,
                braking,
                current_time,
            )
            self._live_mode = True
            self._back_to_sim_btn.configure(state=tk.NORMAL)
            return True
        except Exception as exc:  # noqa: BLE001
            self.parent._set_status(f"Live mode setup failed: {exc}", "error")
            return False

    def _apply_leader_command(self, command: LiveLeaderCommand) -> None:
        self.pause()
        if not self._ensure_live_mode():
            return
        assert self._live_stepper is not None
        new_rows = self._live_stepper.advance_one_second(command)
        if new_rows:
            self._live_rows.extend(new_rows)
            self.rows.extend(new_rows)
            self.draw_frame(len(self.rows) - 1)
            self._save_as_btn.configure(state=tk.NORMAL)

    def _on_accelerate(self) -> None:
        try:
            rate = float(self._accel_rate_var.get())
        except ValueError:
            return
        self._apply_leader_command(accelerate(rate))

    def _on_decelerate(self) -> None:
        try:
            rate = float(self._decel_rate_var.get())
        except ValueError:
            return
        self._apply_leader_command(decelerate(rate))

    def _on_orange_brake(self) -> None:
        self._apply_leader_command(ORANGE_BRAKE)

    def _on_red_brake(self) -> None:
        self._apply_leader_command(RED_BRAKE)

    def _on_fort_brake(self) -> None:
        self._apply_leader_command(FORT_BRAKE)

    def _on_leader_pause(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def _on_back_to_sim(self) -> None:
        self.pause()
        self.rows = self.rows[:self._live_entry_index + 1]
        self._live_rows = []
        self._live_stepper = None
        self._live_mode = False
        self._save_as_btn.configure(state=tk.DISABLED)
        self._back_to_sim_btn.configure(state=tk.DISABLED)
        self.draw_frame(self._live_entry_index)

    def _on_save_as(self) -> None:
        if not self._live_rows:
            return
        initial_path = _next_version_name(self._scenario_path)
        save_path = filedialog.asksaveasfilename(
            initialfile=Path(initial_path).name,
            initialdir=str(Path(initial_path).parent),
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not save_path:
            return
        try:
            entry_time = self.rows[self._live_entry_index].time_s
            _save_online_scenario(
                self._scenario_path, entry_time, tuple(self._live_rows), save_path
            )
        except Exception as exc:  # noqa: BLE001
            self.parent._set_status(f"Save failed: {exc}", "error")
            return
        self.parent.scenario_path.set(save_path)
        self.parent._set_status(f"Saved and loaded: {Path(save_path).name}", "success")

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _apply_chart_visibility(self) -> None:
        for chart in (self.gap12_chart, self.gap23_chart, self.velocity_chart):
            chart.canvas.pack_forget()
        if self.show_gap_chart_var.get():
            self.gap12_chart.canvas.pack(fill=tk.BOTH, expand=True, before=self.time_scale)
            self.gap23_chart.canvas.pack(fill=tk.BOTH, expand=True, before=self.time_scale)
        if self.show_velocity_chart_var.get():
            self.velocity_chart.canvas.pack(fill=tk.BOTH, expand=True, before=self.time_scale)

    def _toggle_legend(self) -> None:
        if self._legend_frame.winfo_ismapped():
            self._legend_frame.pack_forget()
        else:
            self._legend_frame.pack(fill=tk.X, padx=8, pady=(0, 4), before=self.pane)

    def _build_legend(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)
        items = (
            ("Truck #1", truck_color_for_label(2), None, 4),
            ("Truck #2 / Gap1-2", truck_color_for_label(1), None, 4),
            ("Truck #3 / Gap2-3", truck_color_for_label(0), None, 4),
            ("Image lost", truck_color_for_label(1), (5, 4), 3),
            ("Orange braking", "#d77a00", None, 4),
            ("Red braking / violation", "#b00020", None, 4),
        )
        for i, (text, color, dash, width) in enumerate(items):
            item = tk.Frame(frame)
            item.grid(row=0, column=i, sticky="w", padx=8, pady=3)
            swatch = tk.Canvas(item, width=40, height=12, highlightthickness=0)
            swatch.pack(side=tk.LEFT)
            swatch.create_line(2, 6, 38, 6, fill=color, width=width, dash=dash)
            tk.Label(item, text=text).pack(side=tk.LEFT, padx=4)
        return frame

    def _btn(
        self,
        parent: tk.Widget,
        text: str,
        command: object,
        role: str,
        width: int | None = None,
        text_var: tk.StringVar | None = None,
    ) -> tk.Button:
        colors = {
            "primary": ("#1565c0", "#ffffff"),
            "view": ("#5e35b1", "#ffffff"),
            "save": ("#2e7d32", "#ffffff"),
            "edit": ("#ef6c00", "#ffffff"),
            "danger": ("#b00020", "#ffffff"),
            "play": ("#00897b", "#ffffff"),
            "utility": ("#546e7a", "#ffffff"),
        }
        bg, fg = colors.get(role, colors["utility"])
        kwargs: dict = dict(bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                             disabledforeground="#dddddd", relief=tk.RAISED, bd=2, padx=6, pady=2)
        if width is not None:
            kwargs["width"] = width
        if text_var is not None:
            return tk.Button(parent, textvariable=text_var, command=command, **kwargs)
        return tk.Button(parent, text=text, command=command, **kwargs)

    def close(self) -> None:
        self.pause()
        if callable(self.on_close):
            self.on_close(self)
        self.window.destroy()


class ConvoySimGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ConvoySIM Stage A")
        self.geometry("1200x760")
        saved_config = load_stage_a_run_config()
        self.parameters_path = tk.StringVar(value=saved_config.parameters_path)
        self.scenario_path = tk.StringVar(value=saved_config.scenario_path)
        self.loaded_scenario_label_var = tk.StringVar(value=self._loaded_scenario_label())
        self.visualization_header_var = tk.StringVar(value=self._loaded_scenario_label())
        self.braking_path = tk.StringVar(value=saved_config.braking_table_path)
        self.output_path = tk.StringVar(value=saved_config.output_path)
        self.log_path = tk.StringVar(value=saved_config.log_path)
        self.charts_path = tk.StringVar(value=saved_config.charts_path)
        self.cost_function_weights_path = tk.StringVar(value=saved_config.cost_function_weights_path)
        self.visualization_rows: tuple[SimulationRow, ...] = ()
        self.current_frame_index = 0
        self.is_playing = False
        self.playback_after_id: str | None = None
        self.visualization_window: tk.Toplevel | None = None
        self.visualization: ConvoyPlaybackCanvas | None = None
        self.gap12_chart: ConvoyTimelineChart | None = None
        self.gap23_chart: ConvoyTimelineChart | None = None
        self.velocity_chart: ConvoyTimelineChart | None = None
        self.time_scale: ttk.Scale | None = None
        self.legend_frame: ttk.Frame | None = None
        self.visualization_pane: tk.PanedWindow | None = None
        self.visualization_divider_position = saved_config.visualization_divider_position
        self.time_var = tk.DoubleVar(value=0.0)
        self.time_label_var = tk.StringVar(value="Time: 0.0s")
        self.playback_speed_var = tk.DoubleVar(value=saved_config.playback_speed)
        self.playback_speed_label_var = tk.StringVar(value=f"Speed: x{saved_config.playback_speed:.1f}")
        self.show_gap_chart_var = tk.BooleanVar(value=saved_config.show_gap_chart)
        self.show_velocity_chart_var = tk.BooleanVar(value=saved_config.show_velocity_chart)
        self.show_truck2_velocity_var = tk.BooleanVar(value=saved_config.show_truck2_velocity)
        self.show_truck3_velocity_var = tk.BooleanVar(value=saved_config.show_truck3_velocity)
        self.status_var = tk.StringVar(value="Ready.")
        bulk_parameters = bulk_parameter_names()
        bulk_cost_functions = bulk_cost_function_names()
        self.bulk_scenarios_dir = tk.StringVar(value=saved_config.bulk_scenarios_dir)
        self.bulk_parameter_var = tk.StringVar(value=bulk_parameters[0] if bulk_parameters else "")
        self.bulk_parameter_default_var = tk.StringVar(value="")
        self.bulk_min_var = tk.StringVar(value="")
        self.bulk_max_var = tk.StringVar(value="")
        self.bulk_step_var = tk.StringVar(value="")
        self.bulk_cost_function_var = tk.StringVar(value=bulk_cost_functions[0] if bulk_cost_functions else "")
        self.bulk_progress_var = tk.StringVar(value="Select scenarios, parameter range, and cost function.")
        self.bulk_progress_value = tk.DoubleVar(value=0.0)
        self.status_label: tk.Label | None = None
        self.notebook: ttk.Notebook | None = None
        self.parameters_table: ttk.Treeview | None = None
        self.scenario_table: ttk.Treeview | None = None
        self.cost_weights_table: ttk.Treeview | None = None
        self.bulk_scenario_listbox: tk.Listbox | None = None
        self.bulk_cost_function_listbox: tk.Listbox | None = None
        self.bulk_start_button: tk.Button | None = None
        self.bulk_cancel_button: tk.Button | None = None
        self.bulk_results_window: tk.Toplevel | None = None
        self.bulk_results_table: ttk.Treeview | None = None
        self.bulk_chart_canvas: tk.Canvas | None = None
        self.bulk_weighted_chart_canvas: tk.Canvas | None = None
        self.log_text: tk.Text | None = None
        self.parameters_csv_table = CsvTable((), ())
        self.bulk_result: BulkSimulationResult | None = None
        self.bulk_chart_points: list[tuple[float, float, float, str, str]] = []
        self.bulk_selected_chart_point: tuple[float, str, str] | None = None
        self.bulk_result_rows_by_item: dict[str, BulkSimulationRunRow] = {}
        self.bulk_active_table_cost_function = bulk_cost_functions[0] if bulk_cost_functions else ""
        self.bulk_visualization_windows: list[BulkVisualizationWindow] = []
        self.parameter_filter_var = tk.StringVar(value="")
        self._parameter_edit_entry: tk.Entry | None = None
        self._scenario_edit_widget: tk.Entry | ttk.Combobox | None = None
        self._bulk_thread: threading.Thread | None = None
        self._bulk_cancel_requested = False
        self.open_visualization_button: tk.Button | None = None
        self.open_charts_button: tk.Button | None = None
        self.open_online_visualization_button: tk.Button | None = None
        self.show_bulk_results_button: tk.Button | None = None
        self._online_visualization_windows: list[OnlineVisualizationWindow] = []
        self.scenario_save_button: tk.Button | None = None
        self.scenario_save_as_button: tk.Button | None = None
        self._scenario_dirty = False
        self._parameters_dirty = False
        self._tab_images: list[tk.PhotoImage] = []
        self._results_available = False
        self._loading_initial_files = True
        self._updating_time_scale = False
        self._refreshing_output_paths = False
        self.parameters_path.trace_add("write", self._on_parameters_path_changed)
        self.parameter_filter_var.trace_add("write", self._on_parameter_filter_changed)
        self.bulk_parameter_var.trace_add("write", self._on_bulk_parameter_changed)
        self.scenario_path.trace_add("write", self._on_scenario_path_changed)
        self.braking_path.trace_add("write", self._on_braking_path_changed)
        self.cost_function_weights_path.trace_add("write", self._on_cost_function_weights_path_changed)
        self.bulk_min_var.trace_add("write", self._on_bulk_input_changed)
        self.bulk_max_var.trace_add("write", self._on_bulk_input_changed)
        self.bulk_step_var.trace_add("write", self._on_bulk_input_changed)
        self._build_ui()
        self._load_previous_run_files()
        self._load_parameters_tab()
        self._load_cost_weights_tab()
        self._update_bulk_parameter_default()
        self._load_scenario_tab()
        self._loading_initial_files = False
        self._update_result_buttons()

    def _build_ui(self) -> None:
        title = tk.Label(self, text="ConvoySIM", font=("Arial", 18, "bold"), anchor="w")
        title.pack(fill=tk.X, padx=10, pady=(8, 2))
        subtitle = tk.Label(self, text="Three-truck convoy simulation and review", font=("Arial", 10), anchor="w", fg="#555")
        subtitle.pack(fill=tk.X, padx=10, pady=(0, 6))

        paths = ttk.LabelFrame(self, text="Input and Output Files")
        paths.pack(fill=tk.X, padx=8, pady=8)

        # Scenario field spans full width
        scenario_frame = ttk.Frame(paths)
        scenario_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=4)
        paths.columnconfigure(0, weight=1)
        paths.columnconfigure(1, weight=1)
        self._path_row(scenario_frame, "Scenario", self.scenario_path, 0, width=120)

        # Input files (left column)
        left_paths = ttk.Frame(paths)
        left_paths.grid(row=1, column=0, sticky="ew", padx=(4, 8), pady=4)
        self._path_row(left_paths, "Parameters", self.parameters_path, 0, width=58)
        self._path_row(left_paths, "Braking table", self.braking_path, 1, width=58)
        self._path_row(left_paths, "Cost weights", self.cost_function_weights_path, 2, width=58)

        # Output files (right column, shifted down)
        right_paths = ttk.Frame(paths)
        right_paths.grid(row=1, column=1, sticky="ew", padx=(8, 4), pady=4)
        self._path_row(right_paths, "Output CSV", self.output_path, 0, save=True, width=58)
        self._path_row(right_paths, "Log CSV", self.log_path, 1, save=True, width=58)
        self._path_row(right_paths, "Charts HTML", self.charts_path, 2, save=True, width=58)

        controls = ttk.Frame(self)
        controls.pack(fill=tk.X, padx=8, pady=4)
        self._colored_button(controls, "Start Simulation", self.run_simulation, "primary").pack(side=tk.LEFT, padx=4)
        self._colored_button(controls, "Bulk simulations", self.open_bulk_simulations_tab, "edit").pack(side=tk.LEFT, padx=4)
        self.open_visualization_button = self._colored_button(
            controls,
            "Open Visualization",
            self.open_visualization_window,
            "view",
        )
        self.open_visualization_button.pack(side=tk.LEFT, padx=4)
        self.open_charts_button = self._colored_button(controls, "Open Charts", self.open_charts, "view")
        self.open_charts_button.pack(side=tk.LEFT, padx=4)
        self.open_online_visualization_button = self._colored_button(
            controls, "Open Online Visualization", self.open_online_visualization_window, "view"
        )
        self.open_online_visualization_button.pack(side=tk.LEFT, padx=4)
        self.show_bulk_results_button = self._colored_button(controls, "Show Bulk Results", self.show_bulk_results_window, "view")
        self.show_bulk_results_button.pack(side=tk.LEFT, padx=4)
        self.status_label = tk.Label(controls, textvariable=self.status_var, anchor="w", fg="#555")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(16, 4))
        tk.Label(self, textvariable=self.loaded_scenario_label_var, anchor="w", font=("Arial", 10, "bold"), fg="#333").pack(
            fill=tk.X,
            padx=10,
            pady=(0, 4),
        )

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.notebook = notebook
        parameters_frame = ttk.Frame(notebook)
        scenario_frame = ttk.Frame(notebook)
        bulk_frame = ttk.Frame(notebook)
        cost_weights_frame = ttk.Frame(notebook)
        table_frame = ttk.Frame(notebook)
        log_frame = ttk.Frame(notebook)
        self._configure_tab_selector_style(notebook)
        self._add_colored_tab(notebook, scenario_frame, "Scenario", "#f4b400")
        self._add_colored_tab(notebook, parameters_frame, "Parameters", "#66bb6a")
        self._add_colored_tab(notebook, bulk_frame, "Bulk Simulation", "#00acc1")
        self._add_colored_tab(notebook, cost_weights_frame, "Cost Weight", "#8d6e63")
        self._add_colored_tab(notebook, table_frame, "Output Table", "#4285f4")
        self._add_colored_tab(notebook, log_frame, "Log", "#9c6ade")

        self._add_tab_header(parameters_frame, "Editable parameter CSV", "#d9f2e6")
        params_controls = ttk.Frame(parameters_frame)
        params_controls.pack(fill=tk.X, padx=6, pady=(0, 4))
        self._colored_button(params_controls, "Save", self.save_parameters_tab, "save").pack(side=tk.LEFT, padx=4)
        self._colored_button(params_controls, "Save As", self.save_parameters_tab_as, "save").pack(side=tk.LEFT, padx=4)
        ttk.Label(params_controls, text="Filter").pack(side=tk.LEFT, padx=(16, 4))
        ttk.Entry(params_controls, textvariable=self.parameter_filter_var, width=28).pack(side=tk.LEFT, padx=4)
        self._colored_button(params_controls, "Clear Filter", self.clear_parameter_filter, "utility").pack(side=tk.LEFT, padx=4)
        self.parameters_table = self._build_table(parameters_frame)
        self.parameters_table.bind("<Double-1>", self._begin_parameter_cell_edit)

        self._add_tab_header(scenario_frame, "Editable scenario timeline CSV", "#fff4d6")
        scenario_controls = ttk.Frame(scenario_frame)
        scenario_controls.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.scenario_save_button = self._colored_button(scenario_controls, "Save", self.save_scenario_tab, "save")
        self.scenario_save_button.pack(side=tk.LEFT, padx=4)
        self.scenario_save_as_button = self._colored_button(scenario_controls, "Save As", self.save_scenario_tab_as, "save")
        self.scenario_save_as_button.pack(side=tk.LEFT, padx=4)
        self._colored_button(scenario_controls, "Insert Row", self.insert_scenario_row, "edit").pack(side=tk.LEFT, padx=4)
        self._colored_button(scenario_controls, "Delete Row", self.delete_scenario_rows, "danger").pack(side=tk.LEFT, padx=4)
        self.scenario_table = self._build_table(scenario_frame)
        self.scenario_table.bind("<Double-1>", self._begin_scenario_cell_edit)

        self._build_bulk_tab(bulk_frame)

        self._add_tab_header(cost_weights_frame, "Editable cost function weights CSV", "#efe2d3")
        cost_weight_controls = ttk.Frame(cost_weights_frame)
        cost_weight_controls.pack(fill=tk.X, padx=6, pady=(0, 4))
        self._colored_button(cost_weight_controls, "Save", self.save_cost_weights_tab, "save").pack(side=tk.LEFT, padx=4)
        self._colored_button(cost_weight_controls, "Save As", self.save_cost_weights_tab_as, "save").pack(side=tk.LEFT, padx=4)
        self.cost_weights_table = self._build_table(cost_weights_frame)
        self.cost_weights_table.bind("<Double-1>", self._begin_parameter_cell_edit)

        self._add_tab_header(table_frame, "Simulation output rows", "#ddeaff")
        self.table = self._build_table(table_frame)

        self._add_tab_header(log_frame, "Sorted event log", "#f0e6ff")
        self.log_text = tk.Text(log_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self._configure_log_tags()

    def _path_row(
        self,
        parent: tk.Widget,
        label: str,
        variable: tk.StringVar,
        row: int,
        save: bool = False,
        width: int = 120,
    ) -> None:
        command = lambda: self._browse(variable, save)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=0, padx=4, pady=2)
        ttk.Label(parent, text=label).grid(row=row, column=1, sticky="w", padx=4, pady=2)
        ttk.Entry(parent, textvariable=variable, width=width).grid(row=row, column=2, sticky="ew", padx=4, pady=2)
        parent.columnconfigure(2, weight=1)

    def _loaded_scenario_label(self) -> str:
        path = self.scenario_path.get().strip() if hasattr(self, "scenario_path") else ""
        display = Path(path).stem if path else "None"
        return f"Loaded scenario: {display}"

    def _refresh_loaded_scenario_label(self) -> None:
        if hasattr(self, "loaded_scenario_label_var"):
            self.loaded_scenario_label_var.set(self._loaded_scenario_label())
        if hasattr(self, "visualization_header_var"):
            self.visualization_header_var.set(self._loaded_scenario_label())

    def _colored_button(
        self,
        parent: tk.Widget,
        text: str,
        command: object,
        role: str = "utility",
        width: int | None = None,
    ) -> tk.Button:
        colors = {
            "primary": ("#1565c0", "#ffffff"),
            "view": ("#5e35b1", "#ffffff"),
            "save": ("#2e7d32", "#ffffff"),
            "edit": ("#ef6c00", "#ffffff"),
            "danger": ("#b00020", "#ffffff"),
            "play": ("#00897b", "#ffffff"),
            "utility": ("#546e7a", "#ffffff"),
        }
        background, foreground = colors.get(role, colors["utility"])
        options = {}
        if width is not None:
            options["width"] = width
        return tk.Button(
            parent,
            text=text,
            command=command,  # type: ignore[arg-type]
            bg=background,
            fg=foreground,
            activebackground=background,
            activeforeground=foreground,
            disabledforeground="#dddddd",
            relief=tk.RAISED,
            bd=2,
            padx=6,
            pady=2,
            **options,
        )

    def _set_status(self, message: str, level: str = "info") -> None:
        self.status_var.set(message)
        if self.status_label is None:
            return
        color_by_level = {
            "info": "#555555",
            "success": "#237a23",
            "warning": "#b26a00",
            "error": "#b00020",
        }
        self.status_label.configure(fg=color_by_level.get(level, "#555555"))

    def _configure_tab_selector_style(self, notebook: ttk.Notebook) -> None:
        style = ttk.Style(notebook)
        style.configure("ConvoySIM.TNotebook.Tab", padding=(10, 4), font=("Arial", 9, "bold"))
        notebook.configure(style="ConvoySIM.TNotebook")

    def _add_colored_tab(self, notebook: ttk.Notebook, frame: ttk.Frame, text: str, color: str) -> None:
        image = tk.PhotoImage(width=14, height=14)
        image.put(color, to=(0, 0, 14, 14))
        self._tab_images.append(image)
        notebook.add(frame, text=f" {text}", image=image, compound=tk.LEFT)

    def _add_tab_header(self, parent: ttk.Frame, text: str, color: str) -> None:
        header = tk.Frame(parent, background=color)
        header.pack(fill=tk.X, padx=0, pady=(0, 4))
        tk.Label(header, text=text, background=color, anchor="w", font=("Arial", 10, "bold")).pack(fill=tk.X, padx=8, pady=4)

    def _build_table(self, parent: ttk.Frame) -> ttk.Treeview:
        holder = ttk.Frame(parent)
        holder.pack(fill=tk.BOTH, expand=True)
        table = ttk.Treeview(holder, show="headings")
        y_scroll = ttk.Scrollbar(holder, orient=tk.VERTICAL, command=table.yview)
        x_scroll = ttk.Scrollbar(holder, orient=tk.HORIZONTAL, command=table.xview)
        table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        table.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        return table

    def _build_bulk_tab(self, parent: ttk.Frame) -> None:
        self._add_tab_header(parent, "Bulk simulation optimizer", "#d7f5f8")
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=(0, 4))
        ttk.Label(top, text="Scenarios folder").grid(row=0, column=0, sticky="w", padx=4, pady=2)
        ttk.Entry(top, textvariable=self.bulk_scenarios_dir, width=42).grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        ttk.Button(top, text="Browse", command=self._browse_bulk_scenarios_dir).grid(row=0, column=2, padx=4, pady=2)
        self._colored_button(top, "Refresh", self._load_bulk_scenarios, "utility").grid(row=0, column=3, padx=4, pady=2)

        ttk.Label(top, text="Parameter").grid(row=1, column=0, sticky="w", padx=4, pady=2)
        ttk.Combobox(top, textvariable=self.bulk_parameter_var, values=bulk_parameter_names(), state="readonly", width=32).grid(
            row=1,
            column=1,
            sticky="w",
            padx=4,
            pady=2,
        )
        ttk.Label(top, text="Default").grid(row=1, column=2, sticky="e", padx=(8, 2), pady=2)
        ttk.Entry(top, textvariable=self.bulk_parameter_default_var, width=10, state="readonly").grid(
            row=1,
            column=3,
            sticky="w",
            padx=(2, 4),
            pady=2,
        )
        ttk.Label(top, text="Min").grid(row=1, column=4, sticky="e", padx=(8, 2), pady=2)
        ttk.Entry(top, textvariable=self.bulk_min_var, width=10).grid(row=1, column=5, sticky="w", padx=(2, 4), pady=2)
        ttk.Label(top, text="Max").grid(row=1, column=6, sticky="e", padx=(8, 2), pady=2)
        ttk.Entry(top, textvariable=self.bulk_max_var, width=10).grid(row=1, column=7, sticky="w", padx=(2, 4), pady=2)
        ttk.Label(top, text="Step").grid(row=1, column=8, sticky="e", padx=(8, 2), pady=2)
        ttk.Entry(top, textvariable=self.bulk_step_var, width=10).grid(row=1, column=9, sticky="w", padx=(2, 4), pady=2)
        ttk.Progressbar(top, variable=self.bulk_progress_value, maximum=100.0, length=220).grid(
            row=1,
            column=10,
            sticky="ew",
            padx=(12, 4),
            pady=2,
        )

        ttk.Label(top, textvariable=self.bulk_progress_var, foreground="#555").grid(
            row=2,
            column=0,
            columnspan=11,
            sticky="w",
            padx=4,
            pady=2,
        )

        bulk_buttons = ttk.Frame(top)
        bulk_buttons.grid(row=3, column=0, columnspan=11, pady=(6, 2))
        self.bulk_start_button = self._colored_button(bulk_buttons, "Start bulk simulation", self.start_bulk_simulation, "primary")
        self.bulk_start_button.pack(side=tk.LEFT, padx=6)
        self.bulk_cancel_button = self._colored_button(bulk_buttons, "Cancel", self.cancel_bulk_simulation, "danger")
        self.bulk_cancel_button.pack(side=tk.LEFT, padx=6)
        self.bulk_cancel_button.configure(state=tk.DISABLED)
        top.columnconfigure(1, weight=1)
        top.columnconfigure(10, weight=1)

        body = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        scenario_frame = ttk.LabelFrame(body, text="Bulk_Scenarios CSV files")
        cost_frame = ttk.LabelFrame(body, text="Cost functions")
        body.add(scenario_frame, weight=1)
        body.add(cost_frame, weight=1)

        scenario_buttons = ttk.Frame(scenario_frame)
        scenario_buttons.pack(fill=tk.X, padx=4, pady=(4, 0))
        self._colored_button(scenario_buttons, "Select all", self.select_all_bulk_scenarios, "utility").pack(
            side=tk.LEFT,
            padx=2,
        )
        self._colored_button(scenario_buttons, "Unselect all", self.unselect_all_bulk_scenarios, "utility").pack(
            side=tk.LEFT,
            padx=2,
        )
        self.bulk_scenario_listbox = tk.Listbox(scenario_frame, selectmode=tk.MULTIPLE, exportselection=False)
        self.bulk_scenario_listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.bulk_scenario_listbox.bind("<<ListboxSelect>>", self._on_bulk_input_changed)

        cost_buttons = ttk.Frame(cost_frame)
        cost_buttons.pack(fill=tk.X, padx=4, pady=(4, 0))
        self._colored_button(cost_buttons, "Select all", self.select_all_bulk_cost_functions, "utility").pack(side=tk.LEFT, padx=2)
        self._colored_button(cost_buttons, "Unselect all", self.unselect_all_bulk_cost_functions, "utility").pack(side=tk.LEFT, padx=2)
        self.bulk_cost_function_listbox = tk.Listbox(cost_frame, selectmode=tk.MULTIPLE, exportselection=False)
        self.bulk_cost_function_listbox.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        for cost_function in bulk_cost_function_names():
            self.bulk_cost_function_listbox.insert(tk.END, cost_function)
        self.bulk_cost_function_listbox.selection_set(0, tk.END)
        self.bulk_cost_function_listbox.bind("<<ListboxSelect>>", self._on_bulk_input_changed)
        self._load_bulk_scenarios()
        self._update_bulk_start_button()

    def _browse_bulk_scenarios_dir(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.bulk_scenarios_dir.set(path)
            self._load_bulk_scenarios()
            self._save_run_config()

    def _load_bulk_scenarios(self) -> None:
        if self.bulk_scenario_listbox is None:
            return
        self.bulk_scenario_listbox.delete(0, tk.END)
        directory = Path(self.bulk_scenarios_dir.get().strip() or "Bulk_Scenarios")
        if directory.exists():
            for path in sorted(directory.glob("*.csv")):
                self.bulk_scenario_listbox.insert(tk.END, path.name)
        self._update_bulk_start_button()
        if not self._loading_initial_files:
            self._save_run_config()

    def select_all_bulk_scenarios(self) -> None:
        if self.bulk_scenario_listbox is None:
            return
        self.bulk_scenario_listbox.selection_set(0, tk.END)
        self._update_bulk_start_button()

    def unselect_all_bulk_scenarios(self) -> None:
        if self.bulk_scenario_listbox is None:
            return
        self.bulk_scenario_listbox.selection_clear(0, tk.END)
        self._update_bulk_start_button()

    def select_all_bulk_cost_functions(self) -> None:
        if self.bulk_cost_function_listbox is None:
            return
        self.bulk_cost_function_listbox.selection_set(0, tk.END)
        self._update_bulk_start_button()

    def unselect_all_bulk_cost_functions(self) -> None:
        if self.bulk_cost_function_listbox is None:
            return
        self.bulk_cost_function_listbox.selection_clear(0, tk.END)
        self._update_bulk_start_button()

    def _on_bulk_input_changed(self, *_args: object) -> None:
        self._update_bulk_start_button()

    def _selected_bulk_scenario_paths(self) -> tuple[Path, ...]:
        if self.bulk_scenario_listbox is None:
            return ()
        directory = Path(self.bulk_scenarios_dir.get().strip() or "Bulk_Scenarios")
        return tuple(directory / self.bulk_scenario_listbox.get(index) for index in self.bulk_scenario_listbox.curselection())

    def _selected_bulk_cost_functions(self) -> tuple[str, ...]:
        if self.bulk_cost_function_listbox is None:
            return ()
        return tuple(self.bulk_cost_function_listbox.get(index) for index in self.bulk_cost_function_listbox.curselection())

    def _update_bulk_start_button(self) -> None:
        if self.bulk_start_button is None:
            return
        enabled = (
            bool(self._selected_bulk_scenario_paths())
            and bool(self._selected_bulk_cost_functions())
            and self._bulk_range_is_valid()
            and self._bulk_thread is None
        )
        self.bulk_start_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)

    def _bulk_range_is_valid(self) -> bool:
        try:
            minimum = float(self.bulk_min_var.get())
            maximum = float(self.bulk_max_var.get())
            step = float(self.bulk_step_var.get())
            return bool(generate_parameter_values(minimum, maximum, step))
        except ValueError:
            return False

    def _browse(self, variable: tk.StringVar, save: bool) -> None:
        current_path = variable.get().strip()
        initial_dir = str(Path(current_path).parent) if current_path and Path(current_path).parent.exists() else None
        path = filedialog.asksaveasfilename(initialdir=initial_dir) if save else filedialog.askopenfilename(initialdir=initial_dir)
        if path:
            variable.set(path)

    def _on_parameters_path_changed(self, *_args: object) -> None:
        self._load_parameters_tab()
        self._update_bulk_parameter_default()
        self._clear_results_after_input_change()

    def _on_parameter_filter_changed(self, *_args: object) -> None:
        if self.parameters_table is None:
            return
        self._capture_parameters_table_edits()
        self._populate_parameters_table()

    def _on_bulk_parameter_changed(self, *_args: object) -> None:
        self._update_bulk_parameter_default()
        self._update_bulk_start_button()

    def clear_parameter_filter(self) -> None:
        self.parameter_filter_var.set("")

    def _update_bulk_parameter_default(self) -> None:
        parameter_name = self.bulk_parameter_var.get().strip()
        if not parameter_name:
            self.bulk_parameter_default_var.set("")
            return
        for row in self.parameters_csv_table.rows:
            if len(row) >= 2 and row[0] == parameter_name:
                self.bulk_parameter_default_var.set(row[1])
                return
        self.bulk_parameter_default_var.set("")

    def _on_scenario_path_changed(self, *_args: object) -> None:
        if self._refreshing_output_paths:
            return
        self._refresh_loaded_scenario_label()
        self._refresh_output_paths_from_scenario()
        self._load_scenario_tab()
        self._clear_results_after_input_change()

    def _on_braking_path_changed(self, *_args: object) -> None:
        self._clear_results_after_input_change()

    def _on_cost_function_weights_path_changed(self, *_args: object) -> None:
        self._load_cost_weights_tab()
        if not self._loading_initial_files:
            self._save_run_config()

    def _clear_results_after_input_change(self) -> None:
        if self._loading_initial_files:
            return
        self.pause_visualization()
        self.visualization_rows = ()
        self._results_available = False
        self.current_frame_index = 0
        self.time_var.set(0.0)
        self.time_label_var.set("Time: 0.0s")
        if hasattr(self, "table"):
            self.table.delete(*self.table.get_children())
            self.table["columns"] = ()
        if self.log_text is not None:
            self.log_text.delete("1.0", tk.END)
        if self.visualization is not None:
            self.visualization.set_rows((), self._truck_length_m())
        if self.gap12_chart is not None:
            self.gap12_chart.set_rows(())
        if self.gap23_chart is not None:
            self.gap23_chart.set_rows(())
        if self.velocity_chart is not None:
            self.velocity_chart.set_rows(())
        self._update_result_buttons()

    def _update_scenario_save_buttons(self) -> None:
        state = tk.NORMAL if self._scenario_dirty else tk.DISABLED
        if self.scenario_save_button is not None:
            self.scenario_save_button.configure(state=state)
        if self.scenario_save_as_button is not None:
            self.scenario_save_as_button.configure(state=state)

    def _update_result_buttons(self) -> None:
        has_output_rows = self._results_available and (
            bool(self.visualization_rows) or (bool(self.output_path.get()) and Path(self.output_path.get()).exists())
        )
        has_charts = bool(self.charts_path.get()) and Path(self.charts_path.get()).exists() and has_output_rows
        if self.open_visualization_button is not None:
            self.open_visualization_button.configure(state=tk.NORMAL if has_output_rows else tk.DISABLED)
        if self.open_charts_button is not None:
            self.open_charts_button.configure(state=tk.NORMAL if has_charts else tk.DISABLED)
        if self.open_online_visualization_button is not None:
            self.open_online_visualization_button.configure(state=tk.NORMAL if has_output_rows else tk.DISABLED)
        if self.show_bulk_results_button is not None:
            self.show_bulk_results_button.configure(state=tk.NORMAL if self.bulk_result is not None else tk.DISABLED)

    def _refresh_output_paths_from_scenario(self) -> None:
        self._refreshing_output_paths = True
        try:
            run_paths = timestamped_stage_a_paths(
                self.scenario_path.get(),
                output_dir_from_previous_path(self.output_path.get()),
            )
            self.output_path.set(str(run_paths.output_path))
            self.log_path.set(str(run_paths.log_path))
            self.charts_path.set(str(run_paths.charts_path))
        finally:
            self._refreshing_output_paths = False

    def run_simulation(self) -> None:
        if self._parameters_dirty:
            self._set_status(
                "Parameters have unsaved changes — save the Parameters tab first, then run.",
                "warning",
            )
            return
        try:
            self._refresh_output_paths_from_scenario()
            result = run_basic_simulation_from_files(
                self.parameters_path.get(),
                self.scenario_path.get(),
                self.output_path.get(),
                self.braking_path.get(),
                self.log_path.get(),
            )
            parameters = load_parameters_csv(self.parameters_path.get()).simulation_parameters
            write_stage_a_charts_html(result, parameters, self.charts_path.get())
            self._load_output_table(Path(self.output_path.get()))
            self._load_log(result)
            self._set_visualization_rows(result.rows)
            self._results_available = True
            self._update_result_buttons()
            self._save_run_config()
            self._set_status(f"Simulation completed with {len(result.rows)} output rows.", "success")
        except Exception as error:  # noqa: BLE001 - GUI should surface any validation/runtime error.
            self._set_status(f"Error: {error}", "error")

    def open_online_visualization_window(self) -> None:
        if not self.visualization_rows:
            self._set_status("Run a simulation first.", "warning")
            return
        window = OnlineVisualizationWindow(
            parent=self,
            header=self._loaded_scenario_label(),
            rows=self.visualization_rows,
            parameters_path=self.parameters_path.get(),
            scenario_path=self.scenario_path.get(),
            braking_table_path=self.braking_path.get(),
            distances=self._visualization_distances(),
            truck_length_m=self._truck_length_m(),
            playback_speed=self.playback_speed_var.get(),
            on_close=self._forget_online_visualization_window,
        )
        self._online_visualization_windows.append(window)

    def _forget_online_visualization_window(self, window: OnlineVisualizationWindow) -> None:
        if window in self._online_visualization_windows:
            self._online_visualization_windows.remove(window)

    def open_bulk_simulations_tab(self) -> None:
        if self.notebook is None:
            return
        for index in range(self.notebook.index("end")):
            if "Bulk Simulation" in self.notebook.tab(index, "text"):
                self.notebook.select(index)
                break
        self._load_bulk_scenarios()

    def start_bulk_simulation(self) -> None:
        if self._bulk_thread is not None:
            return
        try:
            minimum = float(self.bulk_min_var.get())
            maximum = float(self.bulk_max_var.get())
            step = float(self.bulk_step_var.get())
            generate_parameter_values(minimum, maximum, step)
        except ValueError as error:
            self.bulk_progress_var.set(f"Invalid range: {error}")
            self._set_status(f"Bulk simulation range error: {error}", "error")
            return
        scenario_paths = self._selected_bulk_scenario_paths()
        if not scenario_paths:
            self.bulk_progress_var.set("Select at least one scenario.")
            return
        cost_functions = self._selected_bulk_cost_functions()
        if not cost_functions:
            self.bulk_progress_var.set("Select at least one cost function.")
            return
        try:
            load_cost_function_weights_csv(self.cost_function_weights_path.get())
        except Exception as error:  # noqa: BLE001 - GUI should surface weight-file problems.
            self.bulk_progress_var.set(f"Invalid cost weights file: {error}")
            self._set_status(f"Invalid cost weights file: {error}", "error")
            return

        self._bulk_cancel_requested = False
        self.bulk_progress_value.set(0.0)
        if self.bulk_start_button is not None:
            self.bulk_start_button.configure(state=tk.DISABLED)
        if self.bulk_cancel_button is not None:
            self.bulk_cancel_button.configure(state=tk.NORMAL)
        self.bulk_progress_var.set("Bulk simulation started.")
        self._set_status("Bulk simulation running...", "info")
        self._clear_bulk_results()

        def worker() -> None:
            try:
                result = run_bulk_simulations_from_files(
                    self.parameters_path.get(),
                    scenario_paths,
                    self.bulk_parameter_var.get(),
                    minimum,
                    maximum,
                    step,
                    cost_functions,
                    self.braking_path.get(),
                    self.cost_function_weights_path.get(),
                    progress_callback=self._bulk_progress_from_worker,
                    should_cancel=lambda: self._bulk_cancel_requested,
                )
                self.after(0, lambda: self._finish_bulk_simulation(result, None))
            except Exception as error:  # noqa: BLE001 - GUI should surface any validation/runtime error.
                self.after(0, lambda captured_error=error: self._finish_bulk_simulation(None, captured_error))

        self._bulk_thread = threading.Thread(target=worker, daemon=True)
        self._bulk_thread.start()

    def cancel_bulk_simulation(self) -> None:
        self._bulk_cancel_requested = True
        self.bulk_progress_var.set("Cancel requested. Waiting for current run to finish...")

    def _bulk_progress_from_worker(
        self,
        completed_runs: int,
        total_runs: int,
        scenario_name: str,
        parameter_value: float,
    ) -> None:
        self.after(
            0,
            lambda: (
                self.bulk_progress_var.set(f"{completed_runs}/{total_runs}: {scenario_name}, value {parameter_value:.3g}"),
                self.bulk_progress_value.set((completed_runs / max(1, total_runs)) * 100.0),
            ),
        )

    def _finish_bulk_simulation(self, result: BulkSimulationResult | None, error: Exception | None) -> None:
        self._bulk_thread = None
        if self.bulk_cancel_button is not None:
            self.bulk_cancel_button.configure(state=tk.DISABLED)
        self._update_bulk_start_button()
        if error is not None:
            self.bulk_progress_var.set(f"Bulk simulation failed: {error}")
            self._set_status(f"Bulk simulation failed: {error}", "error")
            return
        if result is None:
            return
        self.bulk_result = result
        self.bulk_progress_value.set(100.0 if result.rows else 0.0)
        self.open_bulk_results_window(result)
        self._update_result_buttons()
        status = "cancelled" if result.cancelled else "completed"
        self.bulk_progress_var.set(f"Bulk simulation {status}. Results: {result.results_csv_path}")
        self._set_status(f"Bulk simulation {status} with {len(result.rows)} runs.", "success" if not result.cancelled else "warning")

    def _clear_bulk_results(self) -> None:
        self.bulk_result = None
        self.bulk_chart_points = []
        self.bulk_selected_chart_point = None
        if self.bulk_chart_canvas is not None:
            self.bulk_chart_canvas.delete("all")
        if self.bulk_weighted_chart_canvas is not None:
            self.bulk_weighted_chart_canvas.delete("all")
        if self.bulk_results_table is not None:
            self.bulk_results_table.delete(*self.bulk_results_table.get_children())
            self.bulk_results_table["columns"] = ()
        if self.bulk_results_window is not None and self.bulk_results_window.winfo_exists():
            self.bulk_results_window.destroy()
        self.bulk_results_window = None
        self._update_result_buttons()

    def open_bulk_results_window(self, result: BulkSimulationResult) -> None:
        if self.bulk_results_window is not None and self.bulk_results_window.winfo_exists():
            self.bulk_results_window.destroy()
        self.bulk_results_window = tk.Toplevel(self)
        self.bulk_results_window.title("Bulk Simulation Results")
        self.bulk_results_window.geometry("1200x720")
        self.bulk_results_window.minsize(900, 560)
        self.bulk_results_window.protocol("WM_DELETE_WINDOW", self._close_bulk_results_window)
        self.bulk_active_table_cost_function = _TOTAL_WEIGHTED_COST_LABEL
        self.bulk_selected_chart_point = None
        tk.Label(
            self.bulk_results_window,
            text=f"Bulk results: {', '.join(result.cost_functions)}",
            anchor="w",
            font=("Arial", 11, "bold"),
            fg="#333",
        ).pack(fill=tk.X, padx=8, pady=(6, 4))

        chart_actions = ttk.Frame(self.bulk_results_window)
        chart_actions.pack(fill=tk.X, padx=8, pady=(0, 4))
        self._colored_button(chart_actions, "Save cost chart JPG", self.save_bulk_cost_chart, "save").pack(side=tk.LEFT, padx=(0, 6))
        self._colored_button(chart_actions, "Save weighted chart JPG", self.save_bulk_weighted_chart, "save").pack(side=tk.LEFT, padx=6)

        self.bulk_chart_canvas = tk.Canvas(self.bulk_results_window, height=270, background="#ffffff")
        self.bulk_chart_canvas.pack(fill=tk.X, padx=8, pady=(0, 12))
        self.bulk_chart_canvas.bind("<Button-1>", self._on_bulk_chart_click)
        self.bulk_chart_canvas.bind("<Configure>", self._on_bulk_chart_resize)
        self.bulk_weighted_chart_canvas = tk.Canvas(self.bulk_results_window, height=200, background="#ffffff")
        self.bulk_weighted_chart_canvas.pack(fill=tk.X, padx=8, pady=(0, 12))
        self.bulk_weighted_chart_canvas.bind("<Button-1>", self._on_bulk_chart_click)
        self.bulk_weighted_chart_canvas.bind("<Configure>", self._on_bulk_chart_resize)
        table_frame = ttk.Frame(self.bulk_results_window)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.bulk_results_table = self._build_table(table_frame)
        self.bulk_results_table.bind("<Configure>", self._on_bulk_results_table_resize)
        self.bulk_results_table.bind("<Double-1>", self.open_bulk_run_visualization)
        self._populate_bulk_results_table(result.rows)
        self._draw_bulk_chart(result)
        self._draw_bulk_weighted_chart(result)

    def _close_bulk_results_window(self) -> None:
        if self.bulk_results_window is not None:
            self.bulk_results_window.destroy()
        self.bulk_results_window = None
        self.bulk_results_table = None
        self.bulk_chart_canvas = None
        self.bulk_weighted_chart_canvas = None

    def show_bulk_results_window(self) -> None:
        if self.bulk_result is None:
            self._set_status("No bulk results available to show.", "warning")
            return
        self.open_bulk_results_window(self.bulk_result)

    def save_bulk_cost_chart(self) -> None:
        if self.bulk_chart_canvas is None:
            return
        self._save_bulk_chart_canvas(self.bulk_chart_canvas, _BULK_COST_CHART_JPG)

    def save_bulk_weighted_chart(self) -> None:
        if self.bulk_weighted_chart_canvas is None:
            return
        self._save_bulk_chart_canvas(self.bulk_weighted_chart_canvas, _BULK_WEIGHTED_CHART_JPG)

    def _save_bulk_chart_canvas(self, canvas: tk.Canvas, filename: str) -> None:
        if self.bulk_result is None:
            self._set_status("No bulk results output folder is available.", "warning")
            return
        try:
            from PIL import ImageGrab

            canvas.update_idletasks()
            left = canvas.winfo_rootx()
            top = canvas.winfo_rooty()
            right = left + canvas.winfo_width()
            bottom = top + canvas.winfo_height()
            image = ImageGrab.grab(bbox=(left, top, right, bottom)).convert("RGB")
            output_path = self.bulk_result.output_dir / filename
            image.save(output_path, "JPEG", quality=95)
        except Exception as error:  # noqa: BLE001 - GUI should surface save failures.
            self._set_status(f"Error saving chart JPG: {error}", "error")
            return
        self._set_status(f"Saved chart: {output_path}", "success")

    def _on_bulk_chart_resize(self, _event: tk.Event) -> None:
        if self.bulk_result is None:
            return
        self._draw_bulk_chart(self.bulk_result)
        self._draw_bulk_weighted_chart(self.bulk_result)

    def _populate_bulk_results_table(self, rows: tuple[object, ...]) -> None:
        if self.bulk_results_table is None:
            return
        columns = (
            "Parameter_Value",
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
        self.bulk_results_table.delete(*self.bulk_results_table.get_children())
        self.bulk_result_rows_by_item = {}
        self.bulk_results_table["columns"] = columns
        self.bulk_results_table.tag_configure("cost_triggered", foreground="#b00020")
        self.bulk_results_table.tag_configure("normal_cost", foreground="#000000")
        for column in columns:
            self.bulk_results_table.heading(column, text=_wrapped_bulk_heading(column))
            self.bulk_results_table.column(column, width=preferred_column_width(column, (), min_width=70), stretch=True)
        for row in rows:
            tags = ("cost_triggered",) if self._bulk_row_selected_cost_value(row, self.bulk_active_table_cost_function) > 0 else ("normal_cost",)
            item_id = self.bulk_results_table.insert(
                "",
                tk.END,
                values=(
                    f"{row.parameter_value:.10g}",
                    row.scenario_name,
                    row.status,
                    f"{row.total_weighted_cost:.10g}",
                    row.truck2_red_braking_count,
                    row.truck3_red_braking_count,
                    row.total_red_braking_count,
                    row.truck2_accident_count,
                    row.truck3_accident_count,
                    row.total_accident_count,
                    row.run_output_csv,
                    row.failure_reason,
                ),
                tags=tags,
            )
            if isinstance(row, BulkSimulationRunRow):
                self.bulk_result_rows_by_item[item_id] = row
        self._resize_bulk_results_columns()

    def _on_bulk_results_table_resize(self, _event: tk.Event) -> None:
        self._resize_bulk_results_columns()

    def _resize_bulk_results_columns(self) -> None:
        if self.bulk_results_table is None:
            return
        columns = tuple(self.bulk_results_table["columns"])
        if not columns:
            return
        available_width = max(self.bulk_results_table.winfo_width() - 28, len(columns) * 60)
        weights = {
            "Parameter_Value": 0.9,
            "Scenario": 1.4,
            "Status": 0.8,
            "Total_Weighted_Cost": 1.1,
            "Run_Output_CSV": 1.8,
            "Failure_Reason": 1.5,
        }
        default_weight = 1.0
        total_weight = sum(weights.get(column, default_weight) for column in columns)
        for column in columns:
            width = int(available_width * weights.get(column, default_weight) / total_weight)
            self.bulk_results_table.column(column, width=max(58, width), stretch=True)

    def _bulk_row_selected_cost_value(self, row: BulkSimulationRunRow, cost_function: str) -> float:
        if cost_function == _TOTAL_WEIGHTED_COST_LABEL:
            return row.total_weighted_cost
        return float(bulk_row_cost_value(row, cost_function))

    def open_bulk_run_visualization(self, _event: tk.Event | None = None) -> None:
        if self.bulk_results_table is None:
            return
        selected = self.bulk_results_table.selection()
        if not selected:
            return
        row = self.bulk_result_rows_by_item.get(selected[0])
        if row is None:
            return
        if row.status != "Completed" or not row.run_output_csv:
            self._set_status("Bulk run has no completed output CSV to visualize.", "warning")
            return
        output_path = Path(row.run_output_csv)
        if not output_path.exists():
            self._set_status(f"Bulk run output CSV does not exist: {output_path}", "warning")
            return
        try:
            rows = load_simulation_rows_csv(output_path)
        except Exception as error:  # noqa: BLE001 - GUI should surface output-load problems.
            self._set_status(f"Error opening bulk visualization: {error}", "error")
            return
        window = BulkVisualizationWindow(
            self,
            self._bulk_visualization_header(row),
            rows,
            self._truck_length_m(),
            self._visualization_distances(),
            self.playback_speed_var.get(),
            on_close=self._forget_bulk_visualization_window,
        )
        self.bulk_visualization_windows.append(window)
        self._set_status(f"Opened bulk visualization for {row.scenario_name}.", "success")

    def _bulk_visualization_header(self, row: BulkSimulationRunRow) -> str:
        return (
            f"Bulk simulation: {row.scenario_name} | {row.parameter_name}={row.parameter_value:.10g} | "
            f"Cost function: {row.cost_function}"
        )

    def _forget_bulk_visualization_window(self, window: BulkVisualizationWindow) -> None:
        if window in self.bulk_visualization_windows:
            self.bulk_visualization_windows.remove(window)

    def _draw_bulk_chart(self, result: BulkSimulationResult) -> None:
        if self.bulk_chart_canvas is None:
            return
        canvas = self.bulk_chart_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 760)
        height = 270
        left, right, top, bottom = 60, 285, 42, 44
        totals_by_cost: dict[str, dict[float, float]] = {cost_function: {} for cost_function in result.cost_functions}
        for row in result.rows:
            if row.status != "Completed":
                continue
            for cost_function in result.cost_functions:
                totals = totals_by_cost[cost_function]
                totals[row.parameter_value] = totals.get(row.parameter_value, 0) + bulk_row_cost_value(row, cost_function)
        all_values = sorted({value for totals in totals_by_cost.values() for value in totals})
        if not all_values:
            canvas.create_text(width / 2, height / 2, text="No completed bulk results to chart.", fill="#555")
            return
        max_cost = max((cost for totals in totals_by_cost.values() for cost in totals.values()), default=1) or 1
        min_value = min(all_values)
        max_value = max(all_values)
        x_span = max(max_value - min_value, 1e-9)
        canvas.create_text(width / 2, 16, text="Cost Function Totals", fill="#222", font=("Arial", 11, "bold"))
        canvas.create_line(left, height - bottom, width - right, height - bottom, fill="#333")
        canvas.create_line(left, top, left, height - bottom, fill="#333")
        canvas.create_text(width / 2, height - 12, text=self.bulk_parameter_var.get(), fill="#333")
        canvas.create_text(18, height / 2, text="Cost", fill="#333", angle=90)
        self.bulk_chart_points = []
        colors = ("#1565c0", "#b00020", "#2e7d32", "#ef6c00", "#5e35b1")
        legend_x = max(left + 20, width - right + 28)
        for cost_index, cost_function in enumerate(result.cost_functions):
            color = colors[cost_index % len(colors)]
            legend_y = top + 8 + cost_index * 18
            canvas.create_line(legend_x, legend_y, legend_x + 25, legend_y, fill=color, width=2)
            canvas.create_oval(legend_x + 9, legend_y - 4, legend_x + 17, legend_y + 4, fill=color, outline=color)
            canvas.create_text(legend_x + 32, legend_y, text=cost_function, anchor="w", fill="#333")
            previous_point: tuple[float, float] | None = None
            for value in sorted(totals_by_cost[cost_function]):
                cost = totals_by_cost[cost_function][value]
                x = left + ((value - min_value) / x_span) * (width - left - right)
                y = height - bottom - (cost / max_cost) * (height - top - bottom)
                if previous_point is not None:
                    canvas.create_line(previous_point[0], previous_point[1], x, y, fill=color, width=2)
                canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline=color)
                if _bulk_chart_point_is_selected(self.bulk_selected_chart_point, value, cost_function, "cost"):
                    self._draw_bulk_selected_point(canvas, x, y)
                canvas.create_text(x, height - bottom + 14, text=f"{value:.3g}", fill="#555")
                canvas.create_text(x, y - 12, text=_bulk_number_label(cost), fill="#333")
                self.bulk_chart_points.append((x, y, value, cost_function, "cost"))
                previous_point = (x, y)

    def _draw_bulk_weighted_chart(self, result: BulkSimulationResult) -> None:
        if self.bulk_weighted_chart_canvas is None:
            return
        canvas = self.bulk_weighted_chart_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 760)
        height = 200
        left, right, top, bottom = 60, 285, 42, 44
        totals: dict[float, float] = {}
        for row in result.rows:
            if row.status == "Completed":
                totals[row.parameter_value] = totals.get(row.parameter_value, 0.0) + row.total_weighted_cost
        if not totals:
            canvas.create_text(width / 2, height / 2, text="No completed weighted results to chart.", fill="#555")
            return
        values = sorted(totals)
        max_cost = max(totals.values()) or 1.0
        min_value = min(values)
        max_value = max(values)
        x_span = max(max_value - min_value, 1e-9)
        canvas.create_text(width / 2, 16, text="Total Weighted Cost", fill="#222", font=("Arial", 11, "bold"))
        canvas.create_line(left, height - bottom, width - right, height - bottom, fill="#333")
        canvas.create_line(left, top, left, height - bottom, fill="#333")
        canvas.create_text(width / 2, height - 12, text=self.bulk_parameter_var.get(), fill="#333")
        canvas.create_text(18, height / 2, text="Weighted", fill="#333", angle=90)
        color = "#5e35b1"
        legend_x = max(left + 20, width - right + 28)
        canvas.create_line(legend_x, top + 10, legend_x + 25, top + 10, fill=color, width=2)
        canvas.create_oval(legend_x + 9, top + 6, legend_x + 17, top + 14, fill=color, outline=color)
        canvas.create_text(legend_x + 32, top + 10, text=_TOTAL_WEIGHTED_COST_LABEL, anchor="w", fill="#333")
        previous_point: tuple[float, float] | None = None
        for value in values:
            cost = totals[value]
            x = left + ((value - min_value) / x_span) * (width - left - right)
            y = height - bottom - (cost / max_cost) * (height - top - bottom)
            if previous_point is not None:
                canvas.create_line(previous_point[0], previous_point[1], x, y, fill=color, width=2)
            canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline=color)
            if _bulk_chart_point_is_selected(self.bulk_selected_chart_point, value, _TOTAL_WEIGHTED_COST_LABEL, "weighted"):
                self._draw_bulk_selected_point(canvas, x, y)
            canvas.create_text(x, height - bottom + 14, text=f"{value:.3g}", fill="#555")
            canvas.create_text(x, y - 12, text=_bulk_number_label(cost), fill="#333")
            self.bulk_chart_points.append((x, y, value, _TOTAL_WEIGHTED_COST_LABEL, "weighted"))
            previous_point = (x, y)

    def _draw_bulk_selected_point(self, canvas: tk.Canvas, x: float, y: float) -> None:
        canvas.create_oval(x - 9, y - 9, x + 9, y + 9, outline="#ffcc00", width=4)
        canvas.create_oval(x - 13, y - 13, x + 13, y + 13, outline="#111111", width=1)

    def _on_bulk_chart_click(self, event: tk.Event) -> None:
        if self.bulk_result is None or not self.bulk_chart_points:
            return
        chart_id = "weighted" if event.widget is self.bulk_weighted_chart_canvas else "cost"
        points = [point for point in self.bulk_chart_points if point[4] == chart_id]
        if not points:
            return
        nearest = min(points, key=lambda point: (point[0] - event.x) ** 2 + (point[1] - event.y) ** 2)
        if (nearest[0] - event.x) ** 2 + (nearest[1] - event.y) ** 2 > 400:
            return
        selected_value = nearest[2]
        selected_cost_function = nearest[3]
        self.bulk_selected_chart_point = (selected_value, selected_cost_function, chart_id)
        self.bulk_active_table_cost_function = selected_cost_function
        self._draw_bulk_chart(self.bulk_result)
        self._draw_bulk_weighted_chart(self.bulk_result)
        rows = tuple(
            row
            for row in self.bulk_result.rows
            if abs(row.parameter_value - selected_value) < 1e-9
        )
        self._populate_bulk_results_table(rows)
        self.bulk_progress_var.set(
            f"Showing all scenarios for value {selected_value:.10g}; red rows triggered {selected_cost_function}."
        )

    def _load_output_table(self, path: Path) -> None:
        with path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            columns = list(display_output_columns(reader.fieldnames or []))
            rows = list(reader)
            self.table.delete(*self.table.get_children())
            self.table["columns"] = columns
            self.table.tag_configure("truck1_row", background="#f2f2f2")
            self.table.tag_configure("truck2_row", background="#eef6ff")
            self.table.tag_configure("truck3_row", background="#fff4e8")
            for column in columns:
                header_text = output_header_label(column)
                self.table.heading(column, text=header_text)
                values = [display_cell_value(row.get(column, "")) for row in rows[:500]]
                self.table.column(
                    column,
                    width=preferred_column_width(header_text, values, min_width=48, max_width=220, include_header=False),
                    stretch=False,
                    anchor=table_column_anchor(column, "output"),
                )
            for index, row in enumerate(rows):
                if index >= 500:
                    break
                values = [display_cell_value(row.get(column, "")) for column in columns]
                self.table.insert("", tk.END, values=values)

    def _load_parameters_tab(self) -> None:
        if self.parameters_table is None:
            return
        path = Path(self.parameters_path.get())
        if not path.exists():
            self.parameters_csv_table = CsvTable((), ())
            self._populate_parameters_table()
        else:
            try:
                self.parameters_csv_table = load_csv_table(path)
                self._populate_parameters_table()
            except (OSError, csv.Error, UnicodeError):
                self.parameters_csv_table = CsvTable((), ())
                self._populate_parameters_table()
        self._parameters_dirty = False

    def _load_cost_weights_tab(self) -> None:
        if self.cost_weights_table is None:
            return
        path = Path(self.cost_function_weights_path.get())
        if not path.exists():
            self._populate_treeview(self.cost_weights_table, CsvTable((), ()), "parameters")
            return
        try:
            self._populate_treeview(self.cost_weights_table, load_csv_table(path), "parameters")
        except (OSError, csv.Error, UnicodeError):
            self._populate_treeview(self.cost_weights_table, CsvTable((), ()), "parameters")

    def _load_scenario_tab(self) -> None:
        if self.scenario_table is None:
            return
        self._refresh_loaded_scenario_label()
        path = Path(self.scenario_path.get())
        if not path.exists():
            self._populate_treeview(self.scenario_table, CsvTable((), ()), "scenario")
        else:
            try:
                self._populate_treeview(self.scenario_table, load_csv_table(path), "scenario")
            except (OSError, csv.Error, UnicodeError):
                self._populate_treeview(self.scenario_table, CsvTable((), ()), "scenario")
        self._scenario_dirty = False
        self._update_scenario_save_buttons()

    def _populate_treeview(self, table: ttk.Treeview, csv_table: CsvTable, table_kind: str) -> None:
        table.delete(*table.get_children())
        table["columns"] = csv_table.headers
        table.tag_configure("odd", background="#ffffff")
        table.tag_configure("even", background="#f7f7f7")
        for header in csv_table.headers:
            table.heading(header, text=header)
            header_index = csv_table.headers.index(header)
            values = [row[header_index] for row in csv_table.rows if header_index < len(row)]
            table.column(
                header,
                width=preferred_column_width(header, values),
                stretch=False,
                anchor=table_column_anchor(header, table_kind),
            )
        for index, row in enumerate(csv_table.rows):
            padded_row = row + ("",) * max(0, len(csv_table.headers) - len(row))
            tag = "even" if index % 2 else "odd"
            table.insert("", tk.END, values=padded_row[: len(csv_table.headers)], tags=(tag,))

    def _populate_parameters_table(self) -> None:
        if self.parameters_table is None:
            return
        table = self.parameters_table
        csv_table = self.parameters_csv_table
        filter_text = self.parameter_filter_var.get()
        table.delete(*table.get_children())
        table["columns"] = csv_table.headers
        table.tag_configure("group", background="#d9f2e6", font=("Arial", 9, "bold"))
        table.tag_configure("odd", background="#ffffff")
        table.tag_configure("even", background="#f7f7f7")
        for header in csv_table.headers:
            table.heading(header, text=header)
            header_index = csv_table.headers.index(header)
            values = [row[header_index] for row in csv_table.rows if header_index < len(row)]
            table.column(
                header,
                width=preferred_column_width(header, values),
                stretch=False,
                anchor=table_column_anchor(header, "parameters"),
            )
        rows_by_category = {category: [] for category in PARAMETER_CATEGORY_ORDER}
        for row in csv_table.rows:
            if not row or not parameter_row_matches_filter(row, filter_text):
                continue
            category = parameter_category(row[0])
            rows_by_category.setdefault(category, []).append(row)
        row_index = 0
        for category in PARAMETER_CATEGORY_ORDER:
            rows = rows_by_category.get(category, [])
            if not rows:
                continue
            group_values = (category,) + ("",) * max(0, len(csv_table.headers) - 1)
            table.insert("", tk.END, values=group_values[: len(csv_table.headers)], tags=("group",))
            for row in rows:
                padded_row = row + ("",) * max(0, len(csv_table.headers) - len(row))
                tag = "even" if row_index % 2 else "odd"
                table.insert("", tk.END, values=padded_row[: len(csv_table.headers)], tags=(tag,))
                row_index += 1

    def _retag_table_rows(self, table: ttk.Treeview) -> None:
        for index, item_id in enumerate(table.get_children()):
            tag = "even" if index % 2 else "odd"
            table.item(item_id, tags=(tag,))

    def _table_to_csv_table(self, table: ttk.Treeview) -> CsvTable:
        headers = tuple(str(column) for column in table["columns"])
        rows = tuple(
            tuple(str(value) for value in table.item(item_id, "values"))
            for item_id in table.get_children()
            if "group" not in table.item(item_id, "tags")
        )
        return CsvTable(headers=headers, rows=rows)

    def _capture_parameters_table_edits(self) -> None:
        if self.parameters_table is None or not self.parameters_csv_table.headers:
            return
        visible_rows = self._table_to_csv_table(self.parameters_table).rows
        if not visible_rows:
            return
        visible_by_name = {row[0]: row for row in visible_rows if row}
        updated_rows = tuple(visible_by_name.get(row[0], row) if row else row for row in self.parameters_csv_table.rows)
        self.parameters_csv_table = CsvTable(headers=self.parameters_csv_table.headers, rows=updated_rows)

    def save_parameters_tab(self) -> None:
        if self.parameters_table is None:
            return
        path = self.parameters_path.get()
        if not path:
            self.save_parameters_tab_as()
            return
        try:
            self._capture_parameters_table_edits()
            write_csv_table(path, self.parameters_csv_table)
            self._parameters_dirty = False
            self._save_run_config()
            self._set_status("Parameters saved.", "success")
        except Exception as error:  # noqa: BLE001 - GUI should surface save problems.
            self._set_status(f"Error saving parameters: {error}", "error")

    def save_parameters_tab_as(self) -> None:
        if self.parameters_table is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if not path:
            return
        try:
            self._capture_parameters_table_edits()
            write_csv_table(path, self.parameters_csv_table)
            self.parameters_path.set(path)
            self._parameters_dirty = False
            self._save_run_config()
            self._set_status("Parameters saved.", "success")
        except Exception as error:  # noqa: BLE001 - GUI should surface save problems.
            self._set_status(f"Error saving parameters: {error}", "error")

    def save_cost_weights_tab(self) -> None:
        if self.cost_weights_table is None:
            return
        path = self.cost_function_weights_path.get()
        if not path:
            self.save_cost_weights_tab_as()
            return
        try:
            write_csv_table(path, self._table_to_csv_table(self.cost_weights_table))
            load_cost_function_weights_csv(path)
            self._save_run_config()
            self._set_status("Cost weights saved.", "success")
        except Exception as error:  # noqa: BLE001 - GUI should surface save problems.
            self._set_status(f"Error saving cost weights: {error}", "error")

    def save_cost_weights_tab_as(self) -> None:
        if self.cost_weights_table is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if not path:
            return
        try:
            write_csv_table(path, self._table_to_csv_table(self.cost_weights_table))
            load_cost_function_weights_csv(path)
            self.cost_function_weights_path.set(path)
            self._save_run_config()
            self._set_status("Cost weights saved.", "success")
        except Exception as error:  # noqa: BLE001 - GUI should surface save problems.
            self._set_status(f"Error saving cost weights: {error}", "error")

    def save_scenario_tab(self) -> None:
        if self.scenario_table is None:
            return
        path = self.scenario_path.get()
        if not path:
            self.save_scenario_tab_as()
            return
        try:
            write_csv_table(path, self._table_to_csv_table(self.scenario_table))
            self._scenario_dirty = False
            self._update_scenario_save_buttons()
            self._save_run_config()
            self._set_status("Scenario saved.", "success")
        except Exception as error:  # noqa: BLE001 - GUI should surface save problems.
            self._set_status(f"Error saving scenario: {error}", "error")

    def save_scenario_tab_as(self) -> None:
        if self.scenario_table is None:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))
        if not path:
            return
        try:
            write_csv_table(path, self._table_to_csv_table(self.scenario_table))
            self.scenario_path.set(path)
            self._scenario_dirty = False
            self._update_scenario_save_buttons()
            self._save_run_config()
            self._set_status("Scenario saved.", "success")
        except Exception as error:  # noqa: BLE001 - GUI should surface save problems.
            self._set_status(f"Error saving scenario: {error}", "error")

    def insert_scenario_row(self) -> None:
        if self.scenario_table is None:
            return
        headers = tuple(str(column) for column in self.scenario_table["columns"])
        if not headers:
            headers = ("Time_s", "Truck1_Velocity_kph", "Truck2_Image_Event", "Truck3_Image_Event", "Notes")
            self.scenario_table["columns"] = headers
            for header in headers:
                self.scenario_table.heading(header, text=header)
                self.scenario_table.column(header, width=preferred_column_width(header, ()), stretch=False, anchor=table_column_anchor(header, "scenario"))
        values = ("",) * len(headers)
        selected = self.scenario_table.selection()
        if selected:
            index = self.scenario_table.index(selected[-1]) + 1
            self.scenario_table.insert("", index, values=values)
        else:
            self.scenario_table.insert("", tk.END, values=values)
        self._retag_table_rows(self.scenario_table)
        self._scenario_dirty = True
        self._update_scenario_save_buttons()
        self._clear_results_after_input_change()

    def delete_scenario_rows(self) -> None:
        if self.scenario_table is None:
            return
        for item_id in self.scenario_table.selection():
            self.scenario_table.delete(item_id)
        self._retag_table_rows(self.scenario_table)
        self._scenario_dirty = True
        self._update_scenario_save_buttons()
        self._clear_results_after_input_change()

    def _begin_parameter_cell_edit(self, event: tk.Event) -> None:
        table = event.widget if isinstance(event.widget, ttk.Treeview) else self.parameters_table
        if table is None:
            return
        row_id = table.identify_row(event.y)
        column_id = table.identify_column(event.x)
        if not row_id or not column_id:
            return
        if "group" in table.item(row_id, "tags"):
            return
        column_index = int(column_id.removeprefix("#")) - 1
        bbox = table.bbox(row_id, column_id)
        if not bbox:
            return
        values = list(table.item(row_id, "values"))
        current_value = values[column_index] if column_index < len(values) else ""
        if self._parameter_edit_entry is not None:
            self._parameter_edit_entry.destroy()
        entry = tk.Entry(table)
        entry.insert(0, current_value)
        entry.select_range(0, tk.END)
        entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        entry.focus_set()
        self._parameter_edit_entry = entry

        def commit(_event: tk.Event | None = None) -> None:
            if self._parameter_edit_entry is None:
                return
            values = list(table.item(row_id, "values"))
            while len(values) <= column_index:
                values.append("")
            values[column_index] = self._parameter_edit_entry.get()
            table.item(row_id, values=values)
            self._parameter_edit_entry.destroy()
            self._parameter_edit_entry = None
            if table is self.parameters_table:
                self._parameters_dirty = True

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)

    def _begin_scenario_cell_edit(self, event: tk.Event) -> None:
        if self.scenario_table is None:
            return
        row_id = self.scenario_table.identify_row(event.y)
        column_id = self.scenario_table.identify_column(event.x)
        if not row_id or not column_id:
            return
        column_index = int(column_id.removeprefix("#")) - 1
        headers = tuple(str(column) for column in self.scenario_table["columns"])
        if column_index >= len(headers):
            return
        bbox = self.scenario_table.bbox(row_id, column_id)
        if not bbox:
            return
        values = list(self.scenario_table.item(row_id, "values"))
        current_value = values[column_index] if column_index < len(values) else ""
        if self._scenario_edit_widget is not None:
            self._scenario_edit_widget.destroy()
        header = headers[column_index]
        if is_scenario_image_event_column(header):
            editor: tk.Entry | ttk.Combobox = ttk.Combobox(
                self.scenario_table,
                values=SCENARIO_IMAGE_EVENT_OPTIONS,
                state="readonly",
            )
            editor.set(current_value if current_value in SCENARIO_IMAGE_EVENT_OPTIONS else "")
        else:
            editor = tk.Entry(self.scenario_table)
            editor.insert(0, current_value)
            editor.select_range(0, tk.END)
        editor.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        editor.focus_set()
        self._scenario_edit_widget = editor

        def commit(_event: tk.Event | None = None) -> None:
            if self._scenario_edit_widget is None:
                return
            values = list(self.scenario_table.item(row_id, "values"))
            while len(values) <= column_index:
                values.append("")
            values[column_index] = self._scenario_edit_widget.get()
            self.scenario_table.item(row_id, values=values)
            self._scenario_edit_widget.destroy()
            self._scenario_edit_widget = None
            self._scenario_dirty = True
            self._update_scenario_save_buttons()
            self._clear_results_after_input_change()

        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)
        if isinstance(editor, ttk.Combobox):
            editor.bind("<<ComboboxSelected>>", commit)

    def _load_previous_run_files(self) -> None:
        output_path = Path(self.output_path.get())
        if output_path.exists():
            self._load_output_table(output_path)
            # _results_available stays False — view buttons stay disabled until user runs simulation this session
        log_path = Path(self.log_path.get())
        if log_path.exists():
            self._load_log_file(log_path)
        if output_path.exists():
            try:
                self._set_visualization_rows(load_simulation_rows_csv(output_path))
            except (ValueError, KeyError):
                if self.visualization is not None:
                    self.visualization.draw_frame(0)

    def _load_log(self, result) -> None:
        if self.log_text is None:
            return
        self.log_text.delete("1.0", tk.END)
        if not result.logs:
            self.log_text.insert(tk.END, "No log entries.\n")
            return
        for row in display_log_rows(result.logs):
            self.log_text.insert(tk.END, f"{row.text}\n", row.tag)

    def _load_log_file(self, path: Path) -> None:
        if self.log_text is None:
            return
        self.log_text.delete("1.0", tk.END)
        for row in display_log_rows_from_csv(path):
            self.log_text.insert(tk.END, f"{row.text}\n", row.tag)

    def _configure_log_tags(self) -> None:
        if self.log_text is None:
            return
        self.log_text.tag_configure("truck1", foreground=TRUCK_COLORS["truck1"], font=("Arial", 9, "bold"))
        self.log_text.tag_configure("truck2", foreground=TRUCK_COLORS["truck2"])
        self.log_text.tag_configure("truck3", foreground=TRUCK_COLORS["truck3"])
        self.log_text.tag_configure("general", foreground=TRUCK_COLORS["truck1"], font=("Arial", 9, "bold"))

    def open_charts(self) -> None:
        path = Path(self.charts_path.get())
        if not path.exists():
            self._set_status("Chart report does not exist yet. Run the simulation first.", "warning")
            return
        os.startfile(path)  # type: ignore[attr-defined]
        self._set_status("Chart report opened.", "success")

    def open_visualization_window(self) -> None:
        if self.visualization_window is not None and self.visualization_window.winfo_exists():
            self.visualization_window.lift()
            return

        self.visualization_window = tk.Toplevel(self)
        self.visualization_window.title("ConvoySIM Stage C Visualization")
        self.visualization_window.geometry("1280x860")
        self.visualization_window.minsize(1000, 720)
        self.visualization_window.protocol("WM_DELETE_WINDOW", self._close_visualization_window)

        tk.Label(
            self.visualization_window,
            textvariable=self.visualization_header_var,
            anchor="w",
            font=("Arial", 11, "bold"),
            fg="#333",
        ).pack(fill=tk.X, padx=8, pady=(6, 0))

        playback_controls = ttk.Frame(self.visualization_window)
        playback_controls.pack(fill=tk.X, padx=6, pady=6)
        self._colored_button(playback_controls, ">", self.play_visualization, "play", width=3).pack(side=tk.LEFT, padx=4)
        self._colored_button(playback_controls, "||", self.pause_visualization, "play", width=3).pack(side=tk.LEFT, padx=4)
        self._colored_button(playback_controls, "[]", self.stop_visualization, "danger", width=3).pack(side=tk.LEFT, padx=4)
        self._colored_button(playback_controls, "<<", self.step_back_visualization, "utility", width=3).pack(side=tk.LEFT, padx=4)
        self._colored_button(playback_controls, ">>", self.step_forward_visualization, "utility", width=3).pack(side=tk.LEFT, padx=4)
        self._colored_button(playback_controls, "Toggle Legend", self.toggle_visualization_legend, "view").pack(side=tk.LEFT, padx=4)
        self._colored_button(playback_controls, "Help", self.open_state_machine_help, "view").pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(
            playback_controls,
            text="Show gap charts",
            variable=self.show_gap_chart_var,
            command=self._on_chart_visibility_changed,
        ).pack(side=tk.LEFT, padx=(14, 4))
        ttk.Checkbutton(
            playback_controls,
            text="Show velocity chart",
            variable=self.show_velocity_chart_var,
            command=self._on_chart_visibility_changed,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(playback_controls, text="T2", variable=self.show_truck2_velocity_var, command=self._on_truck_velocity_visibility_changed).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Checkbutton(playback_controls, text="T3", variable=self.show_truck3_velocity_var, command=self._on_truck_velocity_visibility_changed).pack(side=tk.LEFT, padx=4)
        ttk.Label(playback_controls, textvariable=self.time_label_var).pack(side=tk.LEFT, padx=12)
        ttk.Label(playback_controls, textvariable=self.playback_speed_label_var).pack(side=tk.LEFT, padx=(18, 4))
        ttk.Scale(
            playback_controls,
            from_=0.3,
            to=2.0,
            orient=tk.HORIZONTAL,
            variable=self.playback_speed_var,
            command=self._on_playback_speed_changed,
            length=160,
        ).pack(side=tk.LEFT, padx=4)

        orange_distance_m, red_distance_m, loss_distance_m, resume_distance_m = self._visualization_distances()
        self.visualization_pane = tk.PanedWindow(
            self.visualization_window,
            orient=tk.VERTICAL,
            sashwidth=8,
            sashrelief=tk.RAISED,
            showhandle=True,
        )
        self.visualization_pane.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        self.visualization_pane.bind("<ButtonRelease-1>", self._on_visualization_divider_released)
        visualization_frame = ttk.Frame(self.visualization_pane)
        charts_frame = ttk.Frame(self.visualization_pane)
        self.visualization_pane.add(visualization_frame, minsize=280)
        self.visualization_pane.add(charts_frame, minsize=180)
        self.visualization = ConvoyPlaybackCanvas(
            visualization_frame,
            width=1220,
            height=360,
            orange_distance_m=orange_distance_m,
            red_distance_m=red_distance_m,
            loss_distance_m=loss_distance_m,
            resume_distance_m=resume_distance_m,
        )
        self.gap12_chart = ConvoyTimelineChart(
            charts_frame,
            title="Gap1-2 vs Time",
            y_label="Gap (m)",
            series=(
                ChartSeries(
                    "Gap1-2",
                    truck_color_for_label(1),
                    lambda row: row.truck2_gap_m,
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck2", start, end),
                ),
            ),
            width=1220,
            height=120,
            y_max_cap=40.0,
        )
        self.gap23_chart = ConvoyTimelineChart(
            charts_frame,
            title="Gap2-3 vs Time",
            y_label="Gap (m)",
            series=(
                ChartSeries(
                    "Gap2-3",
                    truck_color_for_label(0),
                    lambda row: row.truck3_gap_m,
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck3", start, end),
                ),
            ),
            width=1220,
            height=120,
            y_max_cap=40.0,
        )
        velocity_series_list = [ChartSeries("Truck1 velocity", "#333333", lambda row: row.truck1_velocity_kph)]
        if self.show_truck2_velocity_var.get():
            velocity_series_list.append(
                ChartSeries(
                    "Truck2 velocity",
                    truck_color_for_label(1),
                    lambda row: row.truck2_velocity_kph,
                    lambda row: row.truck2_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck2_state, row.truck2_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck2", start, end, default_dashed_for_truck2=True),
                )
            )
        if self.show_truck3_velocity_var.get():
            velocity_series_list.append(
                ChartSeries(
                    "Truck3 velocity",
                    truck_color_for_label(0),
                    lambda row: row.truck3_velocity_kph,
                    lambda row: row.truck3_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck3_state, row.truck3_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck3", start, end),
                )
            )
        self.velocity_chart = ConvoyTimelineChart(
            charts_frame,
            title="Velocity vs Time",
            y_label="Velocity (kph)",
            series=tuple(velocity_series_list),
            width=1220,
            height=120,
        )
        self._apply_chart_visibility()
        self.time_scale = ttk.Scale(
            charts_frame,
            from_=0.0,
            to=0.0,
            orient=tk.HORIZONTAL,
            variable=self.time_var,
            command=self._on_time_scale_changed,
        )
        self.time_scale.pack(fill=tk.X, padx=(int(CHART_LEFT_PX), int(CHART_RIGHT_MARGIN_PX)), pady=(6, 8))
        self.visualization_window.after_idle(self._apply_visualization_divider_position)
        self.legend_frame = self._build_visualization_legend(self.visualization_window)
        self.legend_frame.pack(fill=tk.X, padx=8, pady=(0, 8), before=self.visualization_pane)
        self.visualization_window.bind("<Left>", lambda _e: self._keyboard_viz_jump(-1.0))
        self.visualization_window.bind("<Right>", lambda _e: self._keyboard_viz_jump(1.0))
        self.visualization_window.bind("<Home>", lambda _e: self.stop_visualization())
        self.visualization_window.bind("<End>", lambda _e: self._keyboard_viz_jump_to_end())
        if self.visualization_rows:
            self._set_visualization_rows(self.visualization_rows)
        else:
            self.visualization.draw_frame(0)
            self.gap12_chart.draw(0)
            self.gap23_chart.draw(0)
            self.velocity_chart.draw(0)

    def _close_visualization_window(self) -> None:
        self.pause_visualization()
        if self.visualization_window is not None:
            self.visualization_window.destroy()
        self.visualization_window = None
        self.visualization = None
        self.gap12_chart = None
        self.gap23_chart = None
        self.velocity_chart = None
        self.time_scale = None
        self.legend_frame = None
        self.visualization_pane = None

    def _build_visualization_legend(self, parent: tk.Widget) -> ttk.Frame:
        frame = ttk.Frame(parent)
        items = (
            ("Truck #1 body / velocity", truck_color_for_label(2), None, 4),
            ("Truck #2 body / Gap1-2", truck_color_for_label(1), None, 4),
            ("Truck #3 body / Gap2-3", truck_color_for_label(0), None, 4),
            ("Image lost segment/status", truck_color_for_label(1), (5, 4), 3),
            ("Orange braking segment/status", "#d77a00", None, 4),
            ("Red braking / violation", "#b00020", None, 4),
            ("Chart time marker", "#111111", None, 2),
            ("Scenario loss target (empty triangle)", "#6f42c1", None, 2),
            ("Distance loss target (full triangle)", "#6f42c1", None, 2),
        )
        for index, (text, color, dash, width) in enumerate(items):
            item = tk.Frame(frame)
            item.grid(row=index // 5, column=index % 5, sticky="w", padx=8, pady=3)
            swatch = tk.Canvas(item, width=40, height=12, highlightthickness=0)
            swatch.pack(side=tk.LEFT)
            if "triangle" in text.lower():
                fill = color if "full" in text.lower() else "#ffffff"
                swatch.create_polygon(20, 1, 10, 11, 30, 11, outline=color, fill=fill, width=width)
            else:
                swatch.create_line(2, 6, 38, 6, fill=color, width=width, dash=dash)
            tk.Label(item, text=text).pack(side=tk.LEFT, padx=4)
        return frame

    def _on_chart_visibility_changed(self) -> None:
        self._apply_chart_visibility()
        self._save_run_config()

    def _on_truck_velocity_visibility_changed(self) -> None:
        self._redraw_velocity_chart()
        self._save_run_config()

    def _redraw_velocity_chart(self) -> None:
        """Rebuild velocity chart with only selected truck velocity lines."""
        if not hasattr(self, 'velocity_chart') or self.velocity_chart is None:
            return

        # Store current rows to redraw
        rows = self.velocity_chart.rows
        current_index = self.velocity_chart.current_index

        # Find the parent frame where the chart is packed
        charts_frame = self.velocity_chart.canvas.master

        # Destroy old chart canvas
        self.velocity_chart.canvas.pack_forget()
        self.velocity_chart.canvas.destroy()

        # Build new series based on visibility checkboxes
        velocity_series_list = [ChartSeries("Truck1 velocity", "#333333", lambda row: row.truck1_velocity_kph)]

        if self.show_truck2_velocity_var.get():
            velocity_series_list.append(
                ChartSeries(
                    "Truck2 velocity",
                    truck_color_for_label(1),
                    lambda row: row.truck2_velocity_kph,
                    lambda row: row.truck2_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck2_state, row.truck2_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck2", start, end, default_dashed_for_truck2=True),
                )
            )

        if self.show_truck3_velocity_var.get():
            velocity_series_list.append(
                ChartSeries(
                    "Truck3 velocity",
                    truck_color_for_label(0),
                    lambda row: row.truck3_velocity_kph,
                    lambda row: row.truck3_tracking_status == "Lost",
                    lambda row: chart_stroke_width(row.truck3_state, row.truck3_command),
                    segment_style_for_rows=lambda start, end: follower_chart_segment_style("Truck3", start, end),
                )
            )

        # Create new chart with filtered series
        self.velocity_chart = ConvoyTimelineChart(
            charts_frame,
            title="Velocity vs Time",
            y_label="Velocity (kph)",
            series=tuple(velocity_series_list),
            width=1220,
            height=120,
        )

        # Restore rows and redraw
        if rows:
            self.velocity_chart.set_rows(rows)
            if current_index < len(rows):
                self.velocity_chart.draw(current_index)

        # Make chart visible if needed
        if self.show_velocity_chart_var.get():
            self._set_chart_visible(self.velocity_chart, True)

    def _apply_chart_visibility(self) -> None:
        for chart in (self.gap12_chart, self.gap23_chart, self.velocity_chart):
            if chart is not None:
                chart.canvas.pack_forget()
        self._set_chart_visible(self.gap12_chart, self.show_gap_chart_var.get())
        self._set_chart_visible(self.gap23_chart, self.show_gap_chart_var.get())
        self._set_chart_visible(self.velocity_chart, self.show_velocity_chart_var.get())

    def _set_chart_visible(self, chart: ConvoyTimelineChart | None, visible: bool) -> None:
        if chart is None:
            return
        if visible:
            if self.time_scale is not None:
                chart.canvas.pack(fill=tk.BOTH, expand=True, before=self.time_scale)
            else:
                chart.canvas.pack(fill=tk.BOTH, expand=True)

    def _apply_visualization_divider_position(self) -> None:
        if self.visualization_pane is None:
            return
        pane_height = max(1, self.visualization_pane.winfo_height())
        max_position = max(280, pane_height - 180)
        position = max(280, min(self.visualization_divider_position, max_position))
        try:
            self.visualization_pane.sash_place(0, 0, position)
        except tk.TclError:
            pass

    def _on_visualization_divider_released(self, _event: tk.Event) -> None:
        if self.visualization_pane is None:
            return
        try:
            self.visualization_divider_position = max(280, int(self.visualization_pane.sash_coord(0)[1]))
        except tk.TclError:
            return
        self._save_run_config()

    def _save_run_config(self) -> None:
        save_stage_a_run_config(
            StageARunConfig(
                parameters_path=self.parameters_path.get(),
                scenario_path=self.scenario_path.get(),
                braking_table_path=self.braking_path.get(),
                output_path=self.output_path.get(),
                log_path=self.log_path.get(),
                charts_path=self.charts_path.get(),
                cost_function_weights_path=self.cost_function_weights_path.get(),
                show_gap_chart=self.show_gap_chart_var.get(),
                show_velocity_chart=self.show_velocity_chart_var.get(),
                show_truck2_velocity=self.show_truck2_velocity_var.get(),
                show_truck3_velocity=self.show_truck3_velocity_var.get(),
                playback_speed=self.playback_speed_var.get(),
                visualization_divider_position=self.visualization_divider_position,
                bulk_scenarios_dir=self.bulk_scenarios_dir.get(),
            )
        )

    def _set_visualization_rows(self, rows: tuple[SimulationRow, ...]) -> None:
        self.pause_visualization()
        self.visualization_rows = rows
        max_time_s = rows[-1].time_s if rows else 0.0
        if self.time_scale is not None:
            self.time_scale.configure(to=max_time_s)
        if self.visualization is not None:
            self.visualization.set_rows(rows, self._truck_length_m())
            orange_distance_m, red_distance_m, loss_distance_m, resume_distance_m = self._visualization_distances()
            self.visualization.set_braking_distances(
                orange_distance_m,
                red_distance_m,
                loss_distance_m,
                resume_distance_m,
            )
        if self.gap12_chart is not None:
            self.gap12_chart.set_rows(rows)
        if self.gap23_chart is not None:
            self.gap23_chart.set_rows(rows)
        if self.velocity_chart is not None:
            self.velocity_chart.set_rows(rows)
        self._draw_visualization_frame(0)

    def _truck_length_m(self) -> float:
        try:
            return load_parameters_csv(self.parameters_path.get()).initial_conditions.truck_length_m
        except (FileNotFoundError, ValueError):
            return 8.0

    def _visualization_distances(self) -> tuple[float | None, float | None, float | None, float | None]:
        try:
            parameters = load_parameters_csv(self.parameters_path.get()).simulation_parameters
            return (
                parameters.orange_distance_m,
                parameters.red_distance_m,
                parameters.image_identification_loss_distance_m,
                parameters.image_identification_resume_distance_m,
            )
        except (FileNotFoundError, ValueError):
            return None, None, None, None

    def play_visualization(self) -> None:
        if not self.visualization_rows:
            return
        self.is_playing = True
        self._schedule_next_frame()

    def pause_visualization(self) -> None:
        self.is_playing = False
        if self.playback_after_id is not None:
            self.after_cancel(self.playback_after_id)
            self.playback_after_id = None

    def stop_visualization(self) -> None:
        self.pause_visualization()
        self._draw_visualization_frame(0)

    def step_back_visualization(self) -> None:
        self.pause_visualization()
        self._draw_visualization_frame(self.current_frame_index - 1)

    def step_forward_visualization(self) -> None:
        self.pause_visualization()
        self._draw_visualization_frame(self.current_frame_index + 1)

    def _keyboard_viz_jump(self, delta_seconds: float) -> None:
        if not self.visualization_rows:
            return
        current_time = self.visualization_rows[self.current_frame_index].time_s
        self.pause_visualization()
        self._draw_visualization_frame(nearest_row_index(self.visualization_rows, current_time + delta_seconds))

    def _keyboard_viz_jump_to_end(self) -> None:
        if not self.visualization_rows:
            return
        self.pause_visualization()
        self._draw_visualization_frame(len(self.visualization_rows) - 1)

    def toggle_visualization_legend(self) -> None:
        if self.legend_frame is None:
            return
        if self.legend_frame.winfo_ismapped():
            self.legend_frame.pack_forget()
        else:
            self.legend_frame.pack(fill=tk.X, padx=8, pady=(0, 8), before=self.visualization_pane)

    def open_state_machine_help(self) -> None:
        try:
            help_data = load_state_machine_help(Path(__file__).resolve().parents[2] / "SimRequirements.md")
        except Exception as error:  # noqa: BLE001 - GUI should surface documentation parse failures.
            self._set_status(f"Error opening state-machine help: {error}", "error")
            return
        parent = self.visualization_window if self.visualization_window is not None else self
        window = tk.Toplevel(parent)
        window.title("State Machine Help")
        window.geometry("1100x620")
        window.minsize(800, 500)
        search_var = tk.StringVar(value="")
        search_frame = ttk.Frame(window)
        search_frame.pack(fill=tk.X, padx=8, pady=(8, 0))
        ttk.Label(search_frame, text="Search").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Entry(search_frame, textvariable=search_var, width=32).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._colored_button(search_frame, "Clear", lambda: search_var.set(""), "utility").pack(side=tk.LEFT, padx=(6, 0))
        help_tables: list[tuple[ttk.Treeview, tuple[tuple[str, ...], ...]]] = []
        help_tables.append(
            (
                self._add_help_table(window, "States and Commands", help_data.state_command_headers, help_data.state_command_rows),
                help_data.state_command_rows,
            )
        )
        help_tables.append(
            (
                self._add_help_table(window, "State Transitions", help_data.transition_headers, help_data.transition_rows),
                help_data.transition_rows,
            )
        )
        help_tables.append(
            (
                self._add_help_table(
                    window,
                    "Visualization Labels",
                    help_data.visualization_label_headers,
                    help_data.visualization_label_rows,
                ),
                help_data.visualization_label_rows,
            )
        )

        def refresh_help_tables(*_args: object) -> None:
            filter_text = search_var.get()
            for table, rows in help_tables:
                table.delete(*table.get_children())
                for row in rows:
                    if help_row_matches_filter(row, filter_text):
                        table.insert("", tk.END, values=row)

        search_var.trace_add("write", refresh_help_tables)

    def _add_help_table(
        self,
        parent: tk.Widget,
        title: str,
        headers: tuple[str, ...],
        rows: tuple[tuple[str, ...], ...],
    ) -> ttk.Treeview:
        frame = ttk.LabelFrame(parent, text=title)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        table = ttk.Treeview(frame, show="headings", columns=headers)
        y_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=table.yview)
        x_scroll = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=table.xview)
        table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        table.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        for header in headers:
            table.heading(header, text=header)
            table.column(header, width=260 if header in {"Meaning", "Command", "Condition"} else 180, stretch=True)
        for row in rows:
            table.insert("", tk.END, values=row)
        return table

    def _schedule_next_frame(self) -> None:
        if not self.is_playing:
            return
        if self.current_frame_index >= len(self.visualization_rows) - 1:
            self.pause_visualization()
            return
        self._draw_visualization_frame(self.current_frame_index + 1)
        self.playback_after_id = self.after(playback_delay_ms(self.playback_speed_var.get()), self._schedule_next_frame)

    def _draw_visualization_frame(self, index: int) -> None:
        if not self.visualization_rows:
            self.current_frame_index = 0
            self.time_label_var.set("Time: 0.0s")
            if self.visualization is not None:
                self.visualization.draw_frame(0)
            if self.gap12_chart is not None:
                self.gap12_chart.draw(0)
            if self.gap23_chart is not None:
                self.gap23_chart.draw(0)
            if self.velocity_chart is not None:
                self.velocity_chart.draw(0)
            return
        self.current_frame_index = max(0, min(index, len(self.visualization_rows) - 1))
        row = self.visualization_rows[self.current_frame_index]
        if self.visualization is not None:
            self.visualization.draw_frame(self.current_frame_index)
        if self.gap12_chart is not None:
            self.gap12_chart.draw(self.current_frame_index)
        if self.gap23_chart is not None:
            self.gap23_chart.draw(self.current_frame_index)
        if self.velocity_chart is not None:
            self.velocity_chart.draw(self.current_frame_index)
        self.time_label_var.set(f"Time: {row.time_s:.1f}s")
        self._updating_time_scale = True
        self.time_var.set(row.time_s)
        self._updating_time_scale = False

    def _on_time_scale_changed(self, value: str) -> None:
        if self._updating_time_scale or not self.visualization_rows:
            return
        self.pause_visualization()
        self._draw_visualization_frame(nearest_row_index(self.visualization_rows, float(value)))

    def _on_playback_speed_changed(self, value: str) -> None:
        self.playback_speed_label_var.set(f"Speed: x{float(value):.1f}")
        self._save_run_config()


def main() -> None:
    app = ConvoySimGui()
    app.mainloop()


if __name__ == "__main__":
    main()
