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

    def test_two_track_audio_separation_and_speaker_tagging(self):
        engine = MeetingNotetakerEngine(two_track_mode=True)
        sess = engine.start_meeting("Dual-Track Product Sync")
        self.assertTrue(engine.two_track_mode)

        seg_local = engine.add_transcript_segment("Can everyone hear the latest status update?", speaker="Local")
        seg_remote = engine.add_transcript_segment("Yes, we are seeing 25% faster turnaround on the sprint.", speaker="Remote")

        self.assertEqual(seg_local["speaker"], "Local")
        self.assertEqual(seg_remote["speaker"], "Remote")

        transcript = sess.full_transcript
        self.assertIn("[Local] Can everyone hear", transcript)
        self.assertIn("[Remote] Yes, we are seeing", transcript)

        stopped = engine.stop_meeting()
        self.assertIsNotNone(stopped)
        self.assertIn("[Local]", stopped.full_transcript)
        self.assertIn("[Remote]", stopped.full_transcript)

    def test_crosstalk_bleed_suppression(self):
        import numpy as np
        from engine.meeting_notetaker import MeetingAudioWorker

        delivered = []
        worker = MeetingAudioWorker(
            on_chunk_ready=lambda chunk, speaker="Local": delivered.append((speaker, len(chunk))),
            two_track=True
        )
        worker._running = True

        # Simulate 15 frames (1.5s) of remote speech (amplitude 0.20)
        # with weak acoustic speaker bleed into local mic (amplitude 0.03).
        # Bleed suppression must suppress the local channel from triggering false speech.
        frames = 1600
        for _ in range(15):
            stereo_block = np.zeros((frames, 2), dtype=np.float32)
            stereo_block[:, 0] = 0.03  # Weak bleed into mic
            stereo_block[:, 1] = 0.20  # Loud remote speech
            worker.process_audio_frame(stereo_block)

        # Then 15 frames of silence to trigger silence flush
        silence = np.zeros((frames, 2), dtype=np.float32)
        for _ in range(15):
            worker.process_audio_frame(silence)

        worker.stop()

        # Remote chunk should be captured
        remote_chunks = [item for item in delivered if item[0] == "Remote"]
        self.assertGreater(len(remote_chunks), 0)

        # Local channel should have been suppressed and NOT produced a speech chunk
        local_chunks = [item for item in delivered if item[0] == "Local"]
        self.assertEqual(len(local_chunks), 0)

    def test_meeting_vault_isolation(self):
        import json
        from engine.meeting_notetaker import MEETINGS_DIR

        engine = MeetingNotetakerEngine()
        sess = engine.start_meeting("Vault Isolation Test")
        engine.add_transcript_segment("Confidential planning session data.")
        stopped = engine.stop_meeting()

        saved_file = MEETINGS_DIR / f"{stopped.meeting_id}.json"
        self.assertTrue(saved_file.exists())

        with open(saved_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["meeting_id"], stopped.meeting_id)
        self.assertIn("Confidential planning", data["transcript"])

        # Clean up
        engine.delete_meeting(stopped.meeting_id)
        self.assertFalse(saved_file.exists())

if __name__ == "__main__":
    unittest.main()
