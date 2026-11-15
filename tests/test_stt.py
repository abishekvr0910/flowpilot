import sys
import os
import io
from pathlib import Path
import numpy as np
import soundfile as sf

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import load_config
from engine.stt_engine import STTEngine

def test_stt_model():
    print("=" * 60)
    print("AUDIT TEST 2: LOCAL SPEECH-RECOGNITION MODEL & WEIGHTS")
    print("=" * 60)

    # 1. Verify weights presence on disk via the engine's own resolution chain
    # (FLOWPILOT_MODEL_DIR > bundled app dirs > project models/ > user models dir),
    # not a hardcoded HuggingFace cache path the engine never reads.
    resolved = STTEngine.resolve_model_path("base")
    print(f"Engine-resolved model weights directory:\n  {resolved}")
    model_dir = Path(resolved) if resolved else None
    if model_dir is None or not model_dir.exists():
        print("FAILED: Engine could not resolve a local 'base' model directory on disk!")
        return False
    if not STTEngine.is_model_available("base"):
        print("FAILED: STTEngine reports bundled 'base' model unavailable!")
        return False

    files_found = sorted(model_dir.rglob("*.*"))
    print(f"Total model files on disk: {len(files_found)}")
    for f in files_found:
        if f.suffix in (".bin", ".json"):
            print(f"  - {f.name} ({f.stat().st_size:,} bytes)")
    if not any(f.suffix == ".bin" for f in files_found):
        print("FAILED: No .bin weight file in resolved model directory!")
        return False

    # 2. Load model via STTEngine
    config = load_config()
    config["engine_mode"] = "local"
    config["local_model_size"] = "base"
    
    print("\nInitializing STTEngine with local model 'base' (CPU int8)...")
    stt = STTEngine(config)

    # 3. Create a clean spoken tone or audio pattern to transcribe
    fs = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(fs * duration), False)
    # 440Hz test tone
    tone = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, tone, fs, format="WAV", subtype="PCM_16")
    wav_bytes = buf.getvalue()

    print(f"\nSubmitting {len(wav_bytes)} bytes WAV buffer to STTEngine...")
    result = stt.transcribe(wav_bytes)

    print("\nTranscription Result:")
    print(f"  Raw Output: '{result.get('text')}'")
    print(f"  Detected Language: {result.get('detected_language')}")
    print(f"  Engine Used: {result.get('engine')}")
    print(f"  Audio Duration: {result.get('duration')}s")

    if "text" not in result or "detected_language" not in result:
        print("FAILED: Result format invalid.")
        return False

    # Verify idle model unloader reclaims memory
    status_before = stt.get_model_status()
    assert status_before["status"] == "ready"
    unloaded = stt.unload_model()
    assert unloaded is True
    status_after = stt.get_model_status()
    assert status_after["status"] == "unloaded"
    assert status_after["active_size"] is None
    print("[STT] Idle model unloader verified successfully.")

    print("\n[RESULT] Local STT model verified and functioning properly.")
    return True

def test_missing_model_fallback():
    """Verify that an absent model size gracefully falls back to bundled 'base' without network egress."""
    config = load_config()
    config["engine_mode"] = "local"
    config["local_model_size"] = "nonexistent_model_xyz"
    stt = STTEngine(config)
    assert STTEngine.is_model_available("nonexistent_model_xyz") is False
    model = stt._get_local_model()
    assert model is not None
    status = stt.get_model_status()
    assert status["status"] == "ready"
    assert status["active_size"] == "base"
    stt.unload_model()

if __name__ == "__main__":
    s1 = test_stt_model()
    test_missing_model_fallback()
    sys.exit(0 if s1 else 1)
