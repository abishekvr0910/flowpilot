import os
import sys
import time
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.text_injector import TextInjector
from engine.writing_intelligence import AutomaticCorrectionDetector
from engine.context_processor import ContextProcessor

class TestCaretAndCorrectionsIntegration(unittest.TestCase):
    def test_text_injector_caret_safety(self):
        """Verify get_caret_surrounding_text returns safely on non-existent or 0 HWND."""
        prec, foll = TextInjector.get_caret_surrounding_text(0)
        self.assertIsNone(prec)
        self.assertIsNone(foll)

        prec, foll = TextInjector.get_caret_surrounding_text(99999999)
        self.assertIsNone(prec)
        self.assertIsNone(foll)

    def test_correction_detector_persistence(self):
        """Verify AutomaticCorrectionDetector saves and restores state from JSON disk storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persist_file = os.path.join(tmpdir, "corrections.json")
            detector1 = AutomaticCorrectionDetector(
                required_occurrences=2,
                window_days=7,
                storage_path=persist_file
            )

            # Record two occurrences
            now = time.time()
            detector1.record_occurrence("docker", "Docker", timestamp=now - 100)
            detector1.record_occurrence("docker", "Docker", timestamp=now)

            self.assertTrue(os.path.exists(persist_file))
            suggestions1 = detector1.get_pending_suggestions(now=now)
            self.assertEqual(len(suggestions1), 1)
            self.assertEqual(suggestions1[0]["heard"], "docker")
            self.assertEqual(suggestions1[0]["corrected"], "Docker")

            # Create new detector instance pointing to same file
            detector2 = AutomaticCorrectionDetector(
                required_occurrences=2,
                window_days=7,
                storage_path=persist_file
            )
            suggestions2 = detector2.get_pending_suggestions(now=now)
            self.assertEqual(len(suggestions2), 1)
            self.assertEqual(suggestions2[0]["heard"], "docker")
            self.assertEqual(suggestions2[0]["corrected"], "Docker")

            # Dismiss and verify persistence of dismissal
            detector2.dismiss_suggestion("docker", "Docker", cooldown_days=7, now=now)
            self.assertEqual(len(detector2.get_pending_suggestions(now=now)), 0)

            detector3 = AutomaticCorrectionDetector(
                required_occurrences=2,
                window_days=7,
                storage_path=persist_file
            )
            self.assertEqual(len(detector3.get_pending_suggestions(now=now)), 0)

    def test_context_processor_caret_flow(self):
        """Verify ContextProcessor passes caret context to local engine correctly."""
        config = {"active_tone_mode": "professional"}
        processor = ContextProcessor(config)

        # Mid-sentence continuation
        res = processor.process(
            "we should proceed with deployment",
            preceding_text="I really think ",
            following_text=" next week."
        )
        # Should start lower-case and not add a duplicate terminal period before ' next week.'
        self.assertTrue(res.startswith("we should proceed"))
        self.assertFalse(res.endswith("."))

if __name__ == "__main__":
    unittest.main()
