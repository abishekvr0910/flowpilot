"""
FlowPilot Recovery Feedback and Shortcut Unit Tests
Feature 30: Transparent Dictation Recovery & Visual Feedback

Tests the recovery actions:
- re_copy_last() (Shift+Alt+X / Alt+Shift+X)
- re_inject_last() (Shift+Alt+Z / Alt+Shift+Z)
Verifying truthful state transitions, UI notifications, and recording concurrency guards.
"""

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Enforce headless and isolated test environment
os.environ["FLOWPILOT_HEADLESS"] = "1"
os.environ["FLOWPILOT_NO_POPUP"] = "1"

from engine.orchestrator import FlowOrchestrator, AppState
from engine.text_injector import TextInjector, InjectionResult, InjectionStatus


class TestRecoveryFeedback(unittest.TestCase):
    def setUp(self):
        TextInjector.last_injected_text = ""
        TextInjector.last_target_hwnd = 0

    def test_re_copy_last_empty_buffer(self):
        """re_copy_last returns False and emits ERROR notification when no dictation exists."""
        notifications = []
        orch = FlowOrchestrator()
        orch.last_dictation = {}
        orch.on_state_change = lambda p: notifications.append(p)

        with patch.object(TextInjector, "re_copy_last", return_value=False):
            res = orch.re_copy_last()

        self.assertFalse(res)
        self.assertTrue(any(
            n.get("app_state") == AppState.ERROR and "No previous dictation" in n.get("notice", "")
            for n in notifications
        ))

    def test_re_copy_last_with_text(self):
        """re_copy_last returns True and emits IDLE notification with text notice when dictation exists."""
        notifications = []
        orch = FlowOrchestrator()
        orch.last_dictation = {"formatted_text": "Meeting scheduled for 3 PM"}
        orch.on_state_change = lambda p: notifications.append(p)

        with patch.object(TextInjector, "re_copy_last", return_value=True):
            res = orch.re_copy_last()

        self.assertTrue(res)
        self.assertTrue(any(
            n.get("notice") == "Copied last dictation to clipboard"
            for n in notifications
        ))

    def test_re_inject_last_empty_buffer(self):
        """re_inject_last returns ERROR InjectionResult and notifies when recovery buffer is empty."""
        notifications = []
        orch = FlowOrchestrator()
        orch.last_dictation = {}
        orch.on_state_change = lambda p: notifications.append(p)

        res = orch.re_inject_last()
        self.assertEqual(res.status, InjectionStatus.ERROR)
        self.assertIn("recovery buffer", res.error_message)
        self.assertTrue(any(
            n.get("app_state") == AppState.ERROR and "No previous dictation" in n.get("notice", "")
            for n in notifications
        ))

    def test_re_inject_last_postponed_during_active_recording(self):
        """re_inject_last safely refuses to execute while user is actively recording."""
        notifications = []
        orch = FlowOrchestrator()
        orch.state = AppState.RECORDING
        orch.last_dictation = {"formatted_text": "Prior text"}
        orch.on_state_change = lambda p: notifications.append(p)

        res = orch.re_inject_last()
        self.assertEqual(res.status, InjectionStatus.ERROR)
        self.assertIn("while dictation is in progress", res.error_message)
        self.assertEqual(orch.state, AppState.RECORDING)
        self.assertTrue(any(
            "Dictation in progress" in n.get("notice", "")
            for n in notifications
        ))

    def test_re_inject_last_success_and_auto_reset(self):
        """re_inject_last performs injection, transitions to SUCCESS, and resets to IDLE."""
        notifications = []
        orch = FlowOrchestrator()
        orch.state = AppState.IDLE
        orch.last_dictation = {"formatted_text": "Prior dictation text", "injection_status": "SENT_UNVERIFIED"}
        orch.on_state_change = lambda p: notifications.append(p)

        mock_res = InjectionResult(
            status=InjectionStatus.CONFIRMED_INSERTED,
            chars_sent=20,
            target_class="NotepadTextBox"
        )

        with patch.object(TextInjector, "inject_last", return_value=mock_res):
            with patch("engine.window_inspector.WindowInspector.get_active_window_info", return_value={"hwnd": 1234}):
                res = orch.re_inject_last()

        self.assertEqual(res.status, InjectionStatus.CONFIRMED_INSERTED)
        self.assertEqual(orch.last_dictation.get("prior_injection_status"), "SENT_UNVERIFIED")
        self.assertEqual(orch.last_dictation.get("injection_status"), InjectionStatus.CONFIRMED_INSERTED.value)

        # Check SUCCESS notification
        success_notifications = [n for n in notifications if n.get("app_state") == AppState.SUCCESS]
        self.assertTrue(len(success_notifications) > 0)
        self.assertEqual(success_notifications[0].get("notice"), "Re-inserted & confirmed")
        self.assertTrue(success_notifications[0].get("injection_confirmed"))

        # Wait for auto-reset to IDLE
        time.sleep(1.0)
        self.assertEqual(orch.state, AppState.IDLE)


if __name__ == "__main__":
    unittest.main()
