"""Verify idle standby microphone stream release and orchestrator backoff timer."""

import os
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio_recorder import AudioRecorder
from engine.config import DEFAULT_CONFIG
from engine.orchestrator import AppState, FlowOrchestrator


class IdleMicBackoffTests(unittest.TestCase):
    def test_default_config_sets_idle_mic_backoff(self):
        self.assertEqual(DEFAULT_CONFIG["idle_mic_backoff_sec"], 60.0)

    def test_release_idle_stream_closes_hot_stream_and_skips_active_recording(self):
        recorder = AudioRecorder(device=0)
        fake_stream = MagicMock()
        recorder.stream = fake_stream
        recorder._preroll_buffer.append("chunk")
        recorder._last_callback_at = 123.0

        # Active recording must never drop its live capture stream
        recorder.is_recording = True
        self.assertFalse(recorder.release_idle_stream())
        self.assertIs(recorder.stream, fake_stream)
        fake_stream.close.assert_not_called()

        # When idle, release_idle_stream closes and clears the stream
        recorder.is_recording = False
        self.assertTrue(recorder.release_idle_stream())
        self.assertIsNone(recorder.stream)
        self.assertEqual(recorder._last_callback_at, 0.0)
        self.assertEqual(len(recorder._preroll_buffer), 0)
        fake_stream.abort.assert_called_once()
        fake_stream.close.assert_called_once()

        # Releasing again when no stream exists returns False
        self.assertFalse(recorder.release_idle_stream())

    def test_orchestrator_idle_mic_timer_fires_only_when_idle(self):
        released = threading.Event()
        orch = FlowOrchestrator.__new__(FlowOrchestrator)
        orch._state_lock = threading.RLock()
        orch.state = AppState.IDLE
        orch.is_processing = False
        orch._idle_mic_timer = None
        orch._idle_mic_backoff_sec = 0.05
        orch.recorder = SimpleNamespace(
            is_recording=False,
            release_idle_stream=lambda: (released.set() or True),
        )

        # While recording or non-idle, _on_idle_mic_timeout must be a no-op
        orch.state = AppState.RECORDING
        orch._on_idle_mic_timeout()
        self.assertFalse(released.is_set())

        orch.state = AppState.IDLE
        orch.recorder.is_recording = True
        orch._on_idle_mic_timeout()
        self.assertFalse(released.is_set())

        # Scheduling when IDLE fires and calls release_idle_stream
        orch.recorder.is_recording = False
        orch._schedule_idle_mic_backoff()
        self.assertTrue(released.wait(timeout=1.0))

        # Cancelling prevents timer execution
        released.clear()
        orch._idle_mic_backoff_sec = 0.08
        orch._schedule_idle_mic_backoff()
        orch._cancel_idle_mic_backoff()
        time.sleep(0.15)
        self.assertFalse(released.is_set())

    def test_stale_generation_timeout_is_ignored_and_serialized(self):
        released_streams = []
        entered_release = threading.Event()
        proceed_release = threading.Event()

        def slow_release():
            entered_release.set()
            proceed_release.wait(timeout=2.0)
            released_streams.append("stream_0")
            return True

        orch = FlowOrchestrator.__new__(FlowOrchestrator)
        orch._state_lock = threading.RLock()
        orch._mic_release_lock = threading.RLock()
        orch._idle_mic_generation = 0
        orch._stopped = False
        orch.state = AppState.IDLE
        orch.is_processing = False
        orch._idle_mic_timer = None
        orch._idle_unload_timer = None
        orch._idle_mic_backoff_sec = 60.0
        orch.recorder = SimpleNamespace(is_recording=False, release_idle_stream=slow_release)

        # Schedule generation 1, then reschedule to generation 2 before stale gen 1 runs
        orch._schedule_idle_mic_backoff()
        stale_gen = orch._idle_mic_generation
        orch._schedule_idle_mic_backoff()
        orch._cancel_idle_mic_backoff()

        # Stale generation callback must abort even when state is IDLE
        orch._on_idle_mic_timeout(expected_gen=stale_gen)
        self.assertFalse(entered_release.is_set())
        self.assertEqual(released_streams, [])

        # When current generation enters release_idle_stream, concurrent _cancel_idle_mic_backoff
        # waits or cannot overlap with a concurrent start transition holding _mic_release_lock
        orch._schedule_idle_mic_backoff()
        cur_gen = orch._idle_mic_generation
        orch._cancel_idle_mic_backoff()  # user starts dictation -> bumps gen and cancels timer
        orch._on_idle_mic_timeout(expected_gen=cur_gen)
        self.assertEqual(released_streams, [])

        # Running timeout serializes with _mic_release_lock until release_idle_stream finishes
        orch._schedule_idle_mic_backoff()
        active_gen = orch._idle_mic_generation
        t = threading.Thread(target=orch._on_idle_mic_timeout, args=(active_gen,), daemon=True)
        t.start()
        self.assertTrue(entered_release.wait(timeout=1.0))

        acquired_during_release = threading.Event()

        def try_transition():
            with orch._get_mic_release_lock():
                acquired_during_release.set()

        t2 = threading.Thread(target=try_transition, daemon=True)
        t2.start()
        time.sleep(0.05)
        self.assertFalse(acquired_during_release.is_set())
        proceed_release.set()
        t.join(timeout=1.0)
        t2.join(timeout=1.0)
        self.assertTrue(acquired_during_release.is_set())
        self.assertEqual(released_streams, ["stream_0"])

        # After stop(), _schedule_idle_mic_backoff does not arm a new timer
        orch._stopped = True
        orch._schedule_idle_mic_backoff()
        self.assertIsNone(orch._idle_mic_timer)

    def test_no_speech_empty_transcript_reschedules_idle_mic_backoff(self):
        from engine.orchestrator import DictationSession

        released = threading.Event()
        notified = threading.Event()
        orch = FlowOrchestrator.__new__(FlowOrchestrator)
        orch.config = {"post_roll_ms": 0, "language": "en", "active_tone_mode": "general"}
        orch._state_lock = threading.RLock()
        orch._mic_release_lock = threading.RLock()
        orch._idle_mic_generation = 0
        orch._stopped = False
        orch._idle_unload_timer = None
        orch._idle_unload_timeout_sec = 0.0
        orch._idle_mic_timer = None
        orch._idle_mic_backoff_sec = 0.05
        orch._auto_stop_timer = None
        orch._capture_watchdog_stop = threading.Event()
        orch._pending_model_switch = None
        orch.is_processing = False
        orch.state = AppState.RECORDING
        session = DictationSession(target_window_info={}, tone_mode="general")
        orch._current_session = session

        orch.recorder = SimpleNamespace(
            is_recording=False,
            stop_recording=lambda post_roll_ms=0.0: b"RIFF0000",
            get_last_audio_array=lambda: None,
            release_idle_stream=lambda: (released.set() or True),
        )
        orch.feedback = SimpleNamespace(play_stop=lambda: None)
        orch.ducker = SimpleNamespace(stop_ducking=lambda: None)
        orch.stt = SimpleNamespace(transcribe=lambda *a, **kw: {"text": "   ", "detected_language": "en"})
        orch._notify = lambda st, payload=None: notified.set() if st == AppState.IDLE else None

        orch.stop_dictation_and_process()
        self.assertTrue(notified.wait(timeout=1.5))
        self.assertEqual(orch.state, AppState.IDLE)
        self.assertIsNotNone(orch._idle_mic_timer)
        self.assertTrue(released.wait(timeout=1.5))
        orch._cancel_idle_mic_backoff()


