"""
Tests for FlowPilot Local Meeting Notetaker Engine
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.meeting_notetaker import MeetingNotetakerEngine, MeetingSession

class TestMeetingNotetaker(unittest.TestCase):
    def setUp(self):
        self.received_segments = []
        self.engine = MeetingNotetakerEngine(on_segment=lambda seg: self.received_segments.append(seg))

    def test_start_and_stop_session(self):
        sess = self.engine.start_meeting("Architecture Sync")
        self.assertTrue(self.engine.is_recording)
        self.assertEqual(sess.title, "Architecture Sync")

        # Add segments
        self.engine.add_transcript_segment("Good morning team, let's begin the review.")
        self.engine.add_transcript_segment("We decided to proceed with the local SQLite architecture.")
        self.engine.add_transcript_segment("I will prepare the deployment scripts by tomorrow morning.")

        stopped = self.engine.stop_meeting()
        self.assertFalse(self.engine.is_recording)
        self.assertEqual(len(stopped.segments), 3)
        self.assertEqual(len(self.received_segments), 3)

    def test_extractive_summary_action_items_and_decisions(self):
        self.engine.start_meeting("Planning Meeting")
        self.engine.add_transcript_segment("First point of discussion.")
        self.engine.add_transcript_segment("We agreed to release version 3.2 this week.")
        self.engine.add_transcript_segment("I will update the documentation for the companion studio.")
        self.engine.add_transcript_segment("Make sure to check the egress test suite before pushing.")

        summary = self.engine.generate_summary()
        self.assertNotIn("Architecture", summary["title"])
        self.assertIn("Planning", summary["title"])
        self.assertGreater(len(summary["decisions"]), 0)
        self.assertTrue(any("agreed to release" in dec.lower() for dec in summary["decisions"]))

        self.assertGreater(len(summary["action_items"]), 0)
        self.assertTrue(any("i will update" in act.lower() for act in summary["action_items"]))
        self.assertTrue(any("make sure to check" in act.lower() for act in summary["action_items"]))

    def test_empty_meeting_handling(self):
        sess = self.engine.start_meeting("Empty")
        summary = self.engine.generate_summary()
        self.assertEqual(summary["action_items"], [])
        self.assertEqual(summary["decisions"], [])

if __name__ == "__main__":
    unittest.main()
