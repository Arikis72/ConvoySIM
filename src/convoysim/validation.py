"""Validation helpers for simulation inputs."""

from __future__ import annotations

from dataclasses import dataclass

from convoysim.leader_profile import LeaderProfile
from convoysim.models import InitialConditions, SimulationParameters
from convoysim.units import KPH_TO_MPS


@dataclass(frozen=True)
class ValidationMessage:
    field: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[ValidationMessage, ...]
    warnings: tuple[ValidationMessage, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_initial_conditions(initial: InitialConditions) -> ValidationResult:
    errors: list[ValidationMessage] = []

    if initial.truck_length_m <= 0:
        errors.append(ValidationMessage("truck_length_m", "Truck length must be positive."))

    if initial.initial_gap_12_m <= 0:
        errors.append(ValidationMessage("initial_gap_12_m", "Initial gap #2 must be positive."))

    if initial.initial_gap_23_m <= 0:
        errors.append(ValidationMessage("initial_gap_23_m", "Initial gap #3 must be positive."))

    for field_name in ("truck1_velocity_kph", "truck2_velocity_kph", "truck3_velocity_kph"):
        if getattr(initial, field_name) < 0:
            errors.append(ValidationMessage(field_name, "Initial velocity cannot be negative."))

    return ValidationResult(errors=tuple(errors))


def validate_parameters(parameters: SimulationParameters) -> ValidationResult:
    errors: list[ValidationMessage] = []
    warnings: list[ValidationMessage] = []

    positive_fields = (
        "max_velocity_kph",
        "max_acceleration_mps2",
        "max_red_deceleration_mps2",
        "minimum_gap_m",
        "maximum_gap_m",
        "red_distance_m",
        "orange_distance_m",
        "time_headway_s",
        "emergency_deceleration_mps2",
        "image_identification_loss_distance_m",
        "image_identification_resume_distance_m",
        "simulation_time_step_s",
        "output_resolution_s",
    )
    for field_name in positive_fields:
        if getattr(parameters, field_name) <= 0:
            errors.append(ValidationMessage(field_name, "Value must be positive."))

    if parameters.minimum_gap_m >= parameters.maximum_gap_m:
        errors.append(ValidationMessage("minimum_gap_m", "Minimum gap must be less than maximum gap."))

    if parameters.red_distance_m >= parameters.orange_distance_m:
        errors.append(ValidationMessage("red_distance_m", "Red distance must be less than orange distance."))

    if parameters.orange_braking_mode not in {0, 1}:
        errors.append(ValidationMessage("orange_braking_mode", "Orange braking mode must be 0 (fixed) or 1 (TimeHeadway)."))

    if parameters.image_identification_resume_distance_m > parameters.image_identification_loss_distance_m:
        errors.append(
            ValidationMessage(
                "image_identification_resume_distance_m",
                "Resume distance must be less than or equal to image-identification loss distance.",
            )
        )

    if not 0 <= parameters.communication_reliability_percent <= 100:
        errors.append(
            ValidationMessage("communication_reliability_percent", "Communication reliability must be 0-100 percent.")
        )

    if parameters.output_resolution_s < parameters.simulation_time_step_s:
        errors.append(
            ValidationMessage("output_resolution_s", "Output resolution must be equal to or larger than time step.")
        )

    if parameters.maximum_gap_m > parameters.image_identification_loss_distance_m:
        warnings.append(
            ValidationMessage(
                "maximum_gap_m",
                "Maximum allowed gap is greater than image-identification loss distance.",
            )
        )

    return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))


def validate_leader_profile(profile: LeaderProfile, parameters: SimulationParameters) -> ValidationResult:
    errors: list[ValidationMessage] = []

    max_delta_mps2 = parameters.max_acceleration_mps2
    # Allow emergency deceleration rate: FORT events in the scenario produce it by design
    max_brake_mps2 = max(parameters.max_red_deceleration_mps2, parameters.emergency_deceleration_mps2)
    _EPS = 1e-6  # floating-point guard for exact boundary values

    for index, (left, right) in enumerate(zip(profile.points, profile.points[1:]), start=1):
        dt_s = right.time_s - left.time_s
        acceleration_mps2 = (right.velocity_kph - left.velocity_kph) * KPH_TO_MPS / dt_s

        if acceleration_mps2 > max_delta_mps2 + _EPS:
            errors.append(
                ValidationMessage(
                    f"leader_profile.segment_{index}",
                    "Leader profile acceleration exceeds max acceleration.",
                )
            )

        if acceleration_mps2 < -(max_brake_mps2 + _EPS):
            errors.append(
                ValidationMessage(
                    f"leader_profile.segment_{index}",
                    "Leader profile deceleration exceeds max red deceleration.",
                )
            )

    return ValidationResult(errors=tuple(errors))
