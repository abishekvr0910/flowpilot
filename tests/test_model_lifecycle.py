"""
Unit and Concurrency Tests for STTEngine Model Lifecycle & Orchestrator Ownership (Track B)
"""

import sys
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.stt_engine import STTEngine
from engine.orchestrator import FlowOrchestrator, AppState

class MockSegment:
    def __init__(self, text: str, start: float = 0.0, end: float = 1.0):
        self.text = text
        self.start = start
        self.end = end

class MockWhisperModel:
    def __init__(self, model_target: str, **kwargs):
        self.model_target = model_target
        self.kwargs = kwargs
        self.transcribe_call_count = 0

    def transcribe(self, audio_input, **kwargs):
        self.transcribe_call_count += 1
        def lazy_gen():
            yield MockSegment("Hello", 0.0, 0.5)
            yield MockSegment("world", 0.5, 1.0)
        info = MagicMock()
        info.language = kwargs.get("language") or "en"
        info.language_probability = 0.99
        info.duration = 1.0
        return lazy_gen(), info

def test_base_to_small_model_key_and_reloading():
    """Verify base to small constructs a new model, while identical key reuses cached model."""
    construct_count = 0
    created_targets = []

    def mock_factory(target, **kwargs):
        nonlocal construct_count
        construct_count += 1
        created_targets.append(target)
        return MockWhisperModel(target, **kwargs)

    config = {"local_model_size": "base", "cpu_threads": 4}
    with patch("engine.stt_engine.WhisperModel", side_effect=mock_factory):
        stt = STTEngine(config)

        # 1. First load
        m1 = stt._get_local_model()
        assert construct_count == 1
        status = stt.get_model_status()
        assert status["requested_size"] == "base"
        assert status["active_size"] == "base"
        assert status["status"] == "ready"

        # 2. Second load with same config must reuse instance
        m2 = stt._get_local_model()
        assert construct_count == 1
        assert m1 is m2

        # 3. Requesting different model size triggers new construction
        stt.config["local_model_size"] = "small"
        m3 = stt._get_local_model()
        assert construct_count == 2
        assert m3 is not m1
        status = stt.get_model_status()
        assert status["requested_size"] == "small"
        assert status["active_size"] == "small"

def test_settings_change_key_invalidation_vs_decode_settings():
    """Construction settings (threads) invalidate model key; decode settings (lang) do not."""
    construct_count = 0

    def mock_factory(target, **kwargs):
        nonlocal construct_count
        construct_count += 1
        return MockWhisperModel(target, **kwargs)

    config = {"local_model_size": "base", "cpu_threads": 4, "language": "en"}
    with patch("engine.stt_engine.WhisperModel", side_effect=mock_factory):
        stt = STTEngine(config)
        stt._get_local_model()
        assert construct_count == 1

        # Changing decode setting (language) does NOT reload model
        stt.config["language"] = "ta"
        stt._get_local_model()
        assert construct_count == 1, "Language change must not reload model weights"

        # Changing construction setting (threads) DOES reload model
        stt.config["cpu_threads"] = 8
        stt._get_local_model()
        assert construct_count == 2, "Threads change must rebuild model key and reload"

def test_failed_model_switch_retains_prior_working_model():
    """A failed model load (missing weights) must retain the prior working model intact."""
    call_count = 0

    def mock_factory(target, **kwargs):
        nonlocal call_count
        call_count += 1
        if "small" in str(target):
            raise RuntimeError("Weights file model.bin not found on disk")
        return MockWhisperModel(target, **kwargs)

    config = {"local_model_size": "base", "cpu_threads": 4}
    with patch("engine.stt_engine.WhisperModel", side_effect=mock_factory):
        stt = STTEngine(config)
        base_model = stt._get_local_model()
        assert call_count == 1
        assert stt.get_model_status()["active_size"] == "base"

        # Try switching to missing 'small'
        stt.config["local_model_size"] = "small"
        try:
            stt._get_local_model()
        except RuntimeError as e:
            assert "not found" in str(e)
        else:
            raise AssertionError("Expected RuntimeError on missing weights")

        # Working base model is STILL intact
        status = stt.get_model_status()
        assert status["requested_size"] == "small"
        assert status["active_size"] == "base", "Prior working model must be retained on failed switch"
        assert status["status"] == "ready", "Status remains ready with fallback model"
        assert "not found" in status["last_error"]
        assert stt._local_model is base_model

def test_rapid_requests_coalescing():
    """Rapid base -> small -> base requests discard stale completions and do not activate small."""
    loaded_targets = []
    barrier = threading.Barrier(2)

    def slow_small_factory(target, **kwargs):
        if "small" in str(target):
            # Wait for signal that another request arrived
            barrier.wait(timeout=2.0)
            time.sleep(0.05)
        loaded_targets.append(target)
        return MockWhisperModel(target, **kwargs)

    config = {"local_model_size": "base", "cpu_threads": 4}
    with patch("engine.stt_engine.WhisperModel", side_effect=slow_small_factory):
        stt = STTEngine(config)
        stt._get_local_model()  # base loaded (gen 1)

        # Trigger small in background
        stt.config["local_model_size"] = "small"
        t = threading.Thread(target=stt._get_local_model)
        t.start()

        # Synchronize and request base again (gen 3)
        barrier.wait(timeout=2.0)
        stt.config["local_model_size"] = "base"
        m_base = stt._get_local_model()
        t.join(timeout=2.0)

        # Ensure active model is base, not small
        assert stt.get_model_status()["active_size"] == "base"

