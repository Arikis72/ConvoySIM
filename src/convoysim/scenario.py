"""Minimal Stage A scenario helpers.

The detailed follower state machine is intentionally left for the next step.
This module establishes the initial convoy geometry required by Stage A.
"""

from __future__ import annotations

from dataclasses import dataclass

from convoysim.models import InitialConditions


@dataclass(frozen=True)
class ConvoyGeometry:
    truck1_front_m: float
    truck2_front_m: float
    truck3_front_m: float
    truck2_gap_m: float
    truck3_gap_m: float


def build_initial_geometry(initial: InitialConditions) -> ConvoyGeometry:
    truck1_front_m, truck2_front_m, truck3_front_m = initial.initial_front_positions()
    return ConvoyGeometry(
        truck1_front_m=truck1_front_m,
        truck2_front_m=truck2_front_m,
        truck3_front_m=truck3_front_m,
        truck2_gap_m=initial.initial_gap_12_m,
        truck3_gap_m=initial.initial_gap_23_m,
    )
