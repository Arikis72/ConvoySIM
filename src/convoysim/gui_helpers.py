"""Small helpers for GUI table, help, and log presentation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import re
from typing import Iterable

TRUCK_COLORS = {
    "truck1": "#111111",
    "truck2": "#1f77b4",
    "truck3": "#ff7f0e",
    "general": "#666666",
}

SCENARIO_IMAGE_EVENT_OPTIONS = ("", "Loss", "Resume", "FORT activated")

PARAMETER_CATEGORY_ORDER = (
    "Geometry and initial conditions",
    "Dynamic limits and gap thresholds",
    "Image identification and loss recovery",
    "Communication",
    "Road and braking behavior",
    "Follower control",
    "Simulation timing",
    "Other",
)

OUTPUT_COLUMN_ORDER = (
    "Time_s",
    "Communication_Message",
    "Communication_Status",
    "Truck1_Position_m",
    "Truck1_Velocity_kph",
    "Truck1_Acceleration_mps2",
    "Truck1_State",
    "Truck1_Command",
    "Truck2_Position_m",
    "Truck2_Velocity_kph",
    "Truck2_Acceleration_mps2",
    "Truck2_Gap_m",
    "Truck2_Actual_Gap_m",
    "Truck2_Measured_Gap_m",
    "Truck2_Relative_Velocity_kph",
    "Truck2_State",
    "Truck2_Command",
    "Truck2_Loss_Source",
    "Truck2_Loss_Target_Rear_m",
    "Truck2_Orange_Trigger_Gap_m",
    "Truck2_Tracking_Status",
    "Gap2_Violation",
    "Violation_Type_Truck2",
    "Stop_Reason_Truck2",
    "Truck3_Position_m",
    "Truck3_Velocity_kph",
    "Truck3_Acceleration_mps2",
    "Truck3_Gap_m",
    "Truck3_Actual_Gap_m",
    "Truck3_Measured_Gap_m",
    "Truck3_Relative_Velocity_kph",
    "Truck3_State",
    "Truck3_Command",
    "Truck3_Loss_Source",
    "Truck3_Loss_Target_Rear_m",
    "Truck3_Orange_Trigger_Gap_m",
    "Truck3_Tracking_Status",
    "Gap3_Violation",
    "Violation_Type_Truck3",
    "Stop_Reason_Truck3",
    "Orange_Braking_Mode",
)


@dataclass(frozen=True)
class CsvTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class StateMachineHelp:
    state_command_headers: tuple[str, ...]
    state_command_rows: tuple[tuple[str, ...], ...]
    transition_headers: tuple[str, ...]
    transition_rows: tuple[tuple[str, ...], ...]
    visualization_label_headers: tuple[str, ...] = ()
    visualization_label_rows: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True)
class DisplayLogRow:
    time_s: float
    severity: str
    event: str
    message: str
    truck_order: int
    tag: str
    icon: str

    @property
    def text(self) -> str:
        return f"{self.time_s:.3f} {self.icon} [{self.severity}] {self.event}: {self.message}"


def load_csv_table(path: str | Path) -> CsvTable:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        lines = list(reader)

    # Skip SimGenerator metadata rows (Description and Initial gaps)
    start_idx = 0
    if lines and lines[0] and lines[0][0].startswith("Description:"):
        start_idx = 2

    # Extract headers and rows
    if start_idx < len(lines):
        headers = tuple(lines[start_idx])
        rows = tuple(tuple(row) for row in lines[start_idx + 1:])
    else:
        headers = ()
        rows = ()

    return CsvTable(headers=headers, rows=rows)


def write_csv_table(path: str | Path, table: CsvTable) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(table.headers)
        writer.writerows(table.rows)


def parameter_category(parameter_name: str) -> str:
    normalized = parameter_name.strip().lower()
    if normalized.startswith("truck length") or normalized.startswith("initial gap") or normalized.startswith("initial truck"):
        return "Geometry and initial conditions"
    if normalized in {
        "max velocity",
        "max acceleration",
        "max red deceleration",
        "minimum allowed gap distance",
        "maximum allowed gap distance",
        "red distance",
        "orange distance",
        "orange braking mode",
        "timeheadway",
        "emergency deceleration",
        "convoy target speed",
        "target gap",
    }:
        return "Dynamic limits and gap thresholds"
    if "image identification" in normalized or normalized.startswith("under-loss following") or normalized == "resume by distance":
        return "Image identification and loss recovery"
    if normalized.startswith("trucks communicating") or normalized.startswith("communication"):
        return "Communication"
    if normalized.startswith("road type") or normalized.startswith("orange deceleration"):
        return "Road and braking behavior"
    if normalized in {"green acceleration", "start moving gap", "optimal acceleration"}:
        return "Follower control"
    if normalized in {"simulation time step", "output table resolution"}:
        return "Simulation timing"
    return "Other"


def parameter_row_matches_filter(row: tuple[str, ...], filter_text: str) -> bool:
    text = filter_text.strip().lower()
    if not text:
        return True
    return any(text in cell.lower() for cell in row)


def help_row_matches_filter(row: tuple[str, ...], filter_text: str) -> bool:
    text = filter_text.strip().lower()
    if not text:
        return True
    return any(text in cell.lower() for cell in row)


def preferred_column_width(
    header: str,
    values: Iterable[str],
    min_width: int = 70,
    max_width: int = 360,
    include_header: bool = True,
) -> int:
    longest = max((len(str(value)) for value in values), default=0)
    if include_header:
        longest = max(longest, len(header))
    return max(min_width, min(max_width, longest * 8 + 24))


def wrap_header(header: str, max_part_length: int = 12) -> str:
    parts = header.split("_")
    if len(header) <= max_part_length or len(parts) == 1:
        return header
    lines: list[str] = []
    current = ""
    for part in parts:
        candidate = part if not current else f"{current}_{part}"
        if len(candidate) > max_part_length and current:
            lines.append(current)
            current = part
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines)


def display_output_columns(columns: Iterable[str]) -> tuple[str, ...]:
    available = tuple(columns)
    ordered = [column for column in OUTPUT_COLUMN_ORDER if column in available]
    ordered.extend(column for column in available if column not in ordered)
    return tuple(ordered)


def display_cell_value(value: str) -> str:
    text = str(value)
    try:
        numeric = float(text)
    except ValueError:
        return text
    if text.strip() == "":
        return text
    return f"{numeric:.1f}"


def output_header_label(header: str) -> str:
    labels = {
        "Time_s": "Time",
        "Communication_Message": "Comm Msg",
        "Communication_Status": "Comm",
        "Truck1_Position_m": "T1 Pos",
        "Truck1_Velocity_kph": "T1 Vel",
        "Truck1_Acceleration_mps2": "T1 Acc",
        "Truck1_State": "T1 State",
        "Truck1_Command": "T1 Cmd",
        "Truck2_Position_m": "T2 Pos",
        "Truck2_Velocity_kph": "T2 Vel",
        "Truck2_Acceleration_mps2": "T2 Acc",
        "Truck2_Gap_m": "T2 Gap",
        "Truck2_Actual_Gap_m": "T2 Actual",
        "Truck2_Measured_Gap_m": "T2 Meas",
        "Truck2_Relative_Velocity_kph": "T2 Rel",
        "Truck2_State": "T2 State",
        "Truck2_Command": "T2 Cmd",
        "Truck2_Loss_Source": "T2 Loss Src",
        "Truck2_Loss_Target_Rear_m": "T2 Target",
        "Truck2_Tracking_Status": "T2 Track",
        "Gap2_Violation": "T2 Viol",
        "Violation_Type_Truck2": "T2 Viol Type",
        "Stop_Reason_Truck2": "T2 Stop",
        "Truck3_Position_m": "T3 Pos",
        "Truck3_Velocity_kph": "T3 Vel",
        "Truck3_Acceleration_mps2": "T3 Acc",
        "Truck3_Gap_m": "T3 Gap",
        "Truck3_Actual_Gap_m": "T3 Actual",
        "Truck3_Measured_Gap_m": "T3 Meas",
        "Truck3_Relative_Velocity_kph": "T3 Rel",
        "Truck3_State": "T3 State",
        "Truck3_Command": "T3 Cmd",
        "Truck3_Loss_Source": "T3 Loss Src",
        "Truck3_Loss_Target_Rear_m": "T3 Target",
        "Truck3_Tracking_Status": "T3 Track",
        "Gap3_Violation": "T3 Viol",
        "Violation_Type_Truck3": "T3 Viol Type",
        "Stop_Reason_Truck3": "T3 Stop",
    }
    return labels.get(header, header.replace("_", " "))


def table_column_anchor(header: str, table_kind: str) -> str:
    if table_kind == "parameters" and header.lower() in {"value", "unit"}:
        return "center"
    if table_kind == "scenario" and header.lower() != "notes":
        return "center"
    if table_kind == "output":
        return "center"
    return "w"


def is_scenario_image_event_column(header: str) -> bool:
    return header in {"Truck2_Image_Event", "Truck3_Image_Event"}


def output_column_group(header: str) -> str:
    if header.startswith("Truck1_"):
        return "truck1"
    if header.startswith("Truck2_") or header.endswith("_Truck2") or header.startswith("Gap2_"):
        return "truck2"
    if header.startswith("Truck3_") or header.endswith("_Truck3") or header.startswith("Gap3_"):
        return "truck3"
    return "general"


def state_machine_help_from_markdown(text: str) -> StateMachineHelp:
    required = _table_after_heading(text, "### 17.1 Required states")
    transitions = _table_after_heading(text, "### 17.2 State transitions")
    commands = _table_after_heading(text, "### 17.3 State-to-command mapping")
    visualization_labels = _table_after_heading(text, "### 17.4 Visualization help labels")
    command_by_state = {row[0]: row[1] for row in commands.rows if len(row) >= 2}
    merged_rows = tuple(
        (row[0], row[1], command_by_state.get(row[0], ""))
        for row in required.rows
        if len(row) >= 2
    )
    return StateMachineHelp(
        state_command_headers=("State", "Meaning", "Command"),
        state_command_rows=merged_rows,
        transition_headers=transitions.headers,
        transition_rows=transitions.rows,
        visualization_label_headers=visualization_labels.headers,
        visualization_label_rows=visualization_labels.rows,
    )


def load_state_machine_help(path: str | Path = "SimRequirements.md") -> StateMachineHelp:
    return state_machine_help_from_markdown(Path(path).read_text(encoding="utf-8"))


def display_log_rows(log_rows: Iterable[object]) -> tuple[DisplayLogRow, ...]:
    rows = tuple(_display_log_row(row) for row in log_rows)
    return tuple(sorted(rows, key=lambda row: (row.time_s, row.truck_order, row.event, row.message)))


def display_log_rows_from_csv(path: str | Path) -> tuple[DisplayLogRow, ...]:
    with Path(path).open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return display_log_rows(
            _CsvLogRow(
                time_s=float(row.get("Time_s", "") or 0.0),
                severity=row.get("Severity", ""),
                event=row.get("Event", ""),
                message=row.get("Message", ""),
            )
            for row in reader
        )


def log_truck_order(event: str, message: str) -> int:
    combined = f"{event} {message}"
    match = re.search(r"truck\s*#?\s*([123])|truck([123])", combined, flags=re.IGNORECASE)
    if not match:
        return 4
    return int(match.group(1) or match.group(2))


def log_tag_for_truck_order(truck_order: int) -> str:
    if truck_order == 1:
        return "truck1"
    if truck_order == 2:
        return "truck2"
    if truck_order == 3:
        return "truck3"
    return "general"


def log_state_icon(event: str, message: str) -> str:
    combined = f"{event} {message}".lower()
    if "red" in combined or "collision" in combined or "minimum gap" in combined:
        return "=="
    if "orange" in combined or "braking" in combined or "stop request" in combined:
        return "--"
    if "loss" in combined or "lost" in combined or "tracking" in combined:
        return ".."
    return "-"


@dataclass(frozen=True)
class _MarkdownTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class _CsvLogRow:
    time_s: float
    severity: str
    event: str
    message: str


def _display_log_row(row: object) -> DisplayLogRow:
    time_s = float(getattr(row, "time_s"))
    severity = str(getattr(row, "severity"))
    event = str(getattr(row, "event"))
    message = str(getattr(row, "message"))
    truck_order = log_truck_order(event, message)
    return DisplayLogRow(
        time_s=time_s,
        severity=severity,
        event=event,
        message=message,
        truck_order=truck_order,
        tag=log_tag_for_truck_order(truck_order),
        icon=log_state_icon(event, message),
    )


def _table_after_heading(text: str, heading: str) -> _MarkdownTable:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return _read_markdown_table(lines[index + 1 :])
    raise ValueError(f"Could not find requirements table after heading: {heading}")


def _read_markdown_table(lines: list[str]) -> _MarkdownTable:
    table_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if table_lines:
                break
            continue
        if stripped.startswith("|"):
            table_lines.append(stripped)
        elif table_lines:
            break
    if len(table_lines) < 2:
        raise ValueError("Expected a Markdown table with a header and separator.")
    headers = _split_markdown_row(table_lines[0])
    rows = tuple(_split_markdown_row(line) for line in table_lines[2:])
    return _MarkdownTable(headers=headers, rows=rows)


def _split_markdown_row(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
