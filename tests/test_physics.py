import unittest

from convoysim.physics import MotionState, step_motion


class PhysicsTest(unittest.TestCase):
    def test_steps_constant_acceleration_motion(self) -> None:
        state = step_motion(MotionState(position_m=0.0, velocity_mps=2.0), acceleration_mps2=1.0, dt_s=3.0)

        self.assertEqual(state.position_m, 10.5)
        self.assertEqual(state.velocity_mps, 5.0)

    def test_clamps_velocity_at_zero_and_uses_stopping_distance(self) -> None:
        state = step_motion(MotionState(position_m=0.0, velocity_mps=2.0), acceleration_mps2=-2.0, dt_s=3.0)

        self.assertEqual(state.position_m, 1.0)
        self.assertEqual(state.velocity_mps, 0.0)

    def test_respects_max_velocity_limit(self) -> None:
        state = step_motion(
            MotionState(position_m=0.0, velocity_mps=2.0),
            acceleration_mps2=2.0,
            dt_s=2.0,
            max_velocity_mps=4.0,
        )

        self.assertEqual(state.position_m, 7.0)
        self.assertEqual(state.velocity_mps, 4.0)


if __name__ == "__main__":
    unittest.main()
