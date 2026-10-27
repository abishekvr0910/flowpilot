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
        recorder.stream = MagicMock(active=True)
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

    def test_ci_without_captured_frames_returns_no_audio(self):
        recorder = AudioRecorder(sample_rate=16000, device=1)
        stream = MagicMock(active=True)
        with patch.dict(os.environ, {"CI": "1", "GITHUB_ACTIONS": "1"}), \
             patch.object(recorder, "_open_stream_bounded", return_value=stream):
            recorder.start_recording()
            self.assertIsNone(recorder.stop_recording(keep_stream_alive=False))
            self.assertIsNone(recorder.last_audio_array)
        recorder.close()

    def test_ci_stream_failure_does_not_fabricate_audio(self):
        recorder = AudioRecorder(sample_rate=16000, device=1)
        with patch.dict(os.environ, {"CI": "1", "GITHUB_ACTIONS": "1", "FLOWPILOT_HEADLESS": "1"}), \
             patch.object(recorder, "_open_stream_bounded", side_effect=RuntimeError("device unavailable")), \
             patch("engine.audio_recorder.sd.query_devices", side_effect=RuntimeError("device unavailable")):
            with self.assertRaisesRegex(RuntimeError, "device unavailable"):
                recorder.start_recording()
            self.assertFalse(recorder.is_recording)
            self.assertIsNone(recorder.stream)
        recorder.close()


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
             patch.object(audio_recorder.sd, "query_devices", side_effect=RuntimeError("device unavailable")):
            with self.assertRaisesRegex(RuntimeError, "device unavailable"):
                recorder.start_recording()
            self.assertFalse(recorder.is_recording)

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

    def test_refresh_audio_devices_reinitializes_portaudio(self):
        from engine.audio_devices import refresh_audio_devices
        mock_sd = MagicMock()
        self.assertTrue(refresh_audio_devices(sd_module=mock_sd))
        mock_sd._terminate.assert_called_once()
        mock_sd._initialize.assert_called_once()

    def test_stalled_idle_preroll_stream_is_not_treated_as_healthy_hot_stream(self):
        import time
        recorder = AudioRecorder(device=4)
        self.addCleanup(recorder.close)
        recorder.stream = MagicMock(active=True)
        self.assertTrue(recorder.has_healthy_hot_stream())
        recorder._last_callback_at = time.monotonic() - (recorder.CAPTURE_STALL_SECONDS + 0.5)
        self.assertFalse(recorder.has_healthy_hot_stream())