def test_concurrent_preload_and_transcribe_loads_once():
    """Concurrent preload and transcribe at startup load the model exactly once."""
    construct_count = 0

    def delay_factory(target, **kwargs):
        nonlocal construct_count
        time.sleep(0.05)
        construct_count += 1
        return MockWhisperModel(target, **kwargs)

    config = {"local_model_size": "base", "cpu_threads": 4}
    with patch("engine.stt_engine.WhisperModel", side_effect=delay_factory):
        stt = STTEngine(config)

        t1 = threading.Thread(target=stt.preload_model)
        t2 = threading.Thread(target=lambda: stt.transcribe(b"fake_audio_bytes"))

        t1.start()
        t2.start()
        t1.join(timeout=2.0)
        t2.join(timeout=2.0)

        assert construct_count == 1, f"Expected 1 load, got {construct_count}"

def test_orchestrator_defers_model_switch_during_recording():
    """Orchestrator defers model switch if dictation is in-flight, applying it when idle."""
    with patch("engine.stt_engine.WhisperModel", side_effect=lambda target, **kw: MockWhisperModel(target, **kw)):
        orch = FlowOrchestrator()
        orch.config["local_model_size"] = "base"
        orch.recorder = MagicMock()
        orch.recorder.is_recording = False
        orch.state = AppState.IDLE

        # Simulate recording in-flight
        orch.state = AppState.RECORDING
        res = orch.update_config({"local_model_size": "small"})
        assert res is True
        assert orch._pending_model_switch == "small", "Switch to small must be deferred"
        assert orch.config["local_model_size"] == "base", "In-flight config keeps base"

        # Transition to IDLE applies deferred switch
        orch.state = AppState.IDLE
        orch._apply_pending_model_switch_if_idle()
        assert orch._pending_model_switch is None
        assert orch.config["local_model_size"] == "small", "Deferred switch applied on idle"

def test_lazy_segment_consumption_pins_active_inferences():
    """Active inferences counter remains > 0 while segments generator is being consumed."""
    active_during_consumption = None

    class GeneratorMockWhisperModel:
        def __init__(self, target, **kwargs):
            self.model_target = target

        def transcribe(self, audio_input, **kwargs):
            def gen():
                nonlocal active_during_consumption
                active_during_consumption = stt._active_inferences
                yield MockSegment("Word", 0.0, 1.0)
            info = MagicMock()
            info.language = "en"
            return gen(), info

    config = {"local_model_size": "base", "cpu_threads": 4}
    with patch("engine.stt_engine.WhisperModel", side_effect=GeneratorMockWhisperModel):
        stt = STTEngine(config)
        assert stt._active_inferences == 0
        res = stt.transcribe(b"dummy")
        assert res["text"] == "Word"
        assert active_during_consumption == 1, "Model ownership must be active during lazy segment iteration"
        assert stt._active_inferences == 0, "Active inferences counter must return to 0 after transcription"

def test_env_dir_base_weights_cannot_masquerade_as_small(tmp_path):
    """A FLOWPILOT_MODEL_DIR with faster-whisper-base weights must not resolve as small."""
    base_dir = tmp_path / "faster-whisper-base"
    base_dir.mkdir()
    (base_dir / "model.bin").write_bytes(b"dummy_weights")

    with patch.dict("os.environ", {"FLOWPILOT_MODEL_DIR": str(tmp_path)}):
        resolved_base = STTEngine.resolve_model_path("base")
        assert "faster-whisper-base" in resolved_base

        resolved_small = STTEngine.resolve_model_path("small")
        assert "faster-whisper-base" not in resolved_small
        expected_small = [
            "small",
            str(Path(__file__).resolve().parent.parent / "models" / "faster-whisper-small"),
            str(Path(__file__).resolve().parent.parent / "models" / "small"),
        ]
        assert resolved_small in expected_small, "Small must not resolve to base folder"

if __name__ == "__main__":
    print("Running STTEngine model lifecycle tests...")
    test_base_to_small_model_key_and_reloading()
    test_settings_change_key_invalidation_vs_decode_settings()
    test_failed_model_switch_retains_prior_working_model()
    test_rapid_requests_coalescing()
    test_concurrent_preload_and_transcribe_loads_once()
    test_orchestrator_defers_model_switch_during_recording()
    test_lazy_segment_consumption_pins_active_inferences()
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        test_env_dir_base_weights_cannot_masquerade_as_small(Path(td))
    print("[RESULT] STTEngine model lifecycle tests PASSED.")
    sys.exit(0)

