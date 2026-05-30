"""Small physical motion helpers for constant-acceleration simulation steps."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotionState:
    position_m: float
    velocity_mps: float


def step_motion(
    state: MotionState,
    acceleration_mps2: float,
    dt_s: float,
    max_velocity_mps: float | None = None,
) -> MotionState:
    if dt_s <= 0:
        raise ValueError("Simulation time step must be positive.")

    if state.velocity_mps < 0:
        raise ValueError("Velocity cannot be negative.")

    if acceleration_mps2 < 0 and state.velocity_mps + acceleration_mps2 * dt_s < 0:
        stopping_time_s = state.velocity_mps / abs(acceleration_mps2)
        distance_m = state.velocity_mps * stopping_time_s + 0.5 * acceleration_mps2 * stopping_time_s**2
        return MotionState(position_m=state.position_m + distance_m, velocity_mps=0.0)

    next_velocity_mps = state.velocity_mps + acceleration_mps2 * dt_s
    if max_velocity_mps is not None and next_velocity_mps > max_velocity_mps:
        if acceleration_mps2 > 0:
            time_to_limit_s = (max_velocity_mps - state.velocity_mps) / acceleration_mps2
            time_to_limit_s = max(0.0, min(dt_s, time_to_limit_s))
            distance_before_limit_m = (
                state.velocity_mps * time_to_limit_s + 0.5 * acceleration_mps2 * time_to_limit_s**2
            )
            distance_at_limit_m = max_velocity_mps * (dt_s - time_to_limit_s)
            return MotionState(
                position_m=state.position_m + distance_before_limit_m + distance_at_limit_m,
                velocity_mps=max_velocity_mps,
            )
        next_velocity_mps = max_velocity_mps

    distance_m = state.velocity_mps * dt_s + 0.5 * acceleration_mps2 * dt_s**2
    return MotionState(position_m=state.position_m + distance_m, velocity_mps=next_velocity_mps)
