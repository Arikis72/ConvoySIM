"""Scenario timeline parsing for Stage A input files."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from convoysim.leader_profile import LeaderProfile, ProfilePoint


class ImageEvent(StrEnum):
    LOSS = "Loss"
    RESUME = "Resume"
    FORT_ACTIVATED = "FORT activated"


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

    @classmethod
    def from_csv(cls, path: str | Path) -> "ScenarioTimeline":
        with Path(path).open(newline="", encoding="utf-8") as csv_file:
            lines = csv_file.readlines()

        # Skip metadata rows (Description and Initial gaps) if present
        start_idx = 0
        if lines and lines[0].strip().startswith("Description:"):
            start_idx = 2

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

        return cls.from_rows(rows)

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
