"""Core data structures for convoy simulation inputs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RoadType(StrEnum):
    GRAVEL = "Gravel"
    ASPHALT = "Asphalt"
    DUST_ROAD = "Dust road"


@dataclass(frozen=True)
class InitialConditions:
    truck_length_m: float
    initial_gap_12_m: float
    initial_gap_23_m: float
    truck1_velocity_kph: float = 0.0
    truck2_velocity_kph: float = 0.0
    truck3_velocity_kph: float = 0.0

    def initial_front_positions(self) -> tuple[float, float, float]:
        """Return front bumper positions for Truck #1, #2, and #3."""
        truck3_front_m = 0.0
        truck2_front_m = self.truck_length_m + self.initial_gap_23_m
        truck1_front_m = truck2_front_m + self.truck_length_m + self.initial_gap_12_m
        return truck1_front_m, truck2_front_m, truck3_front_m


@dataclass(frozen=True)
class SimulationParameters:
    max_velocity_kph: float
    max_acceleration_mps2: float
    max_red_deceleration_mps2: float
    minimum_gap_m: float
    maximum_gap_m: float
    red_distance_m: float
    orange_distance_m: float
    start_moving_identification_delay_ms: float
    distance_identification_delay_ms: float
    image_identification_loss_distance_m: float
    image_identification_resume_distance_m: float
    under_loss_following_velocity_kph: float
    under_loss_leading_velocity_kph: float
    trucks_communicating: bool
    orange_braking_mode: int = 0
    time_headway_s: float = 3.0
    emergency_deceleration_mps2: float = 6.0
    resume_by_distance: bool = False
    communication_latency_ms: float = 200.0
    communication_reliability_percent: float = 100.0
    convoy_target_speed_kph: float = 10.0
    target_gap_m: float = 10.0
    road_type: RoadType = RoadType.ASPHALT
    orange_deceleration_mps2: float = 1.0
    green_acceleration_mps2: float = 1.0
    optimal_acceleration_mps2: float = 1.0
    simulation_time_step_s: float = 0.1
    output_resolution_s: float = 0.1
    start_moving_gap_m: float = 10.0
