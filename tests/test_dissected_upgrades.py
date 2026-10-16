"""
Tests for FlowPilot Architectural Upgrades Adopted from Competitive Teardowns:
1. Pre-roll Audio Ring Buffer (from whisper-local)
2. TapLatch Dual Push-to-Talk / Hands-Free State Machine (from whisper-local)
3. Atomic Win32 Clipboard Sequence Number Verification (from SpeakoFlow)
4. Local OpenAI-Compatible Server Endpoints: GET /v1/models & POST /v1/audio/transcriptions
"""

import sys
import time
import io
import numpy as np
import soundfile as sf
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio_recorder import AudioRecorder
from engine.hotkey_service import TapLatch
from engine.text_injector import TextInjector
from engine.server import app
from fastapi.testclient import TestClient

def test_preroll_audio_buffer():
    """Validates that AudioRecorder maintains a rolling pre-roll buffer and seeds recordings."""
    rec = AudioRecorder(sample_rate=16000)
    assert rec.enable_preroll is True
    assert rec.preroll_seconds == 0.35
    assert len(rec._preroll_buffer) == 0

    # Simulate 5 chunks arriving while idle (not recording)
    dummy_chunk = np.zeros((512, 1), dtype=np.float32)
    for _ in range(5):
        rec._audio_callback(dummy_chunk, 512, None, None)

    # Pre-roll buffer must have captured the idle chunks
    assert len(rec._preroll_buffer) > 0, "Pre-roll buffer should accumulate idle audio chunks"
    buffered_count = len(rec._preroll_buffer)

    # Now trigger start_recording; it must transfer the pre-roll frames
    rec.start_recording()
    assert rec.is_recording is True
    assert len(rec.audio_frames) >= buffered_count, "Recording frames must be seeded with pre-roll buffer"
    assert len(rec._preroll_buffer) == 0, "Pre-roll buffer must be cleared once transferred"

    # Clean up
    rec.close()
    assert rec.is_recording is False

def test_tap_latch_state_machine():
    """Validates dual Push-to-Talk hold and Double-Tap hands-free latch state transitions."""
    starts, stops = [], []
    latch = TapLatch(
        on_start=lambda: starts.append(1),
        on_stop=lambda: stops.append(1),
        window_ms=250
    )
    assert latch.state == TapLatch.IDLE

    # Scenario A: Push-to-talk long hold (> window_ms)
    latch.press()
    assert latch.state == TapLatch.HELD
    assert len(starts) == 1
    time.sleep(0.3)
    latch.release()
    assert latch.state == TapLatch.IDLE
    assert len(stops) == 1

    # Scenario B: Quick double-tap (< window_ms)
    latch.press()
    latch.release()
    assert latch.state == TapLatch.PENDING
    latch.press()
    assert latch.state == TapLatch.LATCHED, "Second tap within window must transition to LATCHED"
    assert len(starts) == 2

    # Scenario C: Tap while latched stops recording
    latch.press()
    assert latch.state == TapLatch.IDLE, "Pressing while latched must return to IDLE and trigger stop"
    assert len(stops) == 2

    # Scenario D: Quick tap without second tap expires timer
    latch.press()
    latch.release()
    assert latch.state == TapLatch.PENDING
    time.sleep(0.35)
    assert latch.state == TapLatch.IDLE, "Window expiration must return state to IDLE"
    assert len(stops) == 3

def test_clipboard_sequence_atomic_check():
    """Validates that TextInjector can atomically read the Win32 clipboard sequence counter."""
    seq = TextInjector._get_clipboard_sequence_number()
    if sys.platform == "win32":
        assert isinstance(seq, int) and seq > 0, "Win32 GetClipboardSequenceNumber must return a positive integer"
        copied = TextInjector._safe_clipboard_copy("flowpilot_seq_test")
        if copied:
            new_seq = TextInjector._get_clipboard_sequence_number()
            assert new_seq != seq, "Clipboard sequence number must advance upon writing new content"

def test_openai_compatible_models_endpoint():
    """Validates GET /v1/models returns OpenAI-compliant model catalog."""
    client = TestClient(app)
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("object") == "list"
    models = [m.get("id") for m in data.get("data", [])]
    assert "whisper-1" in models

def test_openai_compatible_transcriptions_endpoint():
    """Validates POST /v1/audio/transcriptions processes audio and returns standard OpenAI JSON."""
    client = TestClient(app)

    # Synthesize a clean 1.0s sine wave WAV
    fs = 16000
    t = np.linspace(0, 1.0, fs, False)
    tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, tone, fs, format="WAV", subtype="PCM_16")
    wav_bytes = buf.getvalue()

    # Test JSON response format
    files = {"file": ("test.wav", wav_bytes, "audio/wav")}
    data = {"model": "whisper-1", "response_format": "json"}
    resp = client.post("/v1/audio/transcriptions", files=files, data=data)
    assert resp.status_code == 200
    res_json = resp.json()
    assert "text" in res_json, "OpenAI transcriptions response must contain 'text' field"

    # Test text response format
    files_txt = {"file": ("test.wav", wav_bytes, "audio/wav")}
    data_txt = {"model": "whisper-1", "response_format": "text"}
    resp_txt = client.post("/v1/audio/transcriptions", files=files_txt, data=data_txt)
    assert resp_txt.status_code == 200
    assert isinstance(resp_txt.text, str)

if __name__ == "__main__":
    test_preroll_audio_buffer()
    test_tap_latch_state_machine()
    test_clipboard_sequence_atomic_check()
    test_openai_compatible_models_endpoint()
    test_openai_compatible_transcriptions_endpoint()
    print("\n[RESULT] All competitive upgrade verification tests PASSED.")
    sys.exit(0)
