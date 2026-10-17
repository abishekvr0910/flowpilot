"""
Unit tests for Upgraded FlowPilot Meeting Notetaker Engine & Library Management
"""

import sys
import unittest
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.meeting_notetaker import MeetingNotetakerEngine, MeetingSession, ActionItem, TEMPLATES

class TestMeetingNotetakerV2(unittest.TestCase):
    def setUp(self):
        self.segments = []
        self.levels = []
        self.engine = MeetingNotetakerEngine(
            on_segment=lambda seg: self.segments.append(seg),
            on_audio_level=lambda lvl: self.levels.append(lvl)
        )

    def tearDown(self):
        if self.engine.is_recording:
            self.engine.stop_meeting()

    def test_templates_support(self):
        self.assertIn("general", TEMPLATES)
        self.assertIn("one_on_one", TEMPLATES)
        self.assertIn("standup", TEMPLATES)
        self.assertIn("brainstorming", TEMPLATES)
        self.assertIn("interview", TEMPLATES)

    def test_pause_and_resume(self):
        sess = self.engine.start_meeting(title="Standup Meeting", template="standup")
        self.assertTrue(self.engine.is_recording)
        self.assertFalse(self.engine.is_paused)

        self.engine.pause_meeting()
        self.assertTrue(self.engine.is_paused)

        self.engine.resume_meeting()
        self.assertFalse(self.engine.is_paused)

        stopped = self.engine.stop_meeting()
        self.assertFalse(self.engine.is_recording)
        self.assertEqual(stopped.title, "Standup Meeting")

    def test_library_persistence_and_management(self):
        sess = self.engine.start_meeting(title="Sprint Retro", template="standup")
        self.engine.add_transcript_segment("Team did a great job releasing on Friday.")
        self.engine.add_transcript_segment("We decided to adopt the new component studio.")
        self.engine.add_transcript_segment("I will follow up on the performance benchmarks tomorrow.")

        stopped = self.engine.stop_meeting()
        m_id = stopped.meeting_id

        # Verify listed in saved meetings
        meetings = self.engine.list_saved_meetings()
        self.assertTrue(any(m["meeting_id"] == m_id for m in meetings))

        # Verify load
        loaded = self.engine.load_meeting(m_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["title"], "Sprint Retro")
        self.assertGreater(len(loaded["action_items"]), 0)

        # Verify update
        up_ok = self.engine.update_meeting(m_id, {"title": "Updated Sprint Retro"})
        self.assertTrue(up_ok)
        reloaded = self.engine.load_meeting(m_id)
        self.assertEqual(reloaded["title"], "Updated Sprint Retro")

        # Verify delete
        del_ok = self.engine.delete_meeting(m_id)
        self.assertTrue(del_ok)
        self.assertIsNone(self.engine.load_meeting(m_id))

    def test_markdown_format_report(self):
        sess = self.engine.start_meeting(title="Design Review", template="brainstorming")
        self.engine.add_transcript_segment("Let's brainstorm the companion UI.")
        self.engine.add_transcript_segment("We agreed on the 16x16 pixel editor.")
        self.engine.add_transcript_segment("I will create the retro presets.")

        stopped = self.engine.stop_meeting()
        summary = stopped.summary or self.engine.generate_summary(stopped)

        report = self.engine.format_markdown_report(summary)
        self.assertIn("# 🎙️ Design Review", report)
        self.assertIn("## 📌 Key Decisions", report)
        self.assertIn("## ✅ Action Items & Commitments", report)
        self.assertIn("## 📜 Complete Timestamped Transcript", report)

    def test_action_item_dual_nature(self):
        act = ActionItem("I will test all suites", done=False, id="act_999")
        # String interface
        self.assertTrue(isinstance(act, str))
        self.assertEqual(act.lower(), "i will test all suites")
        # Dict interface
        self.assertEqual(act.get("done"), False)
        self.assertEqual(act.get("id"), "act_999")
        self.assertEqual(act["done"], False)

if __name__ == "__main__":
    unittest.main()
