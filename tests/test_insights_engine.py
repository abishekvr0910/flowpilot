"""
Tests for FlowPilot Local Productivity Insights Engine
"""

import sys
import unittest
import tempfile
import os
from pathlib import Path
from datetime import date, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.insights_engine import InsightsEngine

class TestInsightsEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_file = Path(self.temp_dir.name) / "insights.json"
        self.engine = InsightsEngine(storage_path=self.storage_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_metrics(self):
        m = self.engine.get_metrics()
        self.assertEqual(m["total_words"], 0)
        self.assertEqual(m["total_words_formatted"], "0")
        self.assertEqual(m["streak"], 0)
        self.assertEqual(m["total_utterances"], 0)
        self.assertFalse(m["has_data"])
        self.assertEqual(m["wpm"], 0)

    def test_first_session_seeds_wpm_and_drives_has_data(self):
        m = self.engine.record_dictation("one two three four five six seven eight nine ten", duration_sec=4.0)
        self.assertEqual(m["wpm"], 150)
        self.assertEqual(m["streak"], 1)
        self.assertTrue(m["has_data"])

    def test_second_session_smooths_without_fake_prior(self):
        self.engine.record_dictation("one two three four five six seven eight nine ten", duration_sec=4.0)  # 150 wpm
        m = self.engine.record_dictation("one two three four five six seven eight nine ten", duration_sec=2.0)  # 300 wpm
        self.assertEqual(m["wpm"], int(round(0.75 * 150 + 0.25 * 300)))

    def test_record_dictation_calculates_words_and_wpm(self):
        text = "This is a quick test of the local transcription system."  # 10 words
        # 4 seconds -> (10 / 4) * 60 = 150 WPM
        m = self.engine.record_dictation(text, duration_sec=4.0, target_app="Code.exe")

        self.assertEqual(m["total_words"], 10)
        self.assertEqual(m["total_utterances"], 1)
        self.assertEqual(m["wpm"], 150)
        self.assertGreater(m["time_saved_minutes"], 0.0)

        # Check persistence to disk
        self.assertTrue(self.storage_file.exists())
        loaded = InsightsEngine(storage_path=self.storage_file)
        m_loaded = loaded.get_metrics()
        self.assertEqual(m_loaded["total_words"], 10)
        self.assertEqual(m_loaded["total_utterances"], 1)

    def test_formatted_words_thousands(self):
        # 1200 words
        large_text = "word " * 1200
        m = self.engine.record_dictation(large_text, duration_sec=300.0)
        self.assertEqual(m["total_words_formatted"], "1.2K")

    def test_daily_streak_increments_consecutive_days(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        self.engine._data["last_active_date"] = yesterday
        self.engine._data["daily_streak"] = 3
        self.engine._save()

        m = self.engine.record_dictation("Recording today session", duration_sec=2.0)
        self.assertEqual(m["streak"], 4)

    def test_daily_streak_resets_after_gap(self):
        three_days_ago = (date.today() - timedelta(days=3)).isoformat()
        self.engine._data["last_active_date"] = three_days_ago
        self.engine._data["daily_streak"] = 5
        self.engine._save()

        m = self.engine.record_dictation("Recording session after gap", duration_sec=2.0)
        self.assertEqual(m["streak"], 1)

    def test_reset_metrics(self):
        self.engine.record_dictation("Hello world", duration_sec=1.0)
        self.assertGreater(self.engine.get_metrics()["total_words"], 0)
        self.engine.reset_metrics()
        self.assertEqual(self.engine.get_metrics()["total_words"], 0)

if __name__ == "__main__":
    unittest.main()
