import unittest

from convoysim.models import InitialConditions, SimulationParameters
from convoysim.scenario import build_initial_geometry
from convoysim.validation import validate_initial_conditions, validate_parameters


def valid_parameters() -> SimulationParameters:
    return SimulationParameters(
        max_velocity_kph=50.0,
        max_acceleration_mps2=2.0,
        max_red_deceleration_mps2=4.0,
        minimum_gap_m=2.0,
        maximum_gap_m=30.0,
        red_distance_m=4.0,
        orange_distance_m=8.0,
        start_moving_identification_delay_ms=500.0,
        distance_identification_delay_ms=100.0,
        image_identification_loss_distance_m=50.0,
        image_identification_resume_distance_m=40.0,
        under_loss_following_velocity_kph=5.0,
        under_loss_leading_velocity_kph=5.0,
        trucks_communicating=False,
    )


class ValidationAndGeometryTest(unittest.TestCase):
    def test_builds_initial_geometry_from_origin_at_truck3_front(self) -> None:
        geometry = build_initial_geometry(
            InitialConditions(truck_length_m=6.0, initial_gap_12_m=10.0, initial_gap_23_m=12.0)
        )

        self.assertEqual(geometry.truck3_front_m, 0.0)
        self.assertEqual(geometry.truck2_front_m, 18.0)
        self.assertEqual(geometry.truck1_front_m, 34.0)
        self.assertEqual(geometry.truck2_gap_m, 10.0)
        self.assertEqual(geometry.truck3_gap_m, 12.0)

    def test_rejects_invalid_initial_gap(self) -> None:
        result = validate_initial_conditions(
            InitialConditions(truck_length_m=6.0, initial_gap_12_m=0.0, initial_gap_23_m=12.0)
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].field, "initial_gap_12_m")

    def test_warns_when_maximum_gap_exceeds_identification_loss_distance(self) -> None:
        parameters = valid_parameters()
        parameters = SimulationParameters(
            **{
                **parameters.__dict__,
                "maximum_gap_m": 60.0,
            }
        )

        result = validate_parameters(parameters)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.warnings[0].field, "maximum_gap_m")


if __name__ == "__main__":
    unittest.main()
