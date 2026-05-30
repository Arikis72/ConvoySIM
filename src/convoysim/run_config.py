"""Run configuration and timestamped output naming."""

from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DEFAULT_CONFIG_PATH = Path("convoysim.ini")
DEFAULT_PARAMETERS = "Inputs/stage_a_example_inputs/parameters.csv"
DEFAULT_SCENARIO = "Inputs/stage_a_example_inputs/scenario_timeline.csv"
DEFAULT_BRAKING = "Inputs/stage_a_example_inputs/braking_distance_table.csv"
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_BULK_SCENARIOS_DIR = "Bulk_Scenarios"
DEFAULT_COST_FUNCTION_WEIGHTS = "CostFunctionWeights.csv"


@dataclass(frozen=True)
class RunFilePaths:
    output_path: Path
    log_path: Path
    charts_path: Path


@dataclass(frozen=True)
class StageARunConfig:
    parameters_path: str = DEFAULT_PARAMETERS
    scenario_path: str = DEFAULT_SCENARIO
    braking_table_path: str = DEFAULT_BRAKING
    output_path: str = ""
    log_path: str = ""
    charts_path: str = ""
    cost_function_weights_path: str = DEFAULT_COST_FUNCTION_WEIGHTS
    show_gap_chart: bool = True
    show_velocity_chart: bool = True
    show_truck2_velocity: bool = True
    show_truck3_velocity: bool = True
    playback_speed: float = 1.0
    visualization_divider_position: int = 360
    bulk_scenarios_dir: str = DEFAULT_BULK_SCENARIOS_DIR


def timestamped_stage_a_paths(
    scenario_path: str | Path,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    run_time: datetime | None = None,
) -> RunFilePaths:
    timestamp = (run_time or datetime.now()).strftime("%d%m%y_%H%M")
    scenario_stem = Path(scenario_path).stem
    output_directory = Path(output_dir)
    return RunFilePaths(
        output_path=output_directory / f"{scenario_stem}_output_{timestamp}.csv",
        log_path=output_directory / f"{scenario_stem}_log_{timestamp}.csv",
        charts_path=output_directory / f"{scenario_stem}_charts_{timestamp}.html",
    )


def load_stage_a_run_config(path: str | Path = DEFAULT_CONFIG_PATH) -> StageARunConfig:
    config_path = Path(path)
    if not config_path.exists():
        generated_paths = timestamped_stage_a_paths(DEFAULT_SCENARIO)
        return StageARunConfig(
            output_path=str(generated_paths.output_path),
            log_path=str(generated_paths.log_path),
            charts_path=str(generated_paths.charts_path),
        )

    parser = ConfigParser()
    parser.read(config_path, encoding="utf-8")
    section = parser["stage_a"] if parser.has_section("stage_a") else {}
    generated_paths = timestamped_stage_a_paths(section.get("scenario_path", DEFAULT_SCENARIO))
    return StageARunConfig(
        parameters_path=section.get("parameters_path", DEFAULT_PARAMETERS),
        scenario_path=section.get("scenario_path", DEFAULT_SCENARIO),
        braking_table_path=section.get("braking_table_path", DEFAULT_BRAKING),
        output_path=section.get("output_path") or str(generated_paths.output_path),
        log_path=section.get("log_path") or str(generated_paths.log_path),
        charts_path=section.get("charts_path") or str(generated_paths.charts_path),
        cost_function_weights_path=section.get("cost_function_weights_path", DEFAULT_COST_FUNCTION_WEIGHTS),
        show_gap_chart=_config_bool(section, "show_gap_chart", True),
        show_velocity_chart=_config_bool(section, "show_velocity_chart", True),
        show_truck2_velocity=_config_bool(section, "show_truck2_velocity", True),
        show_truck3_velocity=_config_bool(section, "show_truck3_velocity", True),
        playback_speed=_clamp(_config_float(section, "playback_speed", 1.0), 0.3, 2.0),
        visualization_divider_position=int(_clamp(_config_float(section, "visualization_divider_position", 360.0), 280.0, 620.0)),
        bulk_scenarios_dir=section.get("bulk_scenarios_dir", DEFAULT_BULK_SCENARIOS_DIR),
    )


def save_stage_a_run_config(config: StageARunConfig, path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    parser = ConfigParser()
    parser["stage_a"] = {
        "parameters_path": config.parameters_path,
        "scenario_path": config.scenario_path,
        "braking_table_path": config.braking_table_path,
        "output_path": config.output_path,
        "log_path": config.log_path,
        "charts_path": config.charts_path,
        "cost_function_weights_path": config.cost_function_weights_path,
        "show_gap_chart": _yes_no(config.show_gap_chart),
        "show_velocity_chart": _yes_no(config.show_velocity_chart),
        "show_truck2_velocity": _yes_no(config.show_truck2_velocity),
        "show_truck3_velocity": _yes_no(config.show_truck3_velocity),
        "playback_speed": f"{config.playback_speed:.1f}",
        "visualization_divider_position": str(config.visualization_divider_position),
        "bulk_scenarios_dir": config.bulk_scenarios_dir,
    }
    config_path = Path(path)
    with config_path.open("w", encoding="utf-8") as config_file:
        parser.write(config_file)


def output_dir_from_previous_path(path: str | Path) -> Path:
    previous_path = Path(path)
    return previous_path.parent if str(previous_path.parent) not in {"", "."} else Path(DEFAULT_OUTPUT_DIR)


def _config_bool(section: object, key: str, default: bool) -> bool:
    value = section.get(key, "") if hasattr(section, "get") else ""
    if str(value).strip().lower() in {"yes", "true", "1", "on"}:
        return True
    if str(value).strip().lower() in {"no", "false", "0", "off"}:
        return False
    return default


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _config_float(section: object, key: str, default: float) -> float:
    value = section.get(key, "") if hasattr(section, "get") else ""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
