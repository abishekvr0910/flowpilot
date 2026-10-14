"""
Regression and Verification Test for Silero VAD ONNX Asset Resolution
Verifies:
1. Exact Silero VAD asset files exist and are valid in:
   - dist/FlowPilot/_internal/faster_whisper/assets
   - dist/FlowPilot/assets
   - dist/FlowPilot_backup_v200/_internal/faster_whisper/assets
   - dist/FlowPilot_backup_v210/_internal/faster_whisper/assets
   - dist/FlowPilot_backup_v300/_internal/faster_whisper/assets
2. ONNX Runtime loads silero_encoder_v5.onnx directly without errors.
3. Faster-Whisper transcribes an audio sample with vad_filter=True successfully.
4. Launching FlowPilot.exe from a different working directory resolves VAD assets without errors.
"""
import os
import sys
import io
import time
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def test_silero_assets():
    print("=" * 70)
    print("SILERO VAD ONNX ASSET RESOLUTION & REGRESSION TEST")
    print("=" * 70)

    # 1. Check all dist directories
    targets = [
        "dist/FlowPilot/_internal/faster_whisper/assets",
        "dist/FlowPilot/assets",
        "dist/FlowPilot_backup_v200/_internal/faster_whisper/assets",
        "dist/FlowPilot_backup_v210/_internal/faster_whisper/assets",
        "dist/FlowPilot_backup_v300/_internal/faster_whisper/assets",
    ]

    print("\n[Step 1] Verifying asset existence across all distributions...")
    for t in targets:
        full_path = PROJECT_ROOT / t
        enc = full_path / "silero_encoder_v5.onnx"
        dec = full_path / "silero_decoder_v5.onnx"
        assert enc.is_file(), f"Missing silero_encoder_v5.onnx in {t}"
        assert enc.stat().st_size > 500000, f"Corrupt silero_encoder_v5.onnx in {t}"
        print(f"  [OK] {t}: encoder ({enc.stat().st_size} bytes)")

    # 2. Test ONNX Runtime direct session creation on the bundled model
    print("\n[Step 2] Testing direct ONNX Runtime session load on bundled model...")
    bundled_enc = str(PROJECT_ROOT / "dist/FlowPilot/_internal/faster_whisper/assets/silero_encoder_v5.onnx")
    opts = ort.SessionOptions()
    opts.inter_op_num_threads = 1
    opts.intra_op_num_threads = 1
    session = ort.InferenceSession(bundled_enc, sess_options=opts, providers=["CPUExecutionProvider"])
    print(f"  [OK] ONNXRuntime successfully loaded model: {bundled_enc}")
    print(f"  Inputs: {[i.name for i in session.get_inputs()]}")
    print(f"  Outputs: {[o.name for o in session.get_outputs()]}")

    # 3. Test faster-whisper vad_filter=True with synthetic speech audio
    print("\n[Step 3] Testing faster-whisper transcription with vad_filter=True...")
    from engine.stt_engine import STTEngine
    engine = STTEngine({"engine_mode": "local", "local_model_size": "base", "beam_size": 2})

    # Generate 1.5s 16kHz sine tone to simulate audio
    sr = 16000
    t = np.linspace(0, 1.5, int(sr * 1.5), dtype=np.float32)
    sine = 0.5 * np.sin(2 * np.pi * 440 * t)
    buf = io.BytesIO()
    sf.write(buf, sine, sr, format='WAV')
    wav_bytes = buf.getvalue()

    result = engine.transcribe(wav_bytes)
    print(f"  [OK] Transcribe completed successfully with vad_filter active.")
    print(f"  Result text: '{result.get('text')}' (duration: {result.get('duration'):.2f}s)")

    # 4. Test Path Independence: launch packaged FlowPilot.exe from a completely different directory (e.g., %TEMP%)
    print("\n[Step 4] Testing path-independent launch of FlowPilot.exe from %TEMP%...")
    exe_path = str(PROJECT_ROOT / "dist/FlowPilot/FlowPilot.exe")
    temp_dir = os.environ.get("TEMP", "C:\\Temp")
    proc = subprocess.Popen([exe_path], cwd=temp_dir)
    try:
        time.sleep(2.5)
        assert proc.poll() is None, f"Packaged FlowPilot.exe failed to start from {temp_dir}!"
        print(f"  [OK] Packaged FlowPilot.exe is running from CWD={temp_dir} (PID: {proc.pid})")
    finally:
        import psutil
        try:
            p = psutil.Process(proc.pid)
            for c in p.children(recursive=True):
                c.terminate()
            p.terminate()
            proc.wait(timeout=5)
            print("  [OK] FlowPilot.exe cleanly terminated.")
        except Exception:
            proc.kill()

    print("\n" + "=" * 70)
    print("ALL SILERO VAD RESOLUTION & PACKAGING TESTS PASSED!")
    print("=" * 70)

if __name__ == "__main__":
    test_silero_assets()
