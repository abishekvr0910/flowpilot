"""
Unit and integration tests for the three user-facing fixes:
1. Chosen microphone actually becomes FlowPilot's input.
2. Dictionary and snippet edits work immediately without restart.
3. 'Paste Last' targets the intended editor safely and refuses blind dispatch into FlowPilot windows.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio_recorder import AudioRecorder
from engine.orchestrator import FlowOrchestrator
from engine.personalization import get_shared_personalization, PersonalizationEngine
from engine.text_injector import TextInjector, InjectionStatus
from engine.hotkey_service import Win32HotkeyService
from ui.setup_wizard import SetupWizardDialog
from PySide6.QtWidgets import QApplication


class TestUserFacingFixes(unittest.TestCase):
    def setUp(self):
        self.personalization = get_shared_personalization()

    def test_microphone_selection_updates_recorder_device(self):
        """Verify that updating audio_device_index in config immediately updates AudioRecorder device."""
        orch = FlowOrchestrator(on_state_change=lambda _: None)
        self.assertEqual(orch.recorder.device, orch.config.get("audio_device_index", orch.config.get("mic_device")))

        created_streams = []
        def fake_input_stream(**kwargs):
            m = MagicMock()
            m.active = True
            m.kwargs = kwargs
            created_streams.append(m)
            return m

        # Test device change using the REAL warmup_stream and mocked sounddevice InputStream
        with patch("engine.audio_recorder.sd.InputStream", side_effect=fake_input_stream):
            orch.recorder.warmup_stream()
            self.assertEqual(len(created_streams), 1)

            # Change device to test index 4 (uses real set_device and real warmup_stream)
            orch.update_config({"audio_device_index": 4})
            self.assertEqual(orch.recorder.device, 4)
            created_streams[0].stop.assert_called()
            created_streams[0].close.assert_called()
            self.assertEqual(len(created_streams), 2)
            self.assertEqual(created_streams[1].kwargs.get("device"), 4)
            created_streams[1].start.assert_called()

            # Change device back to default (None)
            orch.update_config({"audio_device_index": None})
            self.assertIsNone(orch.recorder.device)
            created_streams[1].stop.assert_called()
            created_streams[1].close.assert_called()
            self.assertEqual(len(created_streams), 3)
            self.assertIsNone(created_streams[2].kwargs.get("device"))

    def test_recorder_lock_reentrancy_and_live_switch(self):
        """Verify that set_device does not deadlock when re-entering locks during idle or active recording."""
        import threading
        rec = AudioRecorder(sample_rate=16000)
        self.assertIsInstance(rec._lock, type(threading.RLock()))

        created_streams = []
        def fake_input_stream(**kwargs):
            m = MagicMock()
            m.active = True
            m.kwargs = kwargs
            created_streams.append(m)
            return m

        with patch("engine.audio_recorder.sd.InputStream", side_effect=fake_input_stream):
            # Test idle re-warmup with real warmup method
            rec.warmup_stream()
            rec.set_device(3)
            self.assertEqual(rec.device, 3)

            # Test live recording device switch without deadlock
            rec.start_recording()
            self.assertTrue(rec.is_recording)
            rec.set_device(8)
            self.assertEqual(rec.device, 8)
            self.assertTrue(rec.is_recording)

            # Clean termination
            rec.close()
            self.assertFalse(rec.is_recording)

    def test_set_device_while_recording_preserves_audio_frames(self):
        """Verify that switching microphones during active dictation preserves all captured audio frames."""
        import numpy as np
        rec = AudioRecorder(sample_rate=16000)

        created_streams = []
        def fake_input_stream(**kwargs):
            m = MagicMock()
            m.active = True
            m.kwargs = kwargs
            created_streams.append(m)
            return m

        with patch("engine.audio_recorder.sd.InputStream", side_effect=fake_input_stream):
            rec.start_recording()
            self.assertTrue(rec.is_recording)

            # Simulate one captured audio frame during dictation (0.5s audio > 0.3s min threshold)
            frame_chunk = np.ones((8000, 1), dtype=np.float32) * 0.1
            rec.audio_frames.append(frame_chunk)
            self.assertEqual(len(rec.audio_frames), 1)

            # Switch microphone device while dictation is in progress
            rec.set_device(5)
            self.assertEqual(rec.device, 5)
            self.assertTrue(rec.is_recording)

            # CRITICAL: Verify the already-captured audio frame was NOT erased/reset to zero
            self.assertGreaterEqual(len(rec.audio_frames), 1, "Captured audio frames were lost during microphone switch!")
            self.assertTrue(np.allclose(rec.audio_frames[0], frame_chunk))

            # Stop recording and verify audio was successfully extracted
            wav_bytes = rec.stop_recording()
            self.assertIsNotNone(wav_bytes)
            self.assertGreater(len(wav_bytes), 100)
            rec.close()

    def test_set_device_deferred_while_recording(self):
        """Verify that defer_if_recording postpones device switch until dictation ends without losing audio."""
        import numpy as np
        rec = AudioRecorder(sample_rate=16000)

        created_streams = []
        def fake_input_stream(**kwargs):
            m = MagicMock()
            m.active = True
            m.kwargs = kwargs
            created_streams.append(m)
            return m

        with patch("engine.audio_recorder.sd.InputStream", side_effect=fake_input_stream):
            rec.start_recording()
            initial_dev = rec.device

            # Capture initial audio
            frame_chunk = np.ones((8000, 1), dtype=np.float32) * 0.2  # 0.5s audio
            rec.audio_frames.append(frame_chunk)

            # Request device switch with deferral
            rec.set_device(9, defer_if_recording=True)

            # Device must NOT switch immediately while user is speaking
            self.assertEqual(rec.device, initial_dev)
            self.assertEqual(rec._pending_device, 9)
            self.assertEqual(len(rec.audio_frames), 1)

            # Finish dictation
            wav_bytes = rec.stop_recording()
            self.assertIsNotNone(wav_bytes)

            # Deferred switch must apply automatically after dictation concludes
            self.assertEqual(rec.device, 9)
            self.assertIsNone(rec._pending_device)
            self.assertFalse(rec._device_change_pending)
            rec.close()

    def test_switch_from_numbered_device_back_to_default_during_recording(self):
        """Verify that switching from a numbered device back to default (None) during recording is deferred and applied cleanly."""
        import numpy as np
        # Initialize recorder on numbered device 3
        rec = AudioRecorder(sample_rate=16000, device=3)
        self.assertEqual(rec.device, 3)

        created_streams = []
        def fake_input_stream(**kwargs):
            m = MagicMock()
            m.active = True
            m.kwargs = kwargs
            created_streams.append(m)
            return m

        with patch("engine.audio_recorder.sd.InputStream", side_effect=fake_input_stream):
            # Warm up on device 3
            rec.warmup_stream()
            self.assertEqual(len(created_streams), 1)
            self.assertEqual(created_streams[0].kwargs.get("device"), 3)

            # Start recording on device 3
            rec.start_recording()
            self.assertTrue(rec.is_recording)

            # Capture initial audio
            frame_chunk = np.ones((8000, 1), dtype=np.float32) * 0.2  # 0.5s audio
            rec.audio_frames.append(frame_chunk)

            # Switch back to system default (None) while recording with deferral
            rec.set_device(None, defer_if_recording=True)

            # Verify that deferral flag is set even when target device is None!
            self.assertEqual(rec.device, 3)
            self.assertTrue(rec._device_change_pending)
            self.assertIsNone(rec._pending_device)
            self.assertEqual(len(rec.audio_frames), 1)

            # Finish dictation
            wav_bytes = rec.stop_recording()
            self.assertIsNotNone(wav_bytes)

            # Deferred switch to default (None) must be applied upon completion!
            self.assertIsNone(rec.device)
            self.assertFalse(rec._device_change_pending)
            self.assertIsNone(rec._pending_device)

            # Stream was re-warmed on device None
            self.assertGreaterEqual(len(created_streams), 2)
            self.assertIsNone(created_streams[-1].kwargs.get("device"))
            rec.close()

    def test_dictionary_edits_work_immediately_in_stt_and_intelligence(self):
        """Verify that adding/removing a dictionary term immediately reflects in Whisper prompt and polishing."""
        orch = FlowOrchestrator(on_state_change=lambda _: None)
        test_term = "FlowPilotEnterprise"
        test_alias = "flow pilot enterprise"

        # Ensure not present initially
        orch.personalization.remove_term(test_term)

        # Add term
        orch.personalization.add_term(test_term, test_alias)

        # 1. Immediate STT prompt biasing
        prompt = orch.stt.build_bias_prompt([], "en")
        self.assertIn(test_term, prompt, "Whisper prompt did not immediately contain newly added dictionary term!")

        # 2. Immediate WritingIntelligence casing & alias expansion
        polished = orch.processor.process("we are running flow pilot enterprise in production")
        res_text = polished if isinstance(polished, str) else polished.get("text", "")
        self.assertIn(test_term, res_text, "WritingIntelligence did not immediately apply newly added dictionary term!")

        # Cleanup
        orch.personalization.remove_term(test_term)

    def test_snippet_edits_work_immediately(self):
        """Verify that adding a voice snippet immediately expands during dictation formatting."""
        orch = FlowOrchestrator(on_state_change=lambda _: None)
        trigger = "insert secret audit code"
        expansion = "FP-SEC-9988-OK"

        orch.personalization.remove_snippet(trigger)
        orch.personalization.add_snippet(trigger, expansion)

        # Test immediate expansion
        res = orch.processor.process("please insert secret audit code now")
        res_text = res if isinstance(res, str) else res.get("text", "")
        self.assertIn(expansion, res_text)

        # Cleanup
        orch.personalization.remove_snippet(trigger)

    def test_paste_last_targets_intended_editor_safely(self):
        """Verify that inject_last targets intended editor, avoids FlowPilot windows, and copies to clipboard if missing."""
        TextInjector.last_injected_text = "Test recovery phrase 12345"
        TextInjector.last_target_hwnd = 54321

        # 1. When target_hwnd is a valid external window, inject_last targets it
        with patch("engine.text_injector.win32gui.IsWindow", return_value=True), \
             patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=54321), \
             patch.object(TextInjector, "_is_flowpilot_window", return_value=False), \
             patch.object(TextInjector, "inject_with_status") as mock_inject:
            mock_inject.return_value = MagicMock(status=InjectionStatus.CONFIRMED_INSERTED)
            res = TextInjector.inject_last()
            mock_inject.assert_called_once_with("Test recovery phrase 12345", target_hwnd=54321)

        # 2. When foreground is a FlowPilot window, inject_last refuses to paste into FlowPilot and targets last_target_hwnd
        flowpilot_hwnd = 11111
        editor_hwnd = 54321
        def is_flowpilot(h):
            return h == flowpilot_hwnd

        def is_win(h):
            return h in (flowpilot_hwnd, editor_hwnd)

        with patch("engine.text_injector.win32gui.IsWindow", side_effect=is_win), \
             patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=flowpilot_hwnd), \
             patch.object(TextInjector, "_is_flowpilot_window", side_effect=is_flowpilot), \
             patch.object(TextInjector, "_safe_set_foreground") as mock_fg, \
             patch.object(TextInjector, "inject_with_status") as mock_inject:
            mock_inject.return_value = MagicMock(status=InjectionStatus.CONFIRMED_INSERTED)
            res = TextInjector.inject_last()
            # Verified that it brought the editor to foreground, not the FlowPilot window
            mock_fg.assert_called_with(editor_hwnd)
            mock_inject.assert_called_once_with("Test recovery phrase 12345", target_hwnd=editor_hwnd)

        # 3. When no external editor is open, inject_last safely copies to clipboard without blind keystroke dispatch
        TextInjector.last_target_hwnd = None
        with patch("engine.text_injector.win32gui.IsWindow", return_value=False), \
             patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=0), \
             patch.object(TextInjector, "_safe_clipboard_copy", return_value=True) as mock_copy, \
             patch.object(TextInjector, "inject_with_status") as mock_inject:
            res = TextInjector.inject_last()
            mock_copy.assert_called_once_with("Test recovery phrase 12345")
            mock_inject.assert_not_called()
            self.assertEqual(res.status, InjectionStatus.FAILED_RECOVERY_AVAILABLE)
            self.assertTrue(res.recovery_available)

    def test_f9_and_custom_hotkey_availability_and_default_exemption(self):
        """Verify that F9 is supported and default assigned recovery shortcuts are exempted from reassignment."""
        # 1. F9 single key is valid and testable
        avail, msg = Win32HotkeyService.test_hotkey_availability("F9")
        # In headless or interactive desktop, it should either be available or recognized
        self.assertTrue("Invalid format" not in msg)

        # 2. FlowPilot default recovery shortcuts are exempted / conflict-flagged
        for reserved_key in ["Alt+Shift+Z", "Shift+Alt+Z", "Alt+Shift+X", "Shift+Alt+X", "Ctrl+Alt+T"]:
            avail, msg = Win32HotkeyService.test_hotkey_availability(reserved_key)
            self.assertFalse(avail, f"Expected {reserved_key} to be exempted from reassignment")
            self.assertIn("Conflict", msg)

        # 3. Windows reserved shortcuts are conflict-flagged
        for win_reserved in ["Win+L", "Win+D", "Win+R"]:
            avail, msg = Win32HotkeyService.test_hotkey_availability(win_reserved)
            self.assertFalse(avail, f"Expected {win_reserved} to be flagged as conflict")
            self.assertIn("Conflict", msg)

    def test_setup_wizard_hotkey_step_and_persistence(self):
        """Verify that the First-Run Setup Wizard exposes hotkey selection and persists F9 push-to-talk."""
        app = QApplication.instance() or QApplication(sys.argv)
        test_cfg = {
            "first_run_completed": False,
            "hotkey": "Ctrl+Shift+Space",
            "hotkey_mode": "toggle",
            "language": "en"
        }
        wizard = SetupWizardDialog(config=test_cfg)
        self.assertEqual(wizard.stack.count(), 5)

        # Configure F9 push-to-talk in Step 4
        wizard.combo_hotkey.setEditText("F9")
        wizard.radio_ptt.setChecked(True)
        wizard._test_wizard_hotkey()
        self.assertTrue("AVAILABLE" in wizard.lbl_wizard_hk_status.text() or "CONFLICT" in wizard.lbl_wizard_hk_status.text())

        # Complete setup
        with patch.object(wizard, "accept"):
            wizard._finish_setup()

        self.assertEqual(test_cfg.get("hotkey"), "F9")
        self.assertEqual(test_cfg.get("hotkey_mode"), "push_to_talk")
        self.assertTrue(test_cfg.get("first_run_completed"))

    def test_reserved_keyword_triggers_in_personalization(self):
        """Verify that voice snippets warn when trigger phrase matches assigned command keywords."""
        res_f9 = self.personalization.add_snippet("f9", "Function Nine Expansion")
        self.assertEqual(res_f9["status"], "added")
        self.assertTrue(any("reserved command or key name" in w for w in res_f9.get("warnings", [])))

        res_recovery = self.personalization.add_snippet("paste last", "Recovery text expansion")
        self.assertEqual(res_recovery["status"], "added")
        self.assertTrue(any("reserved command or key name" in w for w in res_recovery.get("warnings", [])))
        self.personalization.remove_snippet("f9")
        self.personalization.remove_snippet("paste last")


if __name__ == "__main__":
    unittest.main()
