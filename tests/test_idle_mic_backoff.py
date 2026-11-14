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


if __name__ == "__main__":
    unittest.main()
