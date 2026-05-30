import unittest
import tempfile
from pathlib import Path

from convoysim.parameters import load_parameters_csv


EXAMPLE_PARAMETERS = Path("Inputs/stage_a_example_inputs/parameters.csv")


class ParametersTest(unittest.TestCase):
    def test_loads_example_parameters(self) -> None:
        loaded = load_parameters_csv(EXAMPLE_PARAMETERS)

        self.assertEqual(loaded.initial_conditions.truck_length_m, 9.0)
        self.assertEqual(loaded.simulation_parameters.max_velocity_kph, 20.0)
        self.assertEqual(loaded.simulation_parameters.start_moving_gap_m, 8.0)
        self.assertEqual(loaded.simulation_parameters.orange_braking_mode, 0)
        self.assertEqual(loaded.simulation_parameters.time_headway_s, 3.0)
        self.assertEqual(loaded.simulation_parameters.emergency_deceleration_mps2, 6.0)
        self.assertFalse(loaded.simulation_parameters.trucks_communicating)
        self.assertFalse(loaded.simulation_parameters.resume_by_distance)

    def test_resume_by_distance_defaults_to_no_when_missing(self) -> None:
        rows = EXAMPLE_PARAMETERS.read_text(encoding="utf-8").splitlines()
        without_resume = "\n".join(row for row in rows if not row.startswith("Resume by distance,")) + "\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "parameters.csv"
            path.write_text(without_resume, encoding="utf-8")

            loaded = load_parameters_csv(path)

        self.assertFalse(loaded.simulation_parameters.resume_by_distance)


if __name__ == "__main__":
    unittest.main()
