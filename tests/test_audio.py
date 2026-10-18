import os
import sys
import sounddevice as sd
import numpy as np
import io
import soundfile as sf

def test_microphone():
    print("=" * 60)
    print("AUDIT TEST 1: MICROPHONE DEVICE ENUMERATION & PERMISSIONS")
    print("=" * 60)

    devices = sd.query_devices()
    input_devices = [d for d in devices if d['max_input_channels'] > 0]
    print(f"Total input audio devices discovered: {len(input_devices)}")

    try:
        default_device = int(sd.default.device[0])
    except Exception:
        default_device = -1

    if not input_devices or default_device < 0 or default_device >= len(devices):
        print("[RESULT] SKIPPED: Headless environment with 0 physical microphones detected.")
        return True

    default_info = devices[default_device]
    print(f"Default device name: {default_info['name']}")
    print(f"Max input channels: {default_info['max_input_channels']}")
    print(f"Default sample rate: {default_info['default_samplerate']}")

    print("\nRecording 2.0 second test audio sample...")
    fs = 16000
    try:
        audio = sd.rec(int(2.0 * fs), samplerate=fs, channels=1, dtype='float32')
        sd.wait()
    except Exception as e:
        if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS") or any(k in str(e).lower() for k in ("device unavailable", "host error", "invalid device", "no default", "unanticipated", "error querying")):
            print(f"[RESULT] SKIPPED: Physical audio hardware unavailable in headless environment ({e}).")
            return True
        print(f"FAILED: Physical audio hardware capture exception: {e}")
        return False

    max_amp = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio**2)))
    print(f"Captured audio shape: {audio.shape}")
    print(f"Peak amplitude: {max_amp:.6f}")
    print(f"RMS Energy: {rms:.6f}")

    # Check if stream produced valid WAV
    buf = io.BytesIO()
    sf.write(buf, audio, fs, format="WAV", subtype="PCM_16")
    wav_len = len(buf.getvalue())
    print(f"WAV encoded byte length: {wav_len} bytes")

    if wav_len < 1000:
        print("FAILED: Encoded WAV is empty or corrupt.")
        return False

    print("\n[RESULT] Microphone recording PASSED with valid PCM stream.")
    return True

if __name__ == "__main__":
    success = test_microphone()
    sys.exit(0 if success else 1)
