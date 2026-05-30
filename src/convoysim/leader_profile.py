"""Leader velocity profile parsing, validation, and interpolation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv


@dataclass(frozen=True, order=True)
class ProfilePoint:
    time_s: float
    velocity_kph: float


@dataclass(frozen=True)
class LeaderProfile:
    points: tuple[ProfilePoint, ...]

    @classmethod
    def from_points(cls, points: list[ProfilePoint]) -> "LeaderProfile":
        if not points:
            raise ValueError("Leader profile must contain at least one point.")

        ordered = tuple(sorted(points, key=lambda point: point.time_s))
        for previous, current in zip(ordered, ordered[1:]):
            if current.time_s <= previous.time_s:
                raise ValueError("Leader profile times must be strictly increasing.")

        if ordered[0].time_s != 0:
            raise ValueError("Leader profile must start at Time_s = 0.")

        if any(point.velocity_kph < 0 for point in ordered):
            raise ValueError("Leader profile velocities cannot be negative.")

        return cls(ordered)

    @classmethod
    def from_csv(cls, path: str | Path) -> "LeaderProfile":
        with Path(path).open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            required_columns = {"Time_s", "Velocity_kph"}
            if set(reader.fieldnames or []) < required_columns:
                raise ValueError("Leader profile CSV must include Time_s and Velocity_kph columns.")

            points = [
                ProfilePoint(time_s=float(row["Time_s"]), velocity_kph=float(row["Velocity_kph"]))
                for row in reader
            ]

        return cls.from_points(points)

    @property
    def end_time_s(self) -> float:
        return self.points[-1].time_s

    def velocity_at(self, time_s: float) -> float:
        if time_s <= self.points[0].time_s:
            return self.points[0].velocity_kph

        if time_s >= self.points[-1].time_s:
            return self.points[-1].velocity_kph

        for left, right in zip(self.points, self.points[1:]):
            if left.time_s <= time_s <= right.time_s:
                span_s = right.time_s - left.time_s
                ratio = (time_s - left.time_s) / span_s
                return left.velocity_kph + ratio * (right.velocity_kph - left.velocity_kph)

        raise RuntimeError("Unable to interpolate leader profile velocity.")

    def segment_accelerations_kph_per_s(self) -> tuple[float, ...]:
        return tuple(
            (right.velocity_kph - left.velocity_kph) / (right.time_s - left.time_s)
            for left, right in zip(self.points, self.points[1:])
        )
