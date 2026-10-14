import sys
import sounddevice as sd
import numpy as np
import time

print("=" * 60)
print("FLOWPILOT HARDWARE & SYSTEM DIAGNOSTICS")
print("=" * 60)

# 1. Check Audio Devices
print("\n[1] Checking Audio Input Devices...")
devices = sd.query_devices()
input_devices = [d for d in devices if d['max_input_channels'] > 0]
print(f"Total input devices found: {len(input_devices)}")
for idx, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        is_default = " (DEFAULT)" if idx == sd.default.device[0] else ""
        print(f"  [{idx}] {d['name']}{is_default} - In Channels: {d['max_input_channels']}, Rate: {d['default_samplerate']}")

# 2. Test Audio Recording
print("\n[2] Testing 1-second Audio Capture...")
try:
    fs = 16000
    recording = sd.rec(int(fs * 1.0), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    max_amp = np.max(np.abs(recording))
    rms = np.sqrt(np.mean(recording**2))
    print(f"  Recording Success! Max Amplitude: {max_amp:.4f}, RMS Energy: {rms:.4f}")
    if max_amp == 0:
        print("  [WARNING] Microphone recorded pure silence (amplitude 0). Mic might be muted in Windows settings.")
    else:
        print("  [OK] Microphone is capturing sound!")
except Exception as e:
    print(f"  [ERROR] Recording failed: {e}")

# 3. Test Local Whisper Model
print("\n[3] Testing Local Whisper Inference...")
try:
    from faster_whisper import WhisperModel
    import io
    import soundfile as sf
    
    print("  Loading local model 'base'...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("  Model loaded! Running test inference on dummy buffer...")
    
    # Generate 1s tone
    dummy_wav = io.BytesIO()
    sf.write(dummy_wav, recording, fs, format="WAV", subtype="PCM_16")
    dummy_wav.seek(0)
    
    segments, info = model.transcribe(dummy_wav, beam_size=1)
    text = " ".join([s.text for s in segments])
    print(f"  Inference Success! Result text: '{text}' (lang={info.language})")
except Exception as e:
    print(f"  [ERROR] Local Whisper failed: {e}")

# 4. Test Windows Pasting / Focus
print("\n[4] Testing Windows Focus & Pasting...")
try:
    import win32gui
    import win32process
    import psutil
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    print(f"  Current active window: HWND={hwnd}, Title='{title}'")
except Exception as e:
    print(f"  [ERROR] Win32 inspection failed: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTICS COMPLETE")
print("=" * 60)
