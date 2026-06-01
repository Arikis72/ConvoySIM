"""Scenario timeline parsing for Stage A input files."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from convoysim.leader_profile import LeaderProfile, ProfilePoint

if TYPE_CHECKING:
    from convoysim.models import InitialConditions


class ImageEvent(StrEnum):
    LOSS = "Loss"
    RESUME = "Resume"
    FORT_ACTIVATED = "FORT activated"
    ORANGE_BRAKE = "Orange_Brake"


@dataclass(frozen=True)
class ImageEventPoint:
    time_s: float
    event: ImageEvent


@dataclass(frozen=True)
class ScenarioTimelineRow:
    time_s: float
    truck1_velocity_kph: float | None = None
    truck1_event: ImageEvent | None = None
    truck2_image_event: ImageEvent | None = None
    truck3_image_event: ImageEvent | None = None
    notes: str = ""


@dataclass(frozen=True)
class ScenarioTimeline:
    rows: tuple[ScenarioTimelineRow, ...]
    # Initial gaps parsed from CSV metadata row (None if not present)
    initial_gap_12_m: float | None = None
    initial_gap_23_m: float | None = None

    @classmethod
    def from_csv(cls, path: str | Path) -> "ScenarioTimeline":
        with Path(path).open(newline="", encoding="utf-8") as csv_file:
            lines = csv_file.readlines()

        # Parse initial gaps from metadata row 2 if present
        initial_gap_12_m: float | None = None
        initial_gap_23_m: float | None = None
        start_idx = 0
        if lines and lines[0].strip().startswith("Description:"):
            start_idx = 2
            if len(lines) >= 2:
                gap_row = next(csv.reader([lines[1]]))
                if gap_row and gap_row[0].strip().lower().startswith("initial gaps"):
                    try:
                        initial_gap_12_m = float(gap_row[1].strip()) if len(gap_row) > 1 and gap_row[1].strip() else None
                        initial_gap_23_m = float(gap_row[2].strip()) if len(gap_row) > 2 and gap_row[2].strip() else None
                    except ValueError:
                        pass  # malformed — ignore and fall back to parameters

        # Parse CSV starting from the header row
        csv_content = "".join(lines[start_idx:])
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        required_columns = {"Time_s", "Truck1_Velocity_kph", "Truck1_Event", "Truck2_Image_Event", "Truck3_Image_Event"}
        fieldnames = set(reader.fieldnames or [])
        missing_columns = required_columns - fieldnames
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Scenario timeline CSV is missing required columns: {missing}.")

        rows = tuple(_parse_row(row, row_number=index) for index, row in enumerate(reader, start=start_idx + 2))

        timeline = cls.from_rows(rows)
        return replace(timeline, initial_gap_12_m=initial_gap_12_m, initial_gap_23_m=initial_gap_23_m)

    def apply_initial_gaps(self, initial: "InitialConditions") -> "InitialConditions":
        """Return initial conditions with gaps overridden from CSV metadata if present."""
        overrides: dict[str, float] = {}
        if self.initial_gap_12_m is not None:
            overrides["initial_gap_12_m"] = self.initial_gap_12_m
        if self.initial_gap_23_m is not None:
            overrides["initial_gap_23_m"] = self.initial_gap_23_m
        return replace(initial, **overrides) if overrides else initial

    @classmethod
    def from_rows(cls, rows: tuple[ScenarioTimelineRow, ...]) -> "ScenarioTimeline":
        if not rows:
            raise ValueError("Scenario timeline must contain at least one row.")

        for previous, current in zip(rows, rows[1:]):
            if current.time_s <= previous.time_s:
                raise ValueError("Scenario timeline times must be strictly increasing.")

        return cls(rows)

    @property
    def end_time_s(self) -> float:
        return self.rows[-1].time_s

    def leader_profile(self) -> LeaderProfile:
        points = [
            ProfilePoint(time_s=row.time_s, velocity_kph=row.truck1_velocity_kph)
            for row in self.rows
            if row.truck1_velocity_kph is not None
        ]
        return LeaderProfile.from_points(points)

    def truck2_image_events(self) -> tuple[ImageEventPoint, ...]:
        return tuple(
            ImageEventPoint(time_s=row.time_s, event=row.truck2_image_event)
            for row in self.rows
            if row.truck2_image_event is not None
        )

    def truck1_events(self) -> tuple[ImageEventPoint, ...]:
        return tuple(
            ImageEventPoint(time_s=row.time_s, event=row.truck1_event)
            for row in self.rows
            if row.truck1_event is not None
        )

    def truck3_image_events(self) -> tuple[ImageEventPoint, ...]:
        return tuple(
            ImageEventPoint(time_s=row.time_s, event=row.truck3_image_event)
            for row in self.rows
            if row.truck3_image_event is not None
        )

    def orange_brake_windows(self) -> tuple[tuple[float, float], ...]:
        """Return (start_s, end_s) windows during which Truck 1 orange brake is active.

        Each Orange_Brake row contributes 1 second.  Consecutive rows extend the window.
        """
        ob_times = sorted(
            row.time_s for row in self.rows if row.truck1_event == ImageEvent.ORANGE_BRAKE
        )
        if not ob_times:
            return ()
        windows: list[tuple[float, float]] = []
        start = ob_times[0]
        end = ob_times[0] + 1.0
        for t in ob_times[1:]:
            if t <= end + 1e-9:  # consecutive (within 1 s of current window end)
                end = t + 1.0
            else:
                windows.append((start, end))
                start = t
                end = t + 1.0
        windows.append((start, end))
        return tuple(windows)


def _parse_row(row: dict[str, str], row_number: int) -> ScenarioTimelineRow:
    try:
        time_s = float(row["Time_s"])
    except ValueError as error:
        raise ValueError(f"Row {row_number}: Time_s must be numeric.") from error

    if time_s < 0:
        raise ValueError(f"Row {row_number}: Time_s cannot be negative.")

    return ScenarioTimelineRow(
        time_s=time_s,
        truck1_velocity_kph=_parse_optional_float(row["Truck1_Velocity_kph"], "Truck1_Velocity_kph", row_number),
        truck1_event=_parse_optional_event(row["Truck1_Event"], "Truck1_Event", row_number),
        truck2_image_event=_parse_optional_event(row["Truck2_Image_Event"], "Truck2_Image_Event", row_number),
        truck3_image_event=_parse_optional_event(row["Truck3_Image_Event"], "Truck3_Image_Event", row_number),
        notes=row.get("Notes", "").strip(),
    )


def _parse_optional_float(value: str, field_name: str, row_number: int) -> float | None:
    stripped = value.strip()
    if not stripped:
        return None

    try:
        parsed = float(stripped)
    except ValueError as error:
        raise ValueError(f"Row {row_number}: {field_name} must be numeric when provided.") from error

    if parsed < 0:
        raise ValueError(f"Row {row_number}: {field_name} cannot be negative.")

    return parsed


def _parse_optional_event(value: str, field_name: str, row_number: int) -> ImageEvent | None:
    stripped = value.strip()
    if not stripped:
        return None

    try:
        return ImageEvent(stripped)
    except ValueError as error:
        valid_values = ", ".join(event.value for event in ImageEvent)
        raise ValueError(f"Row {row_number}: {field_name} must be blank or one of: {valid_values}.") from error
