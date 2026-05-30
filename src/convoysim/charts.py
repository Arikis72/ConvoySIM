"""Dependency-free Stage A chart export."""

from __future__ import annotations

from html import escape
from pathlib import Path

from convoysim.models import SimulationParameters
from convoysim.simulation import SimulationResult, SimulationRow


_PLOT_LEFT = 70.0
_PLOT_RIGHT = 850.0
_PLOT_TOP = 30.0
_PLOT_BOTTOM = 260.0
_PLOT_WIDTH = _PLOT_RIGHT - _PLOT_LEFT
_PLOT_HEIGHT = _PLOT_BOTTOM - _PLOT_TOP


def write_stage_a_charts_html(
    result: SimulationResult,
    parameters: SimulationParameters,
    path: str | Path,
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>ConvoySIM Stage A Charts</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    .chart {{ border: 1px solid #ccc; margin-bottom: 24px; max-width: 100%; }}
    .chart-layout {{ display: flex; align-items: flex-start; gap: 18px; margin-bottom: 24px; }}
    .chart-layout .chart {{ flex: 0 0 auto; margin-bottom: 0; }}
    .legend {{ border: 1px solid #ddd; padding: 10px 12px; min-width: 260px; max-width: 360px; background: #fafafa; }}
    .legend span {{ display: block; margin: 0 0 10px 0; }}
    .legend-line {{ display: inline-block; width: 34px; height: 0; border-top: 3px solid currentColor; vertical-align: middle; margin-right: 6px; }}
    .legend-line.dotted {{ border-top-style: dotted; }}
    .legend-line.bold {{ border-top-width: 5px; }}
    .legend-line.double-bold {{ border-top-width: 7px; }}
    .legend-note {{ color: #555; margin-top: 6px; }}
    table {{ border-collapse: collapse; }}
    th, td {{ border: 1px solid #ddd; padding: 4px 8px; }}
  </style>
</head>
<body>
  <h1>ConvoySIM Stage A Charts</h1>
  <p>Use browser zoom/save features to inspect or save this chart report.</p>
  <h2>Gap vs Time</h2>
  <div class="chart-layout">
    {_gap_chart(result.rows, parameters)}
    <div class="legend">
      <strong>Legend</strong>
      <span style="color:#1f77b4"><i class="legend-line"></i>Truck #2 gap</span>
      <span style="color:#2ca02c"><i class="legend-line"></i>Truck #3 gap</span>
      <span style="color:#d62728"><i class="legend-line dotted"></i>Minimum / Red thresholds</span>
      <span style="color:#2ca02c"><i class="legend-line dotted"></i>Orange / Maximum thresholds</span>
      <span style="color:#9467bd"><i class="legend-line dotted"></i>Image loss threshold</span>
      <span style="color:#8c564b"><i class="legend-line dotted"></i>Image resume threshold</span>
      <span><i class="legend-line bold"></i>Orange braking = bold data line</span>
      <span><i class="legend-line double-bold"></i>Red braking = double-bold data line</span>
      <div class="legend-note">Solid data line = tracking; dotted data line = image identification lost for that follower. Braking thickness can combine with dotted loss segments.</div>
    </div>
  </div>
  <h2>Velocity vs Time</h2>
  <div class="chart-layout">
    {_velocity_chart(result.rows)}
    <div class="legend">
      <strong>Legend</strong>
      <span style="color:#333"><i class="legend-line"></i>Truck #1 velocity</span>
      <span style="color:#1f77b4"><i class="legend-line" style="border-top-style: dashed;"></i>Truck #2 velocity (dashed)</span>
      <span style="color:#2ca02c"><i class="legend-line"></i>Truck #3 velocity</span>
      <span><i class="legend-line dotted"></i>Dotted segment = image identification lost</span>
      <span><i class="legend-line bold"></i>Orange braking = bold data line</span>
      <span><i class="legend-line double-bold"></i>Red braking = double-bold data line</span>
    </div>
  </div>
  <h2>Events</h2>
  {_event_table(result.rows)}
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def _gap_chart(rows: tuple[SimulationRow, ...], parameters: SimulationParameters) -> str:
    max_gap = max(
        max(row.truck2_gap_m, row.truck3_gap_m) for row in rows
    )
    y_max = max(
        max_gap,
        parameters.maximum_gap_m,
        parameters.image_identification_loss_distance_m,
        parameters.orange_distance_m,
    )
    series = [
        _segmented_polyline(
            rows,
            lambda row: row.truck1_position_m,
            lambda row: row.truck2_gap_m,
            y_max,
            "#1f77b4",
            lambda row: row.truck2_tracking_status == "Lost",
            lambda row: _follower_stroke_width(row.truck2_state, row.truck2_command),
        ),
        _segmented_polyline(
            rows,
            lambda row: row.truck1_position_m,
            lambda row: row.truck3_gap_m,
            y_max,
            "#2ca02c",
            lambda row: row.truck3_tracking_status == "Lost",
            lambda row: _follower_stroke_width(row.truck3_state, row.truck3_command),
        ),
    ]
    thresholds = [
        ("Minimum", parameters.minimum_gap_m, "#d62728"),
        ("Red", parameters.red_distance_m, "#d62728"),
        ("Orange", parameters.orange_distance_m, "#2ca02c"),
        ("Maximum", parameters.maximum_gap_m, "#2ca02c"),
        ("Loss", parameters.image_identification_loss_distance_m, "#9467bd"),
        ("Resume", parameters.image_identification_resume_distance_m, "#8c564b"),
    ]
    return _svg(
        rows,
        y_max,
        "Distance (m)",
        "Gap (m)",
        series + [_threshold_line(rows, value, y_max, color, label) for label, value, color in thresholds],
    )


def _velocity_chart(rows: tuple[SimulationRow, ...]) -> str:
    y_max = max(
        max(row.truck1_velocity_kph, row.truck2_velocity_kph, row.truck3_velocity_kph)
        for row in rows
    )
    y_max = max(y_max, 1.0)
    series = [
        _polyline(rows, lambda row: row.truck1_position_m, lambda row: row.truck1_velocity_kph, y_max, "#333333"),
        _segmented_polyline(
            rows,
            lambda row: row.truck1_position_m,
            lambda row: row.truck2_velocity_kph,
            y_max,
            "#1f77b4",
            lambda row: row.truck2_tracking_status == "Lost",
            lambda row: _follower_stroke_width(row.truck2_state, row.truck2_command),
            default_dashed=True,
        ),
        _segmented_polyline(
            rows,
            lambda row: row.truck1_position_m,
            lambda row: row.truck3_velocity_kph,
            y_max,
            "#2ca02c",
            lambda row: row.truck3_tracking_status == "Lost",
            lambda row: _follower_stroke_width(row.truck3_state, row.truck3_command),
        ),
    ]
    return _svg(rows, y_max, "Distance (m)", "Velocity (kph)", series)


def _event_table(rows: tuple[SimulationRow, ...]) -> str:
    event_rows = [
        row
        for row in rows
        if row.communication_message
        or row.stop_reason_truck2
        or row.stop_reason_truck3
        or row.violation_type_truck2
        or row.violation_type_truck3
    ]
    if not event_rows:
        return "<p>No events recorded.</p>"

    body = "\n".join(
        "<tr>"
        f"<td>{row.time_s:.3f}</td>"
        f"<td>{escape(row.communication_status)}</td>"
        f"<td>{escape(row.communication_message)}</td>"
        f"<td>{escape(row.violation_type_truck2)}</td>"
        f"<td>{escape(row.violation_type_truck3)}</td>"
        f"<td>{escape(row.stop_reason_truck2)}</td>"
        f"<td>{escape(row.stop_reason_truck3)}</td>"
        "</tr>"
        for row in event_rows
    )
    return (
        "<table><thead><tr><th>Time_s</th><th>Communication</th><th>Message</th>"
        "<th>Truck2 Violation</th><th>Truck3 Violation</th><th>Truck2 Stop</th><th>Truck3 Stop</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def _svg(
    rows: tuple[SimulationRow, ...],
    y_max: float,
    x_label: str,
    y_label: str,
    elements: list[str],
) -> str:
    x_max = rows[-1].truck1_position_m
    axes = _axis_elements(x_max, y_max, x_label, y_label)
    return f'<svg class="chart" width="930" height="340" viewBox="0 0 930 340">{axes}{"".join(elements)}</svg>'


def _polyline(rows: tuple[SimulationRow, ...], get_x, get_y, y_max: float, color: str) -> str:
    points = " ".join(_point(row, rows[-1].truck1_position_m, y_max, get_x, get_y) for row in rows)
    return f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>'


def _segmented_polyline(
    rows: tuple[SimulationRow, ...],
    get_x,
    get_y,
    y_max: float,
    color: str,
    is_dotted,
    stroke_width,
    default_dashed: bool = False,
) -> str:
    if len(rows) < 2:
        return _polyline(rows, get_x, get_y, y_max, color)

    x_max = rows[-1].truck1_position_m
    segments: list[str] = []
    for index in range(len(rows) - 1):
        start = rows[index]
        end = rows[index + 1]
        points = f"{_point(start, x_max, y_max, get_x, get_y)} {_point(end, x_max, y_max, get_x, get_y)}"

        # Determine dash pattern
        is_loss = is_dotted(start) or is_dotted(end)
        if is_loss:
            dash = ' stroke-dasharray="2,3"'  # dotted pattern
        elif default_dashed:
            dash = ' stroke-dasharray="6,3"'  # dashed pattern
        else:
            dash = ""

        width = max(stroke_width(start), stroke_width(end))
        segments.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>')
    return "".join(segments)


def _follower_stroke_width(state: str, command: str) -> int:
    combined = f"{state} {command}".lower()
    if "red" in combined:
        return 6
    if "orange" in combined or "communication_request_stop" in combined or "communication stop" in combined:
        return 4
    return 2


def _threshold_line(rows: tuple[SimulationRow, ...], value: float, y_max: float, color: str, label: str) -> str:
    y = _scale_y(value, y_max)
    return (
        f'<line x1="{_PLOT_LEFT:.0f}" y1="{y:.2f}" x2="{_PLOT_RIGHT:.0f}" y2="{y:.2f}" stroke="{color}" stroke-dasharray="5,4"/>'
        f'<text x="{_PLOT_RIGHT + 5:.0f}" y="{y + 4:.2f}" fill="{color}">{escape(label)}</text>'
    )


def _point(row: SimulationRow, x_max: float, y_max: float, get_x, get_y) -> str:
    x = _scale_x(get_x(row), x_max)
    y = _scale_y(get_y(row), y_max)
    return f"{x:.2f},{y:.2f}"


def _axis_elements(x_max: float, y_max: float, x_label: str, y_label: str) -> str:
    x_axis = f'<line x1="{_PLOT_LEFT:.0f}" y1="{_PLOT_BOTTOM:.0f}" x2="{_PLOT_RIGHT:.0f}" y2="{_PLOT_BOTTOM:.0f}" stroke="#666"/>'
    y_axis = f'<line x1="{_PLOT_LEFT:.0f}" y1="{_PLOT_TOP:.0f}" x2="{_PLOT_LEFT:.0f}" y2="{_PLOT_BOTTOM:.0f}" stroke="#666"/>'
    labels = (
        f'<text x="{(_PLOT_LEFT + _PLOT_RIGHT) / 2:.0f}" y="325" text-anchor="middle">{escape(x_label)}</text>'
        f'<text x="18" y="{(_PLOT_TOP + _PLOT_BOTTOM) / 2:.0f}" text-anchor="middle" transform="rotate(-90 18 {(_PLOT_TOP + _PLOT_BOTTOM) / 2:.0f})">{escape(y_label)}</text>'
    )
    return x_axis + y_axis + labels + _x_ticks(x_max) + _y_ticks(y_max)


def _x_ticks(x_max: float, tick_count: int = 6) -> str:
    if tick_count <= 0:
        return ""
    elements: list[str] = []
    for index in range(tick_count + 1):
        value = x_max * index / tick_count if tick_count else 0.0
        x = _scale_x(value, x_max)
        elements.append(f'<line x1="{x:.2f}" y1="{_PLOT_BOTTOM:.0f}" x2="{x:.2f}" y2="{_PLOT_BOTTOM + 6:.0f}" stroke="#666"/>')
        elements.append(f'<line x1="{x:.2f}" y1="{_PLOT_TOP:.0f}" x2="{x:.2f}" y2="{_PLOT_BOTTOM:.0f}" stroke="#eee"/>')
        elements.append(f'<text x="{x:.2f}" y="{_PLOT_BOTTOM + 22:.0f}" text-anchor="middle">{value:.0f}</text>')
    return "".join(elements)


def _y_ticks(y_max: float, tick_count: int = 5) -> str:
    if tick_count <= 0:
        return ""
    elements: list[str] = []
    for index in range(tick_count + 1):
        value = y_max * index / tick_count if tick_count else 0.0
        y = _scale_y(value, y_max)
        elements.append(f'<line x1="{_PLOT_LEFT - 6:.0f}" y1="{y:.2f}" x2="{_PLOT_LEFT:.0f}" y2="{y:.2f}" stroke="#666"/>')
        elements.append(f'<line x1="{_PLOT_LEFT:.0f}" y1="{y:.2f}" x2="{_PLOT_RIGHT:.0f}" y2="{y:.2f}" stroke="#eee"/>')
        elements.append(f'<text x="{_PLOT_LEFT - 10:.0f}" y="{y + 4:.2f}" text-anchor="end">{value:.1f}</text>')
    return "".join(elements)


def _scale_x(value: float, x_max: float) -> float:
    return _PLOT_LEFT + (value / x_max) * _PLOT_WIDTH if x_max > 0 else _PLOT_LEFT


def _scale_y(value: float, y_max: float) -> float:
    return _PLOT_BOTTOM - (value / y_max) * _PLOT_HEIGHT if y_max > 0 else _PLOT_BOTTOM
