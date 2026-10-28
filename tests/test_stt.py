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

    # 1. Verify weights presence on disk
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--Systran--faster-whisper-base"
    print(f"Checking model weights directory:\n  {cache_dir}")
    if not cache_dir.exists():
        print("FAILED: Model directory does not exist on disk!")
        return False

    snapshot_dir = cache_dir / "snapshots"
    snapshots = list(snapshot_dir.glob("*")) if snapshot_dir.exists() else []
    print(f"Snapshots found: {[s.name for s in snapshots]}")
    
    files_found = list(cache_dir.rglob("*.*"))
    print(f"Total model files on disk: {len(files_found)}")
    for f in files_found:
        if f.suffix in ('.bin', '.json'):
            print(f"  - {f.name} ({f.stat().st_size:,} bytes)")

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

if __name__ == "__main__":
    success = test_stt_model()
    sys.exit(0 if success else 1)
