import tempfile
import unittest
from pathlib import Path

from convoysim.scenario_timeline import ImageEvent, ScenarioTimeline


EXAMPLE_TIMELINE = Path("Inputs/stage_a_example_inputs/scenario_timeline.csv")


class ScenarioTimelineTest(unittest.TestCase):
    def test_loads_example_scenario_timeline(self) -> None:
        timeline = ScenarioTimeline.from_csv(EXAMPLE_TIMELINE)

        self.assertGreaterEqual(len(timeline.rows), 1)
        self.assertEqual(timeline.rows[0].time_s, 0.0)
        self.assertEqual(timeline.end_time_s, 60.0)

    def test_extracts_leader_profile_from_non_empty_velocity_rows(self) -> None:
        timeline = ScenarioTimeline.from_csv(EXAMPLE_TIMELINE)
        profile = timeline.leader_profile()

        self.assertEqual(profile.velocity_at(1.0), 2.5)
        self.assertEqual(profile.velocity_at(22.0), 7.5)
        self.assertEqual(profile.end_time_s, 60.0)

    def test_extracts_truck_image_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario_timeline.csv"
            path.write_text(
                "Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes\n"
                "0,0,,,,\n"
                "18,,,Loss,,\n"
                "22,,,Resume,,\n"
                "30,,,,Loss,\n"
                "34,,,,Resume,\n"
                "44,,,Loss,,\n"
                "50,,,,Loss,\n",
                encoding="utf-8",
            )
            timeline = ScenarioTimeline.from_csv(path)

        truck2_events = timeline.truck2_image_events()
        truck3_events = timeline.truck3_image_events()

        self.assertEqual([(event.time_s, event.event) for event in truck2_events], [(18.0, ImageEvent.LOSS), (22.0, ImageEvent.RESUME), (44.0, ImageEvent.LOSS)])
        self.assertEqual([(event.time_s, event.event) for event in truck3_events], [(30.0, ImageEvent.LOSS), (34.0, ImageEvent.RESUME), (50.0, ImageEvent.LOSS)])

    def test_rejects_non_increasing_times(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario_timeline.csv"
            path.write_text(
                "Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes\n"
                "0,0,,,,\n"
                "0.0,5,,,,\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "strictly increasing"):
                ScenarioTimeline.from_csv(path)

    def test_rejects_unknown_image_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario_timeline.csv"
            path.write_text(
                "Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes\n"
                "0,0,,,,\n"
                "5,,,Blink,,\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Truck2_Image_Event"):
                ScenarioTimeline.from_csv(path)

    def test_accepts_fort_activated_event_on_truck1(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario_timeline.csv"
            path.write_text(
                "Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes\n"
                "0,0,,,,\n"
                "5,,FORT activated,,,\n",
                encoding="utf-8",
            )

            timeline = ScenarioTimeline.from_csv(path)

        self.assertEqual(timeline.truck1_events()[0].event, ImageEvent.FORT_ACTIVATED)

    def test_parses_new_format_with_metadata_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario_timeline.csv"
            path.write_text(
                "Description: Test scenario\n"
                "Initial gaps:,5,20,,,\n"
                "Time_s,Truck1_Velocity_kph,Truck1_Event,Truck2_Image_Event,Truck3_Image_Event,Notes\n"
                "0,0,,,,\n"
                "10,60,FORT activated,,,Test FORT event\n"
                "20,60,,Loss,,\n",
                encoding="utf-8",
            )

            timeline = ScenarioTimeline.from_csv(path)

        self.assertEqual(len(timeline.rows), 3)
        self.assertEqual(timeline.rows[0].time_s, 0.0)
        self.assertEqual(timeline.rows[1].truck1_event, ImageEvent.FORT_ACTIVATED)
        self.assertEqual(timeline.rows[2].truck2_image_event, ImageEvent.LOSS)


if __name__ == "__main__":
    unittest.main()
