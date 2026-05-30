"""Unit conversion helpers used by the simulation core."""

KPH_TO_MPS = 1000.0 / 3600.0
MPS_TO_KPH = 3600.0 / 1000.0
MS_TO_SECONDS = 1.0 / 1000.0


def kph_to_mps(value_kph: float) -> float:
    return value_kph * KPH_TO_MPS


def mps_to_kph(value_mps: float) -> float:
    return value_mps * MPS_TO_KPH


def ms_to_seconds(value_ms: float) -> float:
    return value_ms * MS_TO_SECONDS