class TestOrchestratorShutdownAndRebinding(unittest.TestCase):
    def _build_orchestrator(self, events):
        from types import SimpleNamespace
        from engine.orchestrator import FlowOrchestrator, AppState

        orch = FlowOrchestrator.__new__(FlowOrchestrator)
        orch._state_lock = threading.RLock()
        orch._mic_release_lock = threading.RLock()
        orch._capture_watchdog_stop = threading.Event()
        orch._stopped = False
        orch._stop_pending = False
        orch.is_processing = False
        orch._current_session = None
        orch._auto_stop_timer = None
        orch._idle_unload_timer = None
        orch._idle_mic_timer = None
        orch._idle_unload_timeout_sec = 600.0
        orch._idle_mic_backoff_sec = 60.0
        orch._idle_mic_generation = 0
        orch._pending_model_switch = None
        orch._device_selection = {"mode": "default"}
        orch._last_device_resolution = SimpleNamespace(device_index=None, device_info=None, error_message=None)
        orch._auxiliary_hotkeys = {}
        orch.state = AppState.IDLE
        orch.config = {
            "engine_mode": "local",
            "local_model_size": "base",
            "hotkey": "Ctrl+Shift+Space",
            "hotkey_mode": "toggle",
            "hotkey_exclusive": False,
            "hold_to_mute_enabled": False,
            "mute_hotkey": "Ctrl+Space",
            "smart_pause_during_calls": False,
            "sound_effects_enabled": False,
            "idle_model_unload_sec": 600.0,
            "idle_mic_backoff_sec": 60.0,
            "audio_input_selection": {"mode": "default"},
        }
        orch.capture_monitor = None
        orch.text_repair = None
        orch.stt = SimpleNamespace(config=orch.config, _get_local_model=lambda: None)
        orch.processor = SimpleNamespace(config=orch.config)
        orch.feedback = SimpleNamespace(enabled=False, play_start=lambda: events.append("play_start"), play_error=lambda: events.append("play_error"))
        orch.ducker = SimpleNamespace(start_ducking=lambda: None, stop_ducking=lambda: None)
        orch.on_state_change = None

        class _FakeHotkeyService:
            def __init__(self, label):
                self._label = label
                self.stats = {"errors": []}

            def is_alive(self):
                return False

            def register(self, *args, **kwargs):
                events.append((self._label, "register", args[0]))
                return 1

            def start(self, timeout=3.0):
                events.append((self._label, "start"))
                return True

            def stop(self):
                events.append((self._label, "stop", orch.hotkey_service is self))

        class _FakeRecorder:
            device = None
            _device_change_pending = False

            def has_healthy_hot_stream(self):
                return True

            def set_device(self, dev, defer_if_recording=False):
                self.device = dev

            def start_recording(self):
                events.append("recorder_start")

            def stop_recording(self):
                events.append("recorder_stop")

            def close(self):
                events.append("recorder_close")

        orch.hotkey_service = _FakeHotkeyService("old_hotkey")
        orch.recorder = _FakeRecorder()
        return orch

    def test_stop_stops_hotkeys_before_closing_recorder_and_rejects_post_stop_actions(self):
        from engine.orchestrator import AppState

        events = []
        orch = self._build_orchestrator(events)

        orch.stop()

        self.assertTrue(orch._stopped)
        stop_idx = events.index(("old_hotkey", "stop", True))
        close_idx = events.index("recorder_close")
        self.assertLess(stop_idx, close_idx)

        orch.start_dictation()
        orch.toggle_dictation()
        orch.start_hotkey_listener()
        orch._schedule_idle_unloader()
        orch._schedule_idle_mic_backoff()

        self.assertEqual(orch.state, AppState.IDLE)
        self.assertNotIn("recorder_start", events)
        self.assertNotIn(("old_hotkey", "start"), events)
        self.assertIsNone(orch._idle_unload_timer)
        self.assertIsNone(orch._idle_mic_timer)

    def test_stop_aborts_queued_start_worker_without_starting_recording(self):
        from unittest.mock import patch
        from engine.orchestrator import AppState

        events = []
        orch = self._build_orchestrator(events)
        real_thread_cls = threading.Thread
        mic_starter_thread = None
        allow_mic_starter = threading.Event()
        mic_starter_spawned = threading.Event()

        def deferred_thread(*args, **kwargs):
            nonlocal mic_starter_thread
            if kwargs.get("name") == "FlowPilot-MicStarter":
                target = kwargs["target"]
                t_args = kwargs.get("args", ())

                def _gated():
                    allow_mic_starter.wait(timeout=2.0)
                    target(*t_args)

                mic_starter_thread = real_thread_cls(target=_gated, daemon=True, name="FlowPilot-MicStarter")
                mic_starter_spawned.set()
                return mic_starter_thread
            return real_thread_cls(*args, **kwargs)

        with patch("engine.orchestrator.WindowInspector.get_active_window_info", return_value={"hwnd": 0, "process_name": "test"}), \
             patch("engine.orchestrator.threading.Thread", side_effect=deferred_thread):
            orch.start_dictation()

        self.assertTrue(mic_starter_spawned.wait(timeout=1.5))
        orch.stop()
        allow_mic_starter.set()
        mic_starter_thread.join(timeout=2.0)
        self.assertFalse(mic_starter_thread.is_alive())

        self.assertTrue(orch._stopped)
        self.assertEqual(orch.state, AppState.CANCELLED)
        self.assertNotIn("recorder_start", events)
        self.assertNotIn("play_start", events)

    def test_update_config_hotkey_rebinding_invokes_stop_before_replacement(self):
        from types import SimpleNamespace
        from unittest.mock import patch

        events = []
        orch = self._build_orchestrator(events)
        old_service = orch.hotkey_service

        class _ReplacementHotkeyService:
            stats = {"errors": []}

            def is_alive(self):
                return False

            def register(self, *args, **kwargs):
                events.append(("new_hotkey", "register", args[0]))
                return 1

            def start(self, timeout=3.0):
                events.append(("new_hotkey", "start", orch.hotkey_service is self))
                return True

            def stop(self):
                events.append(("new_hotkey", "stop"))

        new_service = _ReplacementHotkeyService()

        with patch("engine.orchestrator.Win32HotkeyService.test_hotkey_availability", return_value=(True, "OK")), \
             patch("engine.orchestrator.resolve_audio_input", return_value=SimpleNamespace(device_index=None, device_info=None, error_message=None)), \
             patch("engine.orchestrator.save_config", return_value=True), \
             patch("engine.hotkey_service.get_hotkey_service", return_value=new_service):
            ok = orch.update_config({"hotkey": "Ctrl+Alt+F9", "hotkey_mode": "push_to_talk"})

        try:
            self.assertTrue(ok)
            self.assertIs(orch.hotkey_service, new_service)
            self.assertIsNot(orch.hotkey_service, old_service)
            stop_pos = events.index(("old_hotkey", "stop", True))
            start_pos = events.index(("new_hotkey", "start", True))
            self.assertLess(stop_pos, start_pos)
        finally:
            orch._cancel_idle_unloader()
            orch._cancel_idle_mic_backoff()

    def test_stop_during_inflight_mic_open_prevents_or_tears_down_recording(self):
        import time
        from types import SimpleNamespace
        from unittest.mock import patch
        from engine.orchestrator import AppState

        # Case 1: stop() runs while start_worker is resolving audio device (before start_recording)
        events = []
        orch = self._build_orchestrator(events)
        in_resolve = threading.Event()
        allow_resolve = threading.Event()

        def slow_resolve(_selection):
            in_resolve.set()
            allow_resolve.wait(timeout=2.0)
            return SimpleNamespace(device_index=None, device_info=None, error_message=None)

        states = []
        orch.on_state_change = lambda st, payload=None: states.append(st)

        with patch("engine.orchestrator.WindowInspector.get_active_window_info", return_value={"hwnd": 0, "process_name": "test"}), \
             patch("engine.orchestrator.resolve_audio_input", side_effect=slow_resolve):
            orch.start_dictation()
            self.assertTrue(in_resolve.wait(timeout=1.5))

            stop_thread = threading.Thread(target=orch.stop, daemon=True)
            stop_thread.start()
            # Wait until stop() marks _stopped under _state_lock (before _mic_release_lock)
            deadline = time.monotonic() + 1.5
            while not orch._stopped and time.monotonic() < deadline:
                time.sleep(0.005)
            self.assertTrue(orch._stopped)
            allow_resolve.set()
            stop_thread.join(timeout=2.0)

        # Wait briefly for MicStarter thread if still unwinding
        for t in threading.enumerate():
            if t.name == "FlowPilot-MicStarter" and t.is_alive():
                t.join(timeout=1.5)

        self.assertNotIn("recorder_start", events)
        self.assertNotIn("play_start", events)
        self.assertNotIn(AppState.RECORDING, states)
        self.assertEqual(orch.state, AppState.CANCELLED)

        # Case 2: _stopped becomes True while start_recording() itself is executing
        events2 = []
        states2 = []
        orch2 = self._build_orchestrator(events2)
        orch2.on_state_change = lambda st, payload=None: states2.append(st)
        stop_entered_close = threading.Event()

        def start_rec_concurrent_stop():
            events2.append("recorder_start")
            with orch2._state_lock:
                orch2._stopped = True
            stop_entered_close.set()

        orch2.recorder.start_recording = start_rec_concurrent_stop

        with patch("engine.orchestrator.WindowInspector.get_active_window_info", return_value={"hwnd": 0, "process_name": "test"}), \
             patch("engine.orchestrator.resolve_audio_input", return_value=SimpleNamespace(device_index=None, device_info=None, error_message=None)):
            orch2.start_dictation()
            self.assertTrue(stop_entered_close.wait(timeout=1.5))

        for t in threading.enumerate():
            if t.name == "FlowPilot-MicStarter" and t.is_alive():
                t.join(timeout=1.5)

        self.assertIn("recorder_stop", events2)
        self.assertIn("recorder_close", events2)
        self.assertNotIn("play_start", events2)
        self.assertNotIn(AppState.RECORDING, states2)
        orch2.stop()


if __name__ == "__main__":
    unittest.main()
