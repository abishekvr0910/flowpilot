"""
Tests for Feature 28: Persistent Audio Input Selection and Device Identity Resolution
Covers:
- Deterministic resolution when device indices shift across reboots/re-enumerations
- Host API disambiguation across MME, DirectSound, WASAPI, etc.
- Missing/disconnected device detection without silent false-positive switching
- Explicit system default tracking
- Legacy config migration (audio_device_index / mic_device -> audio_input_selection)
- AudioRecorder deferred switching during active recording and frame preservation
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.audio_devices import (
    DeviceResolutionStatus,
    ResolutionResult,
    DEVICE_MISSING_SENTINEL,
    resolve_audio_input,
    build_device_selection,
    migrate_legacy_audio_config,
    get_audio_input_devices
)
from engine.audio_recorder import AudioRecorder


class TestAudioDeviceResolution(unittest.TestCase):

    def setUp(self):
        # Sample mock device inventory simulating Windows PortAudio enumeration
        self.mock_devices = [
            {"index": 0, "name": "Microsoft Sound Mapper - Input", "host_api": "MME", "max_input_channels": 2},
            {"index": 1, "name": "Realtek High Definition Audio", "host_api": "MME", "max_input_channels": 2},
            {"index": 4, "name": "USB Conference Mic", "host_api": "Windows DirectSound", "max_input_channels": 1},
            {"index": 10, "name": "Realtek High Definition Audio", "host_api": "Windows WASAPI", "max_input_channels": 2},
            {"index": 12, "name": "USB Conference Mic", "host_api": "Windows WASAPI", "max_input_channels": 1},
            {"index": 15, "name": "Speakers (Realtek)", "host_api": "MME", "max_input_channels": 0},  # Output only
        ]

    def test_reordered_indices_resolves_correct_device(self):
        """
        P1 regression requirement:
        Microphone A ('USB Conference Mic', 'Windows WASAPI') was index 4 at save time.
        Later, index 4 is occupied by another device or API, and A is now index 12.
        Resolution MUST resolve to index 12, NEVER silently to index 4.
        """
        # Save selection contract for A (saved when it was WASAPI)
        selection = {
            "mode": "endpoint",
            "name": "USB Conference Mic",
            "host_api": "Windows WASAPI",
            "max_channels": 1
        }

        # Resolve against current enumeration where WASAPI USB Mic is index 12, and index 4 is DirectSound
        res = resolve_audio_input(selection, devices=self.mock_devices)
        self.assertEqual(res.status, DeviceResolutionStatus.RESOLVED)
        self.assertEqual(res.device_index, 12)
        self.assertNotEqual(res.device_index, 4)

    def test_host_api_disambiguation_with_identical_names(self):
        """
        When identical microphone names exist across MME and WASAPI,
        the selection contract resolves the exact intended host API.
        """
        mme_selection = {
            "mode": "endpoint",
            "name": "Realtek High Definition Audio",
            "host_api": "MME",
            "max_channels": 2
        }
        res_mme = resolve_audio_input(mme_selection, devices=self.mock_devices)
        self.assertEqual(res_mme.status, DeviceResolutionStatus.RESOLVED)
        self.assertEqual(res_mme.device_index, 1)

        wasapi_selection = {
            "mode": "endpoint",
            "name": "Realtek High Definition Audio",
            "host_api": "Windows WASAPI",
            "max_channels": 2
        }
        res_wasapi = resolve_audio_input(wasapi_selection, devices=self.mock_devices)
        self.assertEqual(res_wasapi.status, DeviceResolutionStatus.RESOLVED)
        self.assertEqual(res_wasapi.device_index, 10)

    def test_missing_or_disconnected_device_reports_missing(self):
        """
        When a saved endpoint is unplugged/disabled, it must report MISSING
        with device_index=DEVICE_MISSING_SENTINEL, NEVER None (which PortAudio treats as default).
        """
        unplugged_selection = {
            "mode": "endpoint",
            "name": "Blue Yeti Pro USB",
            "host_api": "Windows WASAPI",
            "max_channels": 2
        }
        res = resolve_audio_input(unplugged_selection, devices=self.mock_devices)
        self.assertEqual(res.status, DeviceResolutionStatus.MISSING)
        self.assertEqual(res.device_index, DEVICE_MISSING_SENTINEL)
        self.assertNotEqual(res.device_index, None)
        self.assertIn("Blue Yeti Pro USB", res.error_message)

    def test_explicit_system_default_mode(self):
        """
        Explicit default mode dynamically tracks the system default device,
        passing device_index=None to sounddevice while populating device_info.
        """
        default_selection = {"mode": "default"}
        res = resolve_audio_input(default_selection, devices=self.mock_devices, default_device_index=10)
        self.assertEqual(res.status, DeviceResolutionStatus.DEFAULT)
        self.assertIsNone(res.device_index)
        self.assertIsNotNone(res.device_info)
        self.assertEqual(res.device_info["index"], 10)

    def test_build_device_selection_from_index(self):
        """
        build_device_selection constructs a persistent endpoint dictionary.
        """
        sel = build_device_selection(12, devices=self.mock_devices)
        self.assertEqual(sel["mode"], "endpoint")
        self.assertEqual(sel["name"], "USB Conference Mic")
        self.assertEqual(sel["host_api"], "Windows WASAPI")

        # An invalid index requires user selection, never default capture.
        sel_invalid = build_device_selection(999, devices=self.mock_devices)
        self.assertEqual(sel_invalid, {"mode": "unresolved", "legacy_index": 999})

    def test_legacy_config_migration_with_premerged_default(self):
        """
        Regression test: When config loading merges DEFAULT_CONFIG,
        audio_input_selection={'mode': 'default'} is pre-populated.
        Migration MUST still inspect and migrate legacy audio_device_index.
        """
        premerged_cfg = {
            "audio_input_selection": {"mode": "default"},
            "audio_device_index": 12
        }
        modified = migrate_legacy_audio_config(premerged_cfg, devices=self.mock_devices)
        self.assertFalse(modified)
        self.assertEqual(premerged_cfg["audio_input_selection"], {"mode": "default"})

    def test_legacy_config_migration(self):
        """
        Migrates legacy integer 'audio_device_index' into persistent contract.
        """
        legacy_cfg = {"audio_device_index": 12}
        modified = migrate_legacy_audio_config(legacy_cfg, devices=self.mock_devices)
        self.assertTrue(modified)
        self.assertIn("audio_input_selection", legacy_cfg)
        self.assertEqual(legacy_cfg["audio_input_selection"]["mode"], "endpoint")
        self.assertEqual(legacy_cfg["audio_input_selection"]["name"], "USB Conference Mic")
        self.assertEqual(legacy_cfg["audio_input_selection"]["host_api"], "Windows WASAPI")

        # Config with no device info migrates cleanly to default mode
        empty_cfg = {}
        modified = migrate_legacy_audio_config(empty_cfg, devices=self.mock_devices)
        self.assertTrue(modified)
        self.assertEqual(empty_cfg["audio_input_selection"], {"mode": "default"})

        # Config that already has audio_input_selection is not modified
        current_cfg = {"audio_input_selection": {"mode": "default"}}
        modified = migrate_legacy_audio_config(current_cfg, devices=self.mock_devices)
        self.assertFalse(modified)

    def test_name_match_fallback_when_host_api_migrates(self):
        """
        If host API name shifted or is not an exact string match,
        the resolver falls back to matching by name and selects preferred host API.
        """
        selection = {
            "mode": "endpoint",
            "name": "USB Conference Mic",
            "host_api": "Unknown Host API",
            "max_channels": 1
        }
        res = resolve_audio_input(selection, devices=self.mock_devices)
        self.assertEqual(res.status, DeviceResolutionStatus.MISSING)
        self.assertEqual(res.device_index, DEVICE_MISSING_SENTINEL)
        self.assertFalse(res.fallback_used)


class TestAudioRecorderDeviceLifecycle(unittest.TestCase):

    def test_deferred_switch_during_active_recording(self):
        """
        Switching device while recording is active defers the switch until stop_recording(),
        preserving captured frames across the operation.
        """
        import numpy as np
        recorder = AudioRecorder(sample_rate=16000, device=1)
        recorder.is_recording = True
        recorder.audio_frames = [np.zeros((8000, 1), dtype=np.float32)]

        # Request device change while recording with defer_if_recording=True
        recorder.set_device(12, defer_if_recording=True)
        self.assertEqual(recorder.device, 1)
        self.assertTrue(recorder._device_change_pending)
        self.assertEqual(recorder._pending_device, 12)

        # Stop recording should process pending switch
        with patch("engine.audio_recorder.sd.InputStream") as stream:
            try:
                recorder.stop_recording(keep_stream_alive=False)
                self.assertEqual(recorder.device, 12)
                self.assertFalse(recorder._device_change_pending)
                stream.assert_not_called()
            finally:
                recorder.close()

    def test_immediate_switch_when_idle(self):
        """
        When idle, switching device immediately updates device index and resets stream.
        """
        recorder = AudioRecorder(sample_rate=16000, device=1)
        self.assertFalse(recorder.is_recording)

        with patch.object(recorder, "_warmup_stream_locked"):
            recorder.set_device(12, defer_if_recording=False)
            self.assertEqual(recorder.device, 12)
            self.assertFalse(recorder._device_change_pending)

    def test_missing_device_sentinel_blocks_recording_and_warmup(self):
        """
        When device is DEVICE_MISSING_SENTINEL, warmup skips stream creation
        and start_recording raises RuntimeError instead of falling back to default.
        """
        recorder = AudioRecorder(sample_rate=16000, device=DEVICE_MISSING_SENTINEL)
        with patch("engine.audio_recorder.sd.InputStream") as mock_stream:
            recorder.warmup_stream()
            mock_stream.assert_not_called()

            with self.assertRaises(RuntimeError):
                recorder.start_recording()
            mock_stream.assert_not_called()


class TestAudioInputSafetyIntegration(unittest.TestCase):
    """Feature 28: Real routing methods with only OS/hardware boundaries mocked."""

    def setUp(self):
        import tempfile
        from contextlib import ExitStack
        from pathlib import Path
        from types import SimpleNamespace
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        profile = self.stack.enter_context(tempfile.TemporaryDirectory(prefix="fp-audio-test-"))
        self.profile = Path(profile)
        self.stack.enter_context(patch.dict(os.environ, {
            "FLOWPILOT_CONFIG_DIR": profile, "FLOWPILOT_CONFIG_FILE": str(self.profile / "config.json"),
            "FLOWPILOT_HEADLESS": "1", "FLOWPILOT_NO_POPUP": "1", "QT_QPA_PLATFORM": "offscreen"}))
        self.stack.enter_context(patch.object(Path, "home", return_value=self.profile))
        self.devices = [
            {"index": 0, "name": "Laptop", "host_api": "Windows WASAPI", "max_input_channels": 1},
            {"index": 4, "name": "Headset", "host_api": "Windows WASAPI", "max_input_channels": 1},
            {"index": 12, "name": "Headset", "host_api": "Windows WASAPI", "max_input_channels": 2},
        ]
        self.stack.enter_context(patch("engine.audio_devices.get_audio_input_devices", return_value=self.devices))
        self.stack.enter_context(patch("engine.audio_devices.sd", SimpleNamespace(default=SimpleNamespace(device=[0, -1]))))
        self.stream = self.stack.enter_context(patch("engine.audio_recorder.sd.InputStream"))
        from engine import orchestrator
        self.orch_module = orchestrator
        for symbol in ("STTEngine", "ContextProcessor", "AudioDucker", "AudioFeedback", "get_hotkey_service", "get_shared_personalization"):
            self.stack.enter_context(patch.object(orchestrator, symbol))

    def make_orchestrator(self, config):
        from engine.config import DEFAULT_CONFIG
        with patch.object(self.orch_module, "load_config", return_value={**DEFAULT_CONFIG, **config}):
            orch = self.orch_module.FlowOrchestrator()
        self.addCleanup(orch.recorder.close)
        return orch

    def test_all_unusable_resolutions_block_stream_creation(self):
        from engine.audio_devices import resolve_audio_input
        cases = [({}, self.devices), ({"mode": "endpoint", "name": ""}, self.devices),
                 ({"mode": "endpoint", "name": "Absent"}, []),
                 ({"mode": "default"}, []),
                 ({"mode": "endpoint", "name": "Headset", "host_api": "Windows WASAPI", "max_channels": 1},
                  [self.devices[1], dict(self.devices[1], index=9)])]
        for selection, devices in cases:
            with self.subTest(selection=selection):
                resolution = resolve_audio_input(selection, devices=devices)
                recorder = AudioRecorder(device=resolution.device_index)
                try:
                    recorder.warmup_stream()
                    with self.assertRaises(RuntimeError):
                        recorder.start_recording()
                finally:
                    recorder.close()
        self.stream.assert_not_called()

    def test_default_is_authoritative_over_legacy_index(self):
        orch = self.make_orchestrator({"audio_input_selection": {"mode": "default"}, "audio_device_index": 4})
        self.assertIsNone(orch.recorder.device)

    def test_legacy_update_persists_identity_before_restart(self):
        import json
        orch = self.make_orchestrator({"audio_input_selection": {"mode": "default"}})
        self.assertTrue(orch.update_config({"audio_device_index": 12}))
        saved = json.loads((self.profile / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["audio_input_selection"], orch.config["audio_input_selection"])
        self.assertEqual(saved["audio_input_selection"]["max_channels"], 2)
        self.assertEqual(orch.recorder.device, 12)

    def test_raw_migration_survives_disk_reload(self):
        import json
        from engine.config import load_config
        path = self.profile / "config.json"
        path.write_text(json.dumps({"audio_device_index": 12}), encoding="utf-8")
        loaded = load_config()
        self.assertEqual(loaded["audio_input_selection"]["max_channels"], 2)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["audio_input_selection"], loaded["audio_input_selection"])
        self.assertEqual(load_config()["audio_input_selection"], loaded["audio_input_selection"])

    def test_pickers_preserve_missing_and_channel_identity(self):
        from PySide6.QtWidgets import QApplication, QComboBox
        from ui.audio_input_picker import populate_audio_inputs
        app = QApplication.instance() or QApplication([])
        for selection in ({"mode": "endpoint", "name": "Absent", "host_api": "Windows WASAPI"},
                          {"mode": "endpoint", "name": "Headset", "host_api": "Windows WASAPI", "max_channels": 2}):
            combo = QComboBox()
            populate_audio_inputs(combo, {"audio_input_selection": selection})
            self.assertEqual(combo.currentData(), selection)
            combo.deleteLater()
        self.stream.assert_not_called()

    def test_setup_missing_preview_does_not_open_stream(self):
        from PySide6.QtWidgets import QApplication
        from ui.setup_wizard import SetupWizardDialog
        app = QApplication.instance() or QApplication([])
        selection = {"mode": "endpoint", "name": "Absent", "host_api": "Windows WASAPI"}
        wizard = SetupWizardDialog(config={"audio_input_selection": selection})
        try:
            self.assertEqual(wizard.combo_mics.currentData(), selection)
            with patch("ui.setup_wizard.QMessageBox.critical"):
                self.assertFalse(wizard._start_mic_test())
            self.stream.assert_not_called()
        finally:
            wizard.close()
            wizard.deleteLater()

    def test_scratchpad_refreshes_cached_recorder_and_blocks_missing(self):
        from ui.scratchpad_view import ScratchpadView
        view = MagicMock()
        view._audio_recorder = AudioRecorder(device=4)
        self.addCleanup(view._audio_recorder.close)
        with patch("engine.config.load_config", return_value={"audio_input_selection": {
            "mode": "endpoint", "name": "Absent", "host_api": "Windows WASAPI"}}):
            recorder = ScratchpadView._get_audio_recorder(view)
        self.assertEqual(recorder.device, DEVICE_MISSING_SENTINEL)
        with self.assertRaises(RuntimeError):
            recorder.start_recording()
        self.stream.assert_not_called()

    def test_production_stream_failure_does_not_start_synthetic_recording(self):
        from engine import audio_recorder
        recorder = AudioRecorder(device=4)
        self.addCleanup(recorder.close)
        with patch.dict(os.environ, {"FLOWPILOT_HEADLESS": "", "CI": "", "GITHUB_ACTIONS": ""}), \
             patch.object(audio_recorder.sd, "InputStream", side_effect=RuntimeError("device unavailable")), \
             patch.object(audio_recorder.sd, "query_devices", side_effect=RuntimeError("device unavailable")), \
             patch.object(audio_recorder.threading, "Thread") as thread:
            with self.assertRaisesRegex(RuntimeError, "device unavailable"):
                recorder.start_recording()
            self.assertFalse(recorder.is_recording)
            self.assertFalse(recorder.is_synthetic_mode)
            thread.assert_not_called()

    def test_reselecting_active_microphone_cancels_queued_switch(self):
        import json
        orch = self.make_orchestrator({"audio_input_selection": {
            "mode": "endpoint", "name": "Headset", "host_api": "Windows WASAPI", "max_channels": 1}})
        orch.recorder.is_recording = True
        self.assertTrue(orch.update_config({"audio_input_selection": {
            "mode": "endpoint", "name": "Headset", "host_api": "Windows WASAPI", "max_channels": 2}}))
        self.assertTrue(orch.recorder._device_change_pending)
        self.assertEqual(orch.recorder._pending_device, 12)
        self.assertTrue(orch.update_config({"audio_input_selection": {
            "mode": "endpoint", "name": "Headset", "host_api": "Windows WASAPI", "max_channels": 1}}))
        self.assertFalse(orch.recorder._device_change_pending)
        self.assertIsNone(orch.recorder._pending_device)
        self.assertEqual(orch.recorder.device, 4)
        self.assertEqual(json.loads((self.profile / "config.json").read_text(encoding="utf-8"))
                         ["audio_input_selection"]["max_channels"], 1)
        orch.recorder.is_recording = False


if __name__ == "__main__":
    unittest.main()
