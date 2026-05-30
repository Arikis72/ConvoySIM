from datetime import datetime
import tempfile
import unittest
from pathlib import Path

from convoysim.run_config import (
    StageARunConfig,
    load_stage_a_run_config,
    save_stage_a_run_config,
    timestamped_stage_a_paths,
)


class RunConfigTest(unittest.TestCase):
    def test_timestamped_stage_a_paths_use_scenario_file_stem_and_timestamp(self) -> None:
        paths = timestamped_stage_a_paths(
            "inputs/my_scenario.csv",
            "outputs",
            datetime(2026, 5, 23, 3, 47),
        )

        self.assertEqual(paths.output_path, Path("outputs/my_scenario_output_230526_0347.csv"))
        self.assertEqual(paths.log_path, Path("outputs/my_scenario_log_230526_0347.csv"))
        self.assertEqual(paths.charts_path, Path("outputs/my_scenario_charts_230526_0347.html"))

    def test_saves_and_loads_stage_a_run_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "convoysim.ini"
            expected = StageARunConfig(
                parameters_path="params.csv",
                scenario_path="scenario.csv",
                braking_table_path="braking.csv",
                output_path="outputs/scenario_output_230526_0347.csv",
                log_path="outputs/scenario_log_230526_0347.csv",
                charts_path="outputs/scenario_charts_230526_0347.html",
                cost_function_weights_path="weights.csv",
                show_gap_chart=False,
                show_velocity_chart=True,
                playback_speed=0.3,
                visualization_divider_position=512,
                bulk_scenarios_dir="Bulk_Custom",
            )

            save_stage_a_run_config(expected, config_path)
            loaded = load_stage_a_run_config(config_path)

        self.assertEqual(loaded, expected)

    def test_clamps_visualization_divider_position_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "convoysim.ini"
            config_path.write_text(
                "[stage_a]\n"
                "visualization_divider_position = 900\n",
                encoding="utf-8",
            )

            loaded = load_stage_a_run_config(config_path)

        self.assertEqual(loaded.visualization_divider_position, 620)

    def test_clamps_small_visualization_divider_position_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "convoysim.ini"
            config_path.write_text(
                "[stage_a]\n"
                "visualization_divider_position = 0\n",
                encoding="utf-8",
            )

            loaded = load_stage_a_run_config(config_path)

        self.assertEqual(loaded.visualization_divider_position, 280)


if __name__ == "__main__":
    unittest.main()
