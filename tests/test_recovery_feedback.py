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
import threading
import tempfile
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
_test_profile = tempfile.TemporaryDirectory(prefix="flowpilot-recovery-test-")
os.environ["FLOWPILOT_CONFIG_DIR"] = _test_profile.name
os.environ["FLOWPILOT_CONFIG_FILE"] = str(Path(_test_profile.name) / "config.json")

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

    def test_copy_during_recording_preserves_recording_feedback(self):
        orch = FlowOrchestrator()
        orch.state = AppState.RECORDING
        TextInjector.last_injected_text = "Earlier dictation"
        notifications = []
        orch.on_state_change = notifications.append
        with patch.object(TextInjector, "re_copy_last", return_value=True):
            self.assertTrue(orch.re_copy_last())
        self.assertEqual(orch.state, AppState.RECORDING)
        self.assertEqual(notifications[-1]["app_state"], AppState.RECORDING)
        self.assertTrue(notifications[-1]["recovery_action"])

    def test_copy_after_unverified_paste_never_claims_confirmation(self):
        orch = FlowOrchestrator()
        orch.state = AppState.SUCCESS
        orch.last_dictation = {"injection_status": InjectionStatus.SENT_UNVERIFIED.value}
        TextInjector.last_injected_text = "Maybe sent"
        notifications = []
        orch.on_state_change = notifications.append
        with patch.object(TextInjector, "re_copy_last", return_value=True):
            self.assertTrue(orch.re_copy_last())
        self.assertEqual(notifications[-1]["app_state"], AppState.IDLE)
        self.assertTrue(notifications[-1]["recovery_action"])

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
            n.get("app_state") == AppState.RECORDING and "Dictation in progress" in n.get("notice", "")
            for n in notifications
        ))

    def test_re_inject_last_refuses_later_pipeline_states(self):
        for state in (AppState.VALIDATING, AppState.INSERTING_TEXT):
            with self.subTest(state=state):
                orch = FlowOrchestrator()
                orch.state = state
                TextInjector.last_injected_text = "Prior text"
                with patch.object(TextInjector, "inject_last") as inject:
                    result = orch.re_inject_last()
                self.assertEqual(result.status, InjectionStatus.ERROR)
                self.assertEqual(orch.state, state)
                inject.assert_not_called()

    def test_failed_recovery_never_reports_success(self):
        orch = FlowOrchestrator()
        orch.last_dictation = {"formatted_text": "Prior text", "injection_status": "SENT_UNVERIFIED"}
        TextInjector.last_injected_text = "Prior text"
        notifications = []
        orch.on_state_change = notifications.append
        failed = InjectionResult(
            status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
            error_message="Target focus unavailable; text kept for recovery.",
            recovery_available=True,
        )
        with patch.object(TextInjector, "inject_last", return_value=failed), \
             patch("engine.window_inspector.WindowInspector.get_active_window_info", return_value={"hwnd": 0}):
            result = orch.re_inject_last()
        self.assertIs(result, failed)
        self.assertEqual(orch.state, AppState.IDLE)
        self.assertFalse(any(n.get("app_state") == AppState.SUCCESS for n in notifications))
        self.assertEqual(notifications[-1]["injection_status"], InjectionStatus.FAILED_RECOVERY_AVAILABLE.value)
        self.assertTrue(notifications[-1]["recovery_action"])

    def test_recovery_dispatch_blocks_new_dictation_start(self):
        orch = FlowOrchestrator()
        TextInjector.last_injected_text = "Prior text"
        entered = threading.Event()
        release = threading.Event()
        started = threading.Event()

        def delayed_inject(**_kwargs):
            entered.set()
            self.assertTrue(release.wait(2.0))
            return InjectionResult(status=InjectionStatus.SENT_UNVERIFIED, chars_sent=10)

        with patch.object(TextInjector, "inject_last", side_effect=delayed_inject), \
             patch("engine.window_inspector.WindowInspector.get_active_window_info", return_value={"hwnd": 1234}), \
             patch.object(orch, "start_dictation", side_effect=lambda **_kwargs: started.set()):
            recovery = threading.Thread(target=orch.re_inject_last)
            toggle = threading.Thread(target=orch.toggle_dictation)
            recovery.start()
            try:
                self.assertTrue(entered.wait(2.0))
                toggle.start()
                self.assertFalse(started.wait(0.1))
            finally:
                release.set()
                recovery.join(2.0)
                if toggle.ident is not None:
                    toggle.join(2.0)
            self.assertFalse(recovery.is_alive())
            self.assertFalse(toggle.is_alive())
            self.assertTrue(started.is_set())

    def test_recovery_success_does_not_duplicate_dashboard_text(self):
        from desktop_app import FlowPilotApp

        app = object.__new__(FlowPilotApp)
        app.hud = MagicMock()
        app.tray = MagicMock()
        app.dashboard = MagicMock()
        app.dashboard.scratchpad_view.editor.hasFocus.return_value = True
        app.dashboard.notetaker_view.engine.is_recording = True

        app._handle_state_update({
            "state": "pasted", "text": "Already in the target",
            "injection_confirmed": True, "recovery_action": True,
        })
        app.dashboard.scratchpad_view.insert_text.assert_not_called()
        app.dashboard.notetaker_view.append_segment.assert_not_called()
        app.dashboard.history_view.reload_history.assert_not_called()

    def test_earlier_recovery_timer_does_not_clear_later_feedback(self):
        orch = FlowOrchestrator()
        TextInjector.last_injected_text = "Prior text"
        result = InjectionResult(status=InjectionStatus.CONFIRMED_INSERTED, chars_sent=10)
        with patch.object(TextInjector, "inject_last", return_value=result), \
             patch("engine.window_inspector.WindowInspector.get_active_window_info", return_value={"hwnd": 1234}):
            orch.re_inject_last()
            time.sleep(0.4)
            orch.re_inject_last()
        time.sleep(0.45)
        self.assertEqual(orch.state, AppState.SUCCESS)
        time.sleep(0.45)
        self.assertEqual(orch.state, AppState.IDLE)

    def test_re_inject_last_success_and_auto_reset(self):
        """re_inject_last performs injection, transitions to SUCCESS, and resets to IDLE."""
        notifications = []
        orch = FlowOrchestrator()
        orch.state = AppState.IDLE
        orch.last_dictation = {"formatted_text": "Prior dictation text", "injection_status": "SENT_UNVERIFIED"}
        TextInjector.last_injected_text = "Prior dictation text"
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


    def test_hotkey_alias_normalization(self):
        """Verify that Alt+Shift+Z/X and Shift+Alt+Z/X resolve to identical Win32 modifiers and VK codes."""
        from engine.hotkey_service import parse_hotkey_string, MOD_ALT, MOD_SHIFT
        mods_z1, vk_z1 = parse_hotkey_string("Alt+Shift+Z")
        mods_z2, vk_z2 = parse_hotkey_string("Shift+Alt+Z")
        self.assertEqual((mods_z1, vk_z1), (mods_z2, vk_z2))
        self.assertEqual(mods_z1, MOD_ALT | MOD_SHIFT)
        self.assertEqual(vk_z1, ord("Z"))

        mods_x1, vk_x1 = parse_hotkey_string("Alt+Shift+X")
        mods_x2, vk_x2 = parse_hotkey_string("Shift+Alt+X")
        self.assertEqual((mods_x1, vk_x1), (mods_x2, vk_x2))
        self.assertEqual(mods_x1, MOD_ALT | MOD_SHIFT)
        self.assertEqual(vk_x1, ord("X"))


if __name__ == "__main__":
    unittest.main()
