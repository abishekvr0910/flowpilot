"""Call detection and discard must leave dictation ready for another session."""
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.media_presence import CaptureSessionMonitor
from engine.orchestrator import FlowOrchestrator, AppState
from engine.session import DictationSession, SessionState


class SmartPauseTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "Windows audio interfaces required")
    def test_capture_enumeration_uses_shipped_pycaw_interfaces(self):
        from pycaw.pycaw import AudioUtilities
        enumerator = MagicMock()
        endpoints = enumerator.EnumAudioEndpoints.return_value
        endpoints.GetCount.return_value = 1
        manager = endpoints.Item.return_value.Activate.return_value.QueryInterface.return_value
        sessions = manager.GetSessionEnumerator.return_value
        sessions.GetCount.return_value = 1
        control = sessions.GetSession.return_value
        control.QueryInterface.return_value.GetProcessId.return_value = 5678
        control.GetState.return_value = 1
        with patch.object(AudioUtilities, "GetDeviceEnumerator", return_value=enumerator), \
             patch("comtypes.CoInitialize"), patch("comtypes.CoUninitialize"), \
             patch("psutil.Process") as process:
            process.return_value.name.return_value = "teams.exe"
            probe = CaptureSessionMonitor()
            self.assertTrue(probe.is_call_active())
            enumerator.EnumAudioEndpoints.assert_called_with(1, 1)
            control.GetState.return_value = 0
            self.assertFalse(probe.is_call_active())
            control.GetState.return_value = 1
            process.return_value.name.return_value = "flowpilot.exe"
            self.assertFalse(probe.is_call_active())
            self.assertFalse(probe._unavailable)

    def make_orchestrator(self):
        orchestrator = FlowOrchestrator.__new__(FlowOrchestrator)
        orchestrator._state_lock = threading.RLock()
        orchestrator._capture_watchdog_stop = threading.Event()
        orchestrator._call_watchdog_stop = orchestrator._capture_watchdog_stop
        orchestrator._current_session = DictationSession()
        orchestrator._current_session.transition_to(SessionState.RECORDING)
        orchestrator.state = AppState.RECORDING
        orchestrator._auto_stop_timer = MagicMock()
        orchestrator.recorder = MagicMock()
        orchestrator.recorder.is_recording = True
        orchestrator.ducker = MagicMock()
        orchestrator.feedback = MagicMock()
        orchestrator._notify = MagicMock()
        orchestrator._apply_pending_model_switch_if_idle = MagicMock()
        orchestrator.stt = MagicMock()
        return orchestrator

    def test_active_call_discards_recording_and_returns_to_idle(self):
        orchestrator = self.make_orchestrator()
        session = orchestrator._current_session
        with patch("engine.orchestrator.time.sleep"), \
             patch("engine.text_injector.TextInjector.inject_with_status") as inject:
            self.assertTrue(orchestrator._discard_recording_for_call(session))
            inject.assert_not_called()
        self.assertEqual(orchestrator.state, AppState.IDLE)
        self.assertTrue(session.is_cancelled)
        self.assertEqual(session.cancel_reason, "call_detected")
        self.assertTrue(orchestrator._capture_watchdog_stop.is_set())
        orchestrator.recorder.stop_recording.assert_called_once()
        orchestrator.stt.transcribe.assert_not_called()
        self.assertTrue(orchestrator._notify.call_args.args[1]["paused_by_call"])

    def test_stale_call_watchdog_cannot_cancel_new_session(self):
        orchestrator = self.make_orchestrator()
        self.assertFalse(orchestrator._discard_recording_for_call(DictationSession()))
        self.assertFalse(orchestrator._current_session.is_cancelled)
        orchestrator.recorder.stop_recording.assert_not_called()

    def test_stop_releases_capture_monitor(self):
        orchestrator = self.make_orchestrator()
        orchestrator.capture_monitor = MagicMock()
        orchestrator.stop_hotkey_listener = MagicMock()
        orchestrator.text_repair = None
        orchestrator.stop()
        orchestrator.capture_monitor.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
