import tempfile
import unittest
from pathlib import Path

from convoysim.braking import BrakingDistanceTable
from convoysim.charts import _follower_stroke_width, write_stage_a_charts_html
from convoysim.parameters import load_parameters_csv
from convoysim.scenario_timeline import ScenarioTimeline
from convoysim.simulation import run_basic_simulation


EXAMPLE_PARAMETERS = Path("Inputs/stage_a_example_inputs/parameters.csv")
EXAMPLE_TIMELINE = Path("Inputs/stage_a_example_inputs/scenario_timeline.csv")
EXAMPLE_BRAKING_TABLE = Path("Inputs/stage_a_example_inputs/braking_distance_table.csv")


class ChartsTest(unittest.TestCase):
    def test_writes_stage_a_charts_html(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)
        timeline = ScenarioTimeline.from_csv(EXAMPLE_TIMELINE)
        braking_table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)
        result = run_basic_simulation(loaded.initial_conditions, loaded.simulation_parameters, timeline, braking_table)

        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "stage_a_charts.html"
            write_stage_a_charts_html(result, loaded.simulation_parameters, output_path)
            html = output_path.read_text(encoding="utf-8")

        self.assertIn("Gap vs Time", html)
        self.assertIn("Velocity vs Time", html)
        self.assertIn("chart-layout", html)
        self.assertIn("<strong>Legend</strong>", html)
        self.assertIn("Time (s)", html)
        self.assertIn("Gap (m)", html)
        self.assertIn("Velocity (kph)", html)
        self.assertIn("stroke=\"#eee\"", html)
        self.assertIn("Dotted segment = image identification lost", html)
        self.assertIn("Orange braking = bold data line", html)
        self.assertIn("Red braking = double-bold data line", html)
        self.assertIn("stroke-width=\"4\"", html)
        self.assertIn("stroke=\"#1f77b4\"", html)
        self.assertIn("stroke=\"#ff7f0e\"", html)
        self.assertIn("stroke-dasharray=\"5,4\"", html)
        self.assertIn("<svg", html)

    def test_follower_stroke_width_reflects_braking_level(self) -> None:
        self.assertEqual(_follower_stroke_width("FOLLOWING_MATCHING_SPEED", "Match front-truck speed"), 2)
        self.assertEqual(_follower_stroke_width("FOLLOWING_ORANGE_DECEL", "Orange deceleration"), 4)
        self.assertEqual(_follower_stroke_width("FOLLOWING_RED_BRAKING_TO_STOP", "Red brake to stop"), 6)


if __name__ == "__main__":
    unittest.main()
