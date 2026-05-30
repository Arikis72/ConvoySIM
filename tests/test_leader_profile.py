import tempfile
import unittest
from pathlib import Path

from convoysim.leader_profile import LeaderProfile, ProfilePoint
from convoysim.models import SimulationParameters
from convoysim.validation import validate_leader_profile


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


class LeaderProfileTest(unittest.TestCase):
    def test_interpolates_velocity_between_profile_points(self) -> None:
        profile = LeaderProfile.from_points(
            [
                ProfilePoint(time_s=0.0, velocity_kph=0.0),
                ProfilePoint(time_s=10.0, velocity_kph=20.0),
            ]
        )

        self.assertEqual(profile.velocity_at(5.0), 10.0)

    def test_rejects_profile_that_does_not_start_at_zero(self) -> None:
        with self.assertRaises(ValueError):
            LeaderProfile.from_points([ProfilePoint(time_s=1.0, velocity_kph=0.0)])

    def test_loads_leader_profile_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leader.csv"
            path.write_text("Time_s,Velocity_kph\n0,0\n2,10\n", encoding="utf-8")

            profile = LeaderProfile.from_csv(path)

        self.assertEqual(profile.velocity_at(1.0), 5.0)

    def test_reports_impossible_leader_acceleration(self) -> None:
        profile = LeaderProfile.from_points(
            [
                ProfilePoint(time_s=0.0, velocity_kph=0.0),
                ProfilePoint(time_s=1.0, velocity_kph=20.0),
            ]
        )

        result = validate_leader_profile(profile, valid_parameters())

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].field, "leader_profile.segment_1")


if __name__ == "__main__":
    unittest.main()
