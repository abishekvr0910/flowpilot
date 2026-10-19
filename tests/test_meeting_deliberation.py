"""
FlowPilot Guided AI Meeting Deliberation & Intelligence Test Suite
Validates:
1. "What Did I Miss?" Live Catch-Up Recap
2. Decision Weighing Matrix (Deliberative Pros/Cons & Trade-Offs)
3. Risk & Blocker Radar with Severity Tagging
4. Agentic Action Dispatcher (Follow-up email draft & Task Cards)
5. Granular Retention Policy Enforcement (7, 30, 90, 365 days & Indefinite)
6. Dual Audio / Translation Mode Configuration
7. Insights Engine Meeting Analytics Integration
"""

import sys
import time
import json
import tempfile
import shutil
import unittest
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.meeting_deliberation import (
    MeetingDeliberationEngine,
    DeliberationTopic,
    RiskItem,
    CatchUpRecap,
    RetentionPolicy
)
from engine.meeting_notetaker import MeetingSession, MeetingNotetakerEngine, ActionItem
from engine.insights_engine import InsightsEngine


class TestMeetingDeliberation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="fp_test_deliberation_")
        self.deliberation = MeetingDeliberationEngine(storage_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_session(self) -> MeetingSession:
        sess = MeetingSession(title="Q4 Architecture & Security Sync", template="general")
        now = time.time()
        # Simulate 15 minutes of discussion across 8 segments
        segments = [
            {"time": "00:01:00", "text": "Welcome everyone to the quarterly architecture review.", "timestamp": now - 840},
            {"time": "00:03:30", "text": "We are evaluating PostgreSQL versus SQLite for the local client storage.", "timestamp": now - 690},
            {"time": "00:05:00", "text": "PostgreSQL provides concurrent writers and robust indexing, which is a major advantage.", "timestamp": now - 600},
            {"time": "00:06:15", "text": "However, running a separate PostgreSQL service introduces heavy installation overhead and RAM usage.", "timestamp": now - 525},
            {"time": "00:08:00", "text": "SQLite is embedded, zero-dependency, and incredibly fast, but multi-process writes could cause locks.", "timestamp": now - 420},
            {"time": "00:10:00", "text": "We decided to adopt SQLite with WAL mode to achieve single-file zero-egress simplicity.", "timestamp": now - 300},
            {"time": "00:12:00", "text": "A critical security compliance risk is our unpinned third-party library dependencies.", "timestamp": now - 180},
            {"time": "00:13:30", "text": "I will pin all pip dependencies and configure automated SHA-256 integrity verification.", "timestamp": now - 90},
            {"time": "00:14:45", "text": "Make sure to update the developer documentation before the Friday cutoff.", "timestamp": now - 15},
        ]
        sess.segments = segments
        sess.stop_time = now
        return sess

    # -----------------------------------------------------------------------
    # 1. "What Did I Miss?" Live Catch-Up
    # -----------------------------------------------------------------------
    def test_what_did_i_miss_catchup(self):
        sess = self._create_sample_session()
        # Query catchup for the last 5 minutes (300 seconds)
        recap = self.deliberation.generate_catchup(sess, window_seconds=300)

        self.assertIsInstance(recap, CatchUpRecap)
        self.assertGreater(len(recap.recent_points), 0)
        self.assertTrue(any("security" in p.lower() or "sqlite" in p.lower() for p in recap.recent_points))
        self.assertIn("Q4 Architecture", recap.session_title)
        self.assertTrue(len(recap.active_summary) > 10)

    # -----------------------------------------------------------------------
    # 2. Decision Weighing Matrix ("Weighing with AI")
    # -----------------------------------------------------------------------
    def test_decision_weighing_matrix(self):
        sess = self._create_sample_session()
        topics = self.deliberation.extract_weighing_matrix(sess)

        self.assertIsInstance(topics, list)
        self.assertGreater(len(topics), 0)

        # Check topic structure
        first = topics[0]
        self.assertIsInstance(first, DeliberationTopic)
        self.assertTrue(len(first.pros_agreements) > 0 or len(first.cons_concerns) > 0)
        self.assertIn(first.status, ["CONSENSUS_REACHED", "OPEN_DEBATE", "TABLED"])

    # -----------------------------------------------------------------------
    # 3. Risk & Blocker Radar
    # -----------------------------------------------------------------------
    def test_risk_and_blocker_radar(self):
        sess = self._create_sample_session()
        risks = self.deliberation.extract_risk_radar(sess)

        self.assertIsInstance(risks, list)
        self.assertGreater(len(risks), 0)

        sec_risk = next((r for r in risks if "security" in r.text.lower() or "compliance" in r.text.lower()), None)
        self.assertIsNotNone(sec_risk)
        self.assertIn(sec_risk.severity, ["HIGH", "MEDIUM", "LOW"])
        self.assertTrue(len(sec_risk.mitigation_hint) > 5)

    # -----------------------------------------------------------------------
    # 4. Agentic Action Dispatcher (Email & Task Cards)
    # -----------------------------------------------------------------------
    def test_followup_email_draft_generation(self):
        sess = self._create_sample_session()
        email = self.deliberation.generate_followup_email(sess, attendees=["Alice", "Bob", "Charlie"])

        self.assertIn("Subject:", email)
        self.assertIn("Q4 Architecture & Security Sync", email)
        self.assertIn("Executive Summary", email)
        self.assertIn("Key Decisions", email)
        self.assertIn("Action Items", email)
        self.assertIn("Alice", email)

    def test_task_cards_generation(self):
        sess = self._create_sample_session()
        cards = self.deliberation.generate_task_cards(sess)

        self.assertIsInstance(cards, list)
        self.assertGreater(len(cards), 0)
        self.assertIn("title", cards[0])
        self.assertIn("markdown_body", cards[0])
        self.assertIn("priority", cards[0])

    # -----------------------------------------------------------------------
    # 5. Granular Retention Policy Enforcement
    # -----------------------------------------------------------------------
    def test_retention_policy_enforcement(self):
        # Create a mock meeting directory with old and new meetings
        m_dir = Path(self.temp_dir) / "meetings"
        m_dir.mkdir(parents=True, exist_ok=True)

        old_file = m_dir / "meeting_old.json"
        recent_file = m_dir / "meeting_recent.json"

        # Old file: 40 days ago
        old_time = time.time() - (40 * 86400)
        old_data = {"meeting_id": "meeting_old", "title": "Old Meeting", "start_time": old_time}
        old_file.write_text(json.dumps(old_data), encoding="utf-8")

        # Recent file: 2 days ago
        recent_time = time.time() - (2 * 86400)
        recent_data = {"meeting_id": "meeting_recent", "title": "Recent Meeting", "start_time": recent_time}
        recent_file.write_text(json.dumps(recent_data), encoding="utf-8")

        # Apply 30-day retention
        purged = RetentionPolicy.enforce_retention(m_dir, policy="30_days")
        self.assertIn("meeting_old", purged)
        self.assertFalse(old_file.exists())
        self.assertTrue(recent_file.exists())

        # Test indefinite does not purge anything
        purged_indef = RetentionPolicy.enforce_retention(m_dir, policy="indefinite")
        self.assertEqual(len(purged_indef), 0)
        self.assertTrue(recent_file.exists())

    # -----------------------------------------------------------------------
    # 6. Live Call Translation Mode in MeetingNotetakerEngine
    # -----------------------------------------------------------------------
    def test_notetaker_translation_mode_configuration(self):
        engine = MeetingNotetakerEngine()
        self.assertFalse(engine.translation_mode)
        self.assertEqual(engine.target_language, "en")

        engine.set_translation_mode(True, target_language="en")
        self.assertTrue(engine.translation_mode)
        self.assertEqual(engine.target_language, "en")

        # Disable
        engine.set_translation_mode(False)
        self.assertFalse(engine.translation_mode)

    # -----------------------------------------------------------------------
    # 7. Insights Engine Meeting Analytics Integration
    # -----------------------------------------------------------------------
    def test_insights_engine_meeting_tracking(self):
        ins_path = Path(self.temp_dir) / "insights.json"
        insights = InsightsEngine(storage_path=ins_path)

        metrics_initial = insights.get_metrics()
        self.assertIn("meeting_count", metrics_initial)
        self.assertIn("meeting_minutes", metrics_initial)

        # Record a 30-minute meeting with 4 action items and 2 decisions
        updated = insights.record_meeting(
            duration_minutes=30.0,
            action_items_count=4,
            decisions_count=2
        )

        self.assertEqual(updated["meeting_count"], 1)
        self.assertEqual(updated["meeting_minutes"], 30.0)
        self.assertEqual(updated["meeting_decisions"], 2)
        self.assertEqual(updated["meeting_actions_created"], 4)


if __name__ == "__main__":
    unittest.main()
