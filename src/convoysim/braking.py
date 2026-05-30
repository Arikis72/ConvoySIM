"""Braking-distance table loading and deceleration lookup."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import csv

from convoysim.models import RoadType
from convoysim.units import kph_to_mps


class BrakingType(StrEnum):
    ORANGE = "Orange"
    RED = "Red"


@dataclass(frozen=True)
class BrakingDistancePoint:
    road_type: RoadType
    braking_type: BrakingType
    velocity_kph: float
    distance_m: float


@dataclass(frozen=True)
class BrakingDistanceTable:
    points: tuple[BrakingDistancePoint, ...]

    @classmethod
    def from_csv(cls, path: str | Path) -> "BrakingDistanceTable":
        with Path(path).open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = {"RoadType", "BrakingType", "Velocity", "Distance_m"}
            fieldnames = set(reader.fieldnames or [])
            missing_columns = required_columns - fieldnames
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValueError(f"Braking-distance CSV is missing required columns: {missing}.")

            points = tuple(_parse_point(row, row_number=index) for index, row in enumerate(reader, start=2))

        if not points:
            raise ValueError("Braking-distance table must contain at least one row.")

        return cls(points)

    def deceleration_for(
        self,
        road_type: RoadType,
        braking_type: BrakingType,
        velocity_kph: float,
    ) -> float | None:
        """Return negative acceleration in m/s^2, or None when lookup is out of range."""
        if velocity_kph <= 0:
            return 0.0

        rows = sorted(
            (
                point
                for point in self.points
                if point.road_type == road_type and point.braking_type == braking_type
            ),
            key=lambda point: point.velocity_kph,
        )
        if not rows:
            return None

        if velocity_kph < rows[0].velocity_kph or velocity_kph > rows[-1].velocity_kph:
            return None

        for point in rows:
            if point.velocity_kph == velocity_kph:
                return _deceleration_from_distance(velocity_kph, point.distance_m)

        for left, right in zip(rows, rows[1:]):
            if left.velocity_kph <= velocity_kph <= right.velocity_kph:
                ratio = (velocity_kph - left.velocity_kph) / (right.velocity_kph - left.velocity_kph)
                distance_m = left.distance_m + ratio * (right.distance_m - left.distance_m)
                return _deceleration_from_distance(velocity_kph, distance_m)

        return None


def _parse_point(row: dict[str, str], row_number: int) -> BrakingDistancePoint:
    try:
        road_type = RoadType(row["RoadType"].strip())
    except ValueError as error:
        valid_values = ", ".join(road.value for road in RoadType)
        raise ValueError(f"Row {row_number}: RoadType must be one of: {valid_values}.") from error

    try:
        braking_type = BrakingType(row["BrakingType"].strip())
    except ValueError as error:
        valid_values = ", ".join(braking.value for braking in BrakingType)
        raise ValueError(f"Row {row_number}: BrakingType must be one of: {valid_values}.") from error

    try:
        velocity_kph = float(row["Velocity"])
        distance_m = float(row["Distance_m"])
    except ValueError as error:
        raise ValueError(f"Row {row_number}: Velocity and Distance_m must be numeric.") from error

    if velocity_kph < 0:
        raise ValueError(f"Row {row_number}: Velocity cannot be negative.")
    if distance_m <= 0:
        raise ValueError(f"Row {row_number}: Distance_m must be positive.")

    return BrakingDistancePoint(
        road_type=road_type,
        braking_type=braking_type,
        velocity_kph=velocity_kph,
        distance_m=distance_m,
    )


def _deceleration_from_distance(velocity_kph: float, distance_m: float) -> float:
    velocity_mps = kph_to_mps(velocity_kph)
    return -(velocity_mps**2) / (2.0 * distance_m)