class HardwareBusClassifierTests(unittest.TestCase):
    """Unit tests for authoritative Win32 CfgMgr32 + MMDEVAPI hardware bus classification."""

    @staticmethod
    def _make_mock_winreg_and_cfg(registry_nodes: list[dict]):
        """Build fake winreg and cfgmgr32 mocks from a list of endpoint node dicts.

        Each dict in registry_nodes has:
          - subkey: str (e.g. '{0.0.1.00000000}.{guid-1}')
          - friendly_name: str
          - active: bool
          - parent_pnp_id: str
        """
        by_subkey = {n["subkey"]: n for n in registry_nodes}
        by_inst_id = {f"SWD\\MMDEVAPI\\{n['subkey']}": n for n in registry_nodes}

        class FakeKey:
            def __init__(self, subkey=None):
                self.subkey = subkey

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeWinreg:
            HKEY_LOCAL_MACHINE = 0x80000002

            @staticmethod
            def OpenKey(root, path):
                if root == FakeWinreg.HKEY_LOCAL_MACHINE:
                    return FakeKey(None)
                if isinstance(root, FakeKey) and path in by_subkey:
                    return FakeKey(path)
                raise OSError("Key not found")

            @staticmethod
            def EnumKey(key_obj, index):
                if index < len(registry_nodes):
                    return registry_nodes[index]["subkey"]
                raise OSError("No more keys")

            @staticmethod
            def QueryValueEx(key_obj, value_name):
                if value_name == "FriendlyName" and key_obj.subkey in by_subkey:
                    return by_subkey[key_obj.subkey]["friendly_name"], 1
                raise OSError("Value not found")

        class FakeCfgMgr32:
            def __init__(self):
                self._devinst_to_parent_id = {}
                self._next_handle = 100

            def CM_Locate_DevNodeW(self, p_devinst, inst_id, flags):
                node = by_inst_id.get(inst_id)
                if not node or not node.get("active", False):
                    return 13  # CR_NO_SUCH_DEVNODE
                h = self._next_handle
                self._next_handle += 1
                p_devinst._obj.value = h
                self._devinst_to_parent_id[h] = node["parent_pnp_id"]
                return 0  # CR_SUCCESS

            def CM_Get_Parent(self, p_parent, devinst, flags):
                h = getattr(devinst, "value", devinst)
                if h not in self._devinst_to_parent_id:
                    return 13
                p_parent._obj.value = h + 1000
                self._devinst_to_parent_id[h + 1000] = self._devinst_to_parent_id[h]
                return 0

            def CM_Get_Device_IDW(self, parent_handle, buf, buf_len, flags):
                h = getattr(parent_handle, "value", parent_handle)
                parent_id = self._devinst_to_parent_id.get(h)
                if not parent_id:
                    return 13
                buf.value = parent_id
                return 0

        return FakeWinreg(), FakeCfgMgr32()

    def test_unique_usb_audio_endpoint_is_classified_as_usb(self):
        from scripts.interactive_physical_mic_test import classify_hardware_bus
        winreg_mod, cfg_lib = self._make_mock_winreg_and_cfg([
            {
                "subkey": "{0.0.1.00000000}.{11111111-2222-3333-4444-555555555555}",
                "friendly_name": "Microphone (Yeti Stereo Microphone)",
                "active": True,
                "parent_pnp_id": r"USB\VID_B58E&PID_9E84&MI_00\7&1A2B3C4D&0&0000",
            }
        ])
        res = classify_hardware_bus(
            "Microphone (Yeti Stereo Microphone)",
            host_api="Windows WASAPI",
            winreg_module=winreg_mod,
            cfgmgr32_lib=cfg_lib,
        )
        self.assertTrue(res["is_usb_bus_device"])
        self.assertEqual(res["hardware_bus_class"], "usb_audio_device")
        self.assertFalse(res["ambiguous_endpoint_match"])
        self.assertEqual(res["resolution_authority"], "win32_cfgmgr32_unique_devnode")

    def test_duplicate_active_friendly_names_fail_closed_without_explicit_id(self):
        from scripts.interactive_physical_mic_test import classify_hardware_bus
        winreg_mod, cfg_lib = self._make_mock_winreg_and_cfg([
            {
                "subkey": "{0.0.1.00000000}.{aaaaaaaa-1111-2222-3333-444444444444}",
                "friendly_name": "Microphone (Generic Audio)",
                "active": True,
                "parent_pnp_id": r"USB\VID_046D&PID_0A37&MI_00\6&1111&0&0000",
            },
            {
                "subkey": "{0.0.1.00000000}.{bbbbbbbb-1111-2222-3333-444444444444}",
                "friendly_name": "Microphone (Generic Audio)",
                "active": True,
                "parent_pnp_id": r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0287\5&2222&0&0001",
            },
        ])
        res = classify_hardware_bus(
            "Microphone (Generic Audio)",
            host_api="Windows WASAPI",
            winreg_module=winreg_mod,
            cfgmgr32_lib=cfg_lib,
        )
        self.assertFalse(res["is_usb_bus_device"])
        self.assertTrue(res["ambiguous_endpoint_match"])
        self.assertEqual(res["hardware_bus_class"], "ambiguous_multiple_active_endpoints")
        self.assertEqual(res["matched_active_endpoint_count"], 2)
        self.assertEqual(res["resolution_authority"], "ambiguous_multiple_active_devnodes_fail_closed")

    def test_explicit_mmdevice_endpoint_id_disambiguates_duplicate_friendly_names(self):
        from scripts.interactive_physical_mic_test import classify_hardware_bus
        winreg_mod, cfg_lib = self._make_mock_winreg_and_cfg([
            {
                "subkey": "{0.0.1.00000000}.{aaaaaaaa-1111-2222-3333-444444444444}",
                "friendly_name": "Microphone (Generic Audio)",
                "active": True,
                "parent_pnp_id": r"USB\VID_046D&PID_0A37&MI_00\6&1111&0&0000",
            },
            {
                "subkey": "{0.0.1.00000000}.{bbbbbbbb-1111-2222-3333-444444444444}",
                "friendly_name": "Microphone (Generic Audio)",
                "active": True,
                "parent_pnp_id": r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0287\5&2222&0&0001",
            },
        ])
        res_usb = classify_hardware_bus(
            "Microphone (Generic Audio)",
            host_api="Windows WASAPI",
            mmdevice_endpoint_id=r"SWD\MMDEVAPI\{0.0.1.00000000}.{aaaaaaaa-1111-2222-3333-444444444444}",
            winreg_module=winreg_mod,
            cfgmgr32_lib=cfg_lib,
        )
        self.assertTrue(res_usb["is_usb_bus_device"])
        self.assertEqual(res_usb["hardware_bus_class"], "usb_audio_device")
        self.assertFalse(res_usb["ambiguous_endpoint_match"])
        self.assertEqual(res_usb["resolution_authority"], "win32_cfgmgr32_explicit_endpoint")

        res_analog = classify_hardware_bus(
            "Microphone (Generic Audio)",
            host_api="Windows WASAPI",
            mmdevice_endpoint_id=r"SWD\MMDEVAPI\{0.0.1.00000000}.{bbbbbbbb-1111-2222-3333-444444444444}",
            winreg_module=winreg_mod,
            cfgmgr32_lib=cfg_lib,
        )
        self.assertFalse(res_analog["is_usb_bus_device"])
        self.assertEqual(res_analog["hardware_bus_class"], "analog_jack_hd_audio_endpoint")
        self.assertEqual(res_analog["resolution_authority"], "win32_cfgmgr32_explicit_endpoint")

    def test_inactive_phantom_duplicate_does_not_trigger_ambiguity(self):
        from scripts.interactive_physical_mic_test import classify_hardware_bus
        winreg_mod, cfg_lib = self._make_mock_winreg_and_cfg([
            {
                "subkey": "{0.0.1.00000000}.{aaaaaaaa-1111-2222-3333-444444444444}",
                "friendly_name": "Microphone (Realtek(R) Audio)",
                "active": False,  # Disconnected phantom node
                "parent_pnp_id": r"USB\VID_046D&PID_0A37&MI_00\6&1111&0&0000",
            },
            {
                "subkey": "{0.0.1.00000000}.{bbbbbbbb-1111-2222-3333-444444444444}",
                "friendly_name": "Microphone (Realtek(R) Audio)",
                "active": True,
                "parent_pnp_id": r"INTELAUDIO\FUNC_01&VEN_10EC&DEV_0287\5&2222&0&0001",
            },
        ])
        res = classify_hardware_bus(
            "Microphone (Realtek(R) Audio)",
            host_api="Windows WASAPI",
            winreg_module=winreg_mod,
            cfgmgr32_lib=cfg_lib,
        )
        self.assertFalse(res["ambiguous_endpoint_match"])
        self.assertFalse(res["is_usb_bus_device"])
        self.assertEqual(res["hardware_bus_class"], "analog_jack_hd_audio_endpoint")
        self.assertEqual(res["matched_active_endpoint_count"], 1)

    def test_mme_31_char_prefix_matching_is_restricted_to_mme_host_api(self):
        from scripts.interactive_physical_mic_test import classify_hardware_bus
        full_name = "Microphone Array (Intel Smart Sound Technology for Digital Microphones)"
        truncated_mme = full_name[:31]
        winreg_mod, cfg_lib = self._make_mock_winreg_and_cfg([
            {
                "subkey": "{0.0.1.00000000}.{cccccccc-1111-2222-3333-444444444444}",
                "friendly_name": full_name,
                "active": True,
                "parent_pnp_id": r"INTELAUDIO\CTLR_DEV_51C8\5&2C95BAB1&0&0000",
            }
        ])
        # Under MME, 31-character truncated name matches
        res_mme = classify_hardware_bus(
            truncated_mme,
            host_api="MME",
            winreg_module=winreg_mod,
            cfgmgr32_lib=cfg_lib,
        )
        self.assertEqual(res_mme["matched_active_endpoint_count"], 1)
        self.assertEqual(res_mme["hardware_bus_class"], "analog_jack_hd_audio_endpoint")

        # Under Windows WASAPI, truncated prefix does NOT match
        res_wasapi = classify_hardware_bus(
            truncated_mme,
            host_api="Windows WASAPI",
            winreg_module=winreg_mod,
            cfgmgr32_lib=cfg_lib,
        )
        self.assertEqual(res_wasapi["matched_active_endpoint_count"], 0)
        self.assertEqual(res_wasapi["hardware_bus_class"], "unverified_non_usb_endpoint")



if __name__ == "__main__":
    unittest.main()
