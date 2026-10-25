"""Feature 32: Test capture, integrity, local metrics, and model guidance."""

import json
import os
import sys
import tempfile
import atexit
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

_TEST_PROFILE = tempfile.TemporaryDirectory(prefix="flowpilot_pilot_reliability_")
atexit.register(_TEST_PROFILE.cleanup)
os.environ.setdefault("FLOWPILOT_CONFIG_FILE", str(Path(_TEST_PROFILE.name) / "config.json"))
os.environ.setdefault("FLOWPILOT_MUTEX_NAME", f"Global\\FlowPilot_PilotReliability_{os.getpid()}")

from engine.audio_recorder import AudioRecorder
from engine.orchestrator import AppState, FlowOrchestrator
from engine.pilot_telemetry import append_local_event
from engine.session import DictationSession, SessionState
from engine.text_injector import InjectionStatus, TextInjector


_QT_APP = None


def _qt_app():
    # Keep one application alive across both widget tests. Recreating QApplication
    # while Qt wrappers are still being finalized can terminate Python on Windows.
    global _QT_APP
    from PySide6.QtWidgets import QApplication

    if _QT_APP is None:
        _QT_APP = QApplication.instance() or QApplication([])
    return _QT_APP


class PilotReliabilityTests(unittest.TestCase):
    def test_legacy_cloud_settings_are_removed_without_losing_local_choices(self):
        from engine.config import load_config, save_config

        with tempfile.TemporaryDirectory() as temporary:
            config_file = Path(temporary) / "config.json"
            legacy = {
                "engine_mode": "cloud", "cloud_provider": "groq",
                "groq_api_key": "unused-secret", "openai_api_key": "unused-secret",
                "language": "ta", "hotkey": "F9",
            }
            config_file.write_text(json.dumps(legacy), encoding="utf-8")
            with patch("engine.config.get_config_file", return_value=config_file):
                migrated = load_config()
                self.assertEqual(migrated["engine_mode"], "local")
                self.assertEqual(migrated["language"], "ta")
                self.assertEqual(migrated["hotkey"], "F9")
                for key in ("cloud_provider", "groq_api_key", "openai_api_key"):
                    self.assertNotIn(key, migrated)
                self.assertTrue(save_config({**migrated, "groq_api_key": "another-unused-secret"}))
            persisted = config_file.read_text(encoding="utf-8")
            self.assertNotIn("unused-secret", persisted)
            self.assertNotIn("groq_api_key", persisted)

    def test_pilot_metrics_rotate_and_never_write_transcript_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for index in range(35):
                append_local_event({
                    "timestamp": index, "char_count": 20, "target_app": r"C:\private\code.exe",
                    "raw_text": "SECRET_RAW_TRANSCRIPT", "formatted_text": "SECRET_RESULT",
                    "session_id": "fp-sess-private", "injection_confirmed": True,
                }, directory, max_bytes=220, backups=2)
            files = list(directory.glob("dictation_telemetry.log*"))
            self.assertLessEqual(len(files), 3)
            self.assertTrue(all(path.stat().st_size <= 220 for path in files))
            content = "".join(path.read_text(encoding="utf-8") for path in files)
            self.assertNotIn("SECRET", content)
            self.assertNotIn("fp-sess-private", content)
            for line in content.splitlines():
                event = json.loads(line)
                self.assertEqual(event["target_app"], "code.exe")

    def test_elevated_or_unknown_target_refuses_before_clipboard_write(self):
        for integrity in (True, None):
            with self.subTest(integrity=integrity), \
                 patch("engine.text_injector.win32gui.IsWindow", return_value=True), \
                 patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=12345), \
                 patch.object(TextInjector, "_resolve_verified_foreground", return_value=(True, 12345, None)), \
                 patch("engine.text_injector.target_has_higher_integrity", return_value=integrity), \
                 patch.object(TextInjector, "_safe_clipboard_copy") as clipboard_copy, \
                 patch("engine.text_injector.win32api.keybd_event") as key_event:
                result = TextInjector.inject_with_status("recover me", target_hwnd=12345)
                self.assertEqual(result.status, InjectionStatus.FAILED_RECOVERY_AVAILABLE)
                self.assertEqual(TextInjector.last_injected_text, "recover me")
                clipboard_copy.assert_not_called()
                key_event.assert_not_called()

    def test_dispatch_exception_never_auto_retries_and_duplicates_text(self):
        with patch("engine.text_injector.win32gui.IsWindow", return_value=True), \
             patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=12345), \
             patch.object(TextInjector, "_resolve_verified_foreground", return_value=(True, 12345, None)), \
             patch("engine.text_injector.target_has_higher_integrity", return_value=False), \
             patch.object(TextInjector, "_safe_clipboard_copy", return_value=True), \
             patch.object(TextInjector, "_get_target_process_name", return_value="notepad.exe"), \
             patch("engine.text_injector.win32api.keybd_event", side_effect=RuntimeError("driver failed")), \
             patch.object(TextInjector, "inject_unicode_sendinput") as unicode_retry:
            result = TextInjector.inject_with_status(
                "possibly sent", target_hwnd=12345, preserve_clipboard=False,
                verify_confirmation=False,
            )
            self.assertEqual(result.status, InjectionStatus.SENT_UNVERIFIED)
            unicode_retry.assert_not_called()

    def test_audio_callback_error_and_stall_discard_partial_audio(self):
        recorder = AudioRecorder()
        recorder.stream = MagicMock(active=True)
        recorder.is_recording = True
        recorder._recording_started_at = time.monotonic() - 3.0
        recorder._last_callback_at = time.monotonic() - 3.0
        recorder.audio_frames = [np.ones((16000, 1), dtype=np.float32)]
        self.assertIn("stopped delivering audio", recorder.capture_health_error())
        with self.assertRaisesRegex(RuntimeError, "stopped delivering audio"):
            recorder.stop_recording()
        self.assertIsNone(recorder.last_audio_array)
        self.assertEqual(recorder.audio_frames, [])

        recorder.stream = MagicMock(active=True)
        recorder.is_recording = True
        recorder._recording_started_at = time.monotonic()
        recorder._audio_callback(np.zeros((800, 1), dtype=np.float32), 800, None, "input overflow")
        self.assertIn("lost audio", recorder.capture_health_error())
        recorder.close()

    def test_hung_driver_release_is_bounded_and_blocks_new_recording(self):
        recorder = AudioRecorder()
        recorder.STREAM_CLOSE_SECONDS = 0.03
        blocked = threading.Event()
        stream = MagicMock(active=True)
        stream.abort.side_effect = lambda: blocked.wait(0.4)
        recorder.stream = stream
        started = time.monotonic()
        recorder.close()
        self.assertLess(time.monotonic() - started, 0.2)
        self.assertTrue(recorder._stream_cleanup_failed)
        with self.assertRaisesRegex(RuntimeError, "Restart FlowPilot"):
            recorder.start_recording()
        blocked.set()

    def test_failed_driver_close_blocks_reuse(self):
        recorder = AudioRecorder()
        stream = MagicMock(active=True)
        stream.close.side_effect = RuntimeError("USB device vanished")
        recorder.stream = stream
        recorder.close()
        self.assertTrue(recorder._stream_cleanup_failed)
        with self.assertRaisesRegex(RuntimeError, "Restart FlowPilot"):
            recorder.start_recording()

    def test_hung_driver_open_is_bounded_and_late_stream_is_closed(self):
        recorder = AudioRecorder()
        recorder.STREAM_OPEN_SECONDS = 0.03
        blocked = threading.Event()
        stream = MagicMock(active=True)
        stream.start.side_effect = lambda: blocked.wait(0.4)
        with patch("engine.audio_recorder.sd.InputStream", return_value=stream), \
             patch("engine.audio_recorder.sd.query_devices") as query_devices:
            started = time.monotonic()
            with self.assertRaisesRegex(RuntimeError, "Restart FlowPilot"):
                recorder.start_recording()
            self.assertLess(time.monotonic() - started, 0.2)
            self.assertTrue(recorder._stream_cleanup_failed)
            self.assertFalse(recorder.is_recording)
            query_devices.assert_not_called()
            blocked.set()
            deadline = time.monotonic() + 1.0
            while not stream.close.called and time.monotonic() < deadline:
                time.sleep(0.01)
            stream.close.assert_called_once()

    def test_slow_successful_open_starts_stall_clock_after_open(self):
        recorder = AudioRecorder()
        recorder.CAPTURE_STALL_SECONDS = 0.03
        stream = MagicMock(active=True)
        stream.start.side_effect = lambda: time.sleep(0.06)
        with patch("engine.audio_recorder.sd.InputStream", return_value=stream):
            recorder.start_recording()
            self.assertIsNone(recorder.capture_health_error())
            recorder.close()

    def test_capture_watchdog_reports_error_without_injection(self):
        orchestrator = FlowOrchestrator.__new__(FlowOrchestrator)
        orchestrator._state_lock = threading.RLock()
        orchestrator._capture_watchdog_stop = threading.Event()
        orchestrator._auto_stop_timer = None
        orchestrator.recorder = MagicMock()
        orchestrator.recorder.capture_health_error.return_value = "Microphone disconnected"
        orchestrator.ducker = MagicMock()
        orchestrator.feedback = MagicMock()
        orchestrator._notify = MagicMock()
        session = DictationSession()
        session.transition_to(SessionState.RECORDING)
        orchestrator._current_session = session
        orchestrator.state = AppState.RECORDING
        orchestrator.is_processing = False
        orchestrator._start_capture_watchdog(session)
        deadline = time.monotonic() + 1.0
        while orchestrator.state == AppState.RECORDING and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(orchestrator.state, AppState.ERROR)
        self.assertEqual(session.state, SessionState.ERROR)
        while not orchestrator._notify.called and time.monotonic() < deadline:
            time.sleep(0.01)
        orchestrator.recorder.close.assert_called_once()
        self.assertEqual(orchestrator._notify.call_args.args[0], AppState.ERROR)

    def test_indic_language_selection_uses_visible_small_model_guidance(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from ui.settings_dialog import SettingsDialog
        from ui.setup_wizard import SetupWizardDialog

        app = _qt_app()

        def default_input(combo, _config):
            combo.addItem("System default", {"mode": "default"})

        with tempfile.TemporaryDirectory() as model_dir, \
             patch("ui.audio_input_picker.populate_audio_inputs", side_effect=default_input), \
             patch("engine.audio_devices.resolve_audio_input") as resolve, \
             patch("ui.setup_wizard.STTEngine.resolve_model_path", return_value=model_dir), \
             patch("ui.setup_wizard.QMessageBox.warning", side_effect=AssertionError("Bundled model fixture was not found")), \
             patch("ui.setup_wizard.save_config", return_value=True):
            (Path(model_dir) / "model.bin").touch()
            resolve.return_value.device_index = None
            settings = SettingsDialog(
                {"language": "en", "local_model_size": "base", "hotkey": "F9"},
                on_save=lambda _config: True, personalization=MagicMock(),
            )
            settings.combo_lang.setCurrentIndex(settings.combo_lang.findData("ta"))
            self.assertTrue(settings.combo_model.currentText().startswith("small"))
            self.assertIn("real voice check", settings.lbl_model_guidance.text())
            settings.close()

            wizard = SetupWizardDialog(config={"language": "en", "local_model_size": "base"})
            wizard.combo_lang.setCurrentIndex(wizard.combo_lang.findData("ml"))
            self.assertIn("Local small model file found", wizard.lbl_language_model.text())
            wizard._finish_setup()
            self.assertEqual(wizard.config["local_model_size"], "small")
            wizard.close()
        app.processEvents()

    def test_setup_refuses_indic_model_switch_without_local_weights(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from ui.setup_wizard import SetupWizardDialog

        app = _qt_app()
        with tempfile.TemporaryDirectory() as temporary, \
             patch("ui.audio_input_picker.populate_audio_inputs", side_effect=lambda combo, _: combo.addItem("Default", {"mode": "default"})), \
             patch("ui.setup_wizard.STTEngine.resolve_model_path", return_value=temporary), \
             patch("ui.setup_wizard.QMessageBox.warning") as warning, \
             patch("ui.setup_wizard.save_config") as save_config:
            wizard = SetupWizardDialog(config={"language": "en", "local_model_size": "base"})
            wizard.combo_lang.setCurrentIndex(wizard.combo_lang.findData("hi"))
            wizard._finish_setup()
            self.assertNotEqual(wizard.config.get("local_model_size"), "small")
            save_config.assert_not_called()
            warning.assert_called_once()
            wizard.close()
        app.processEvents()


if __name__ == "__main__":
    unittest.main(verbosity=2)
