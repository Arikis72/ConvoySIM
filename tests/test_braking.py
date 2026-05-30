import unittest
from pathlib import Path

from convoysim.braking import BrakingDistanceTable, BrakingType
from convoysim.models import RoadType
from convoysim.units import kph_to_mps


EXAMPLE_BRAKING_TABLE = Path("Inputs/stage_a_example_inputs/braking_distance_table.csv")


class BrakingDistanceTableTest(unittest.TestCase):
    def test_loads_example_braking_distance_table(self) -> None:
        table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)

        self.assertGreaterEqual(len(table.points), 24)
        self.assertIsNotNone(table.deceleration_for(RoadType.ASPHALT, BrakingType.ORANGE, 0.3))

    def test_calculates_deceleration_from_exact_distance(self) -> None:
        table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)

        acceleration = table.deceleration_for(RoadType.ASPHALT, BrakingType.RED, 10.0)

        expected = -(kph_to_mps(10.0) ** 2) / (2.0 * 3.0)
        self.assertAlmostEqual(acceleration, expected)

    def test_interpolates_braking_distance_between_velocity_rows(self) -> None:
        table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)

        acceleration = table.deceleration_for(RoadType.ASPHALT, BrakingType.ORANGE, 12.5)

        expected_distance_m = 7.5
        expected = -(kph_to_mps(12.5) ** 2) / (2.0 * expected_distance_m)
        self.assertAlmostEqual(acceleration, expected)

    def test_returns_none_outside_velocity_range(self) -> None:
        table = BrakingDistanceTable.from_csv(EXAMPLE_BRAKING_TABLE)

        self.assertIsNone(table.deceleration_for(RoadType.ASPHALT, BrakingType.RED, 30.0))


if __name__ == "__main__":
    unittest.main()
