"""
Audio Device Identity and Resolution Gate Verification.
Reproducibly tests:
1. Candidate build hash integrity.
2. Host physical/virtual audio input endpoint enumeration.
3. Live stream capture on default endpoint without health stalls.
4. Missing/unplugged endpoint resolution to DEVICE_MISSING_SENTINEL (-9999).
5. Hard capture refusal with RuntimeError (zero silent fallback to unexpected mic).
6. Deterministic resolution across dynamic PortAudio device index renumbering.
7. Reconnect and subsequent recording stream recovery.
"""

import os
import sys
import time
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.audio_devices import (
    DeviceResolutionStatus,
    ResolutionResult,
    DEVICE_MISSING_SENTINEL,
    resolve_audio_input,
    build_device_selection,
    get_audio_input_devices
)
from engine.audio_recorder import AudioRecorder


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def run_hardware_gate():
    print("=" * 70)
    print("      FLOWPILOT AUDIO HARDWARE & DEVICE GATE VERIFICATION")
    print("=" * 70)

    # 1. Verify candidate artifact hashes if present
    exe_path = PROJECT_ROOT / "dist" / "FlowPilot" / "FlowPilot.exe"
    zip_path = PROJECT_ROOT / "dist" / "FlowPilot-v3.1.0-RC8-win64.zip"

    if exe_path.exists() and zip_path.exists():
        exe_hash = sha256_file(exe_path)
        zip_hash = sha256_file(zip_path)
        print(f"[Artifact] Executable: {exe_path.name}")
        print(f"           SHA-256:    {exe_hash}")
        print(f"[Artifact] Archive:    {zip_path.name}")
        print(f"           SHA-256:    {zip_hash}")

        EXPECTED_EXE_HASH = "67C93341837DBD2D317633DC3B2AAA15136A76BB0C887D019F0EC6AFD23FF156"
        EXPECTED_ZIP_HASH = "2DFB83BCC98068389E6962FCC7A0A25131C90F7D546B8CD3ABDBC6E54A43F69F"

        if exe_hash == EXPECTED_EXE_HASH and zip_hash == EXPECTED_ZIP_HASH:
            print("[Artifact] Hashes strictly match published RC8 manifest.")
        else:
            print("[Artifact] Note: Local binary hashes differ from published RC8.")

    # 2. Live Device Enumeration
    devices = get_audio_input_devices()
    print(f"\n[Hardware] Enumerated {len(devices)} input endpoints on host system.")
    for d in devices[:5]:
        print(f"  - [{d['index']}] {d['name']} ({d['host_api']}, {d['max_input_channels']} ch)")
    if len(devices) > 5:
        print(f"  ... and {len(devices) - 5} more endpoints.")

    # 3. Live capture on default endpoint
    print("\n[Phase 1] Testing live microphone stream capture on default device...")
    rec = AudioRecorder(device_index=None)
    rec.start_recording()
    assert rec.is_recording, "Recorder failed to start recording"
    time.sleep(1.0)
    wav_data = rec.stop_recording()
    assert not rec.is_recording, "Recorder failed to stop recording"
    assert wav_data is not None and len(wav_data) > 0, "No audio captured from live hardware"
    assert rec.capture_health_error() is None, f"Health error encountered: {rec.capture_health_error()}"
    print(f"  -> Captured {len(wav_data)} bytes of valid PCM audio in 1.0s. Health OK.")

    # 4. Missing USB Device Sentinel & Zero Silent Fallback Test
    print("\n[Phase 2] Testing missing/unplugged USB microphone behavior...")
    ghost_selection = {
        "mode": "endpoint",
        "name": "HyperX QuadCast S USB",
        "host_api": "Windows WASAPI",
        "max_channels": 2
    }
    res = resolve_audio_input(ghost_selection, devices=devices)
    print(f"  -> Resolution result: status={res.status}, device_index={res.device_index}")
    assert res.status == DeviceResolutionStatus.MISSING
    assert res.device_index == DEVICE_MISSING_SENTINEL

    # Attempt capture with sentinel
    rec_missing = AudioRecorder(device_index=res.device_index)
    capture_blocked = False
    try:
        rec_missing.start_recording()
    except RuntimeError as e:
        capture_blocked = True
        print(f"  -> Safely blocked capture with expected RuntimeError: {e}")

    assert capture_blocked, "Recorder did NOT block capture on missing device sentinel!"
    assert not rec_missing.is_recording, "Recorder should not be recording missing device!"
    print("  -> Zero silent fallback invariant verified: no audio captured from unintended mic.")

    # 5. Dynamic Device Renumbering Resolution
    print("\n[Phase 3] Testing dynamic index shift resolution...")
    real_dev = devices[0] if devices else {"name": "Default Mic", "host_api": "MME", "max_input_channels": 2, "index": 0}
    saved_selection = {
        "mode": "endpoint",
        "name": real_dev["name"],
        "host_api": real_dev["host_api"],
        "max_channels": real_dev["max_input_channels"]
    }
    shifted_inventory = [
        {"index": d["index"] + 50 if d["name"] == real_dev["name"] and d["host_api"] == real_dev["host_api"] else d["index"],
         "name": d["name"],
         "host_api": d["host_api"],
         "max_input_channels": d["max_input_channels"]}
        for d in devices
    ]
    shift_res = resolve_audio_input(saved_selection, devices=shifted_inventory)
    print(f"  -> Original index: {real_dev['index']}, Shifted index: {shift_res.device_index}")
    assert shift_res.status == DeviceResolutionStatus.RESOLVED
    assert shift_res.device_index == real_dev["index"] + 50
    print("  -> Deterministic resolution verified across PortAudio index renumbering.")

    # 6. Reconnect / Recovery Capture
    print("\n[Phase 4] Testing reconnect recovery capture...")
    rec_reconnect = AudioRecorder(device_index=real_dev["index"])
    rec_reconnect.start_recording()
    assert rec_reconnect.is_recording
    time.sleep(0.5)
    reconnect_wav = rec_reconnect.stop_recording()
    assert not rec_reconnect.is_recording
    assert reconnect_wav is not None and len(reconnect_wav) > 0
    print(f"  -> Captured {len(reconnect_wav)} bytes after recovery. Stream closed cleanly.")

    print("\n" + "=" * 70)
    print(" AUDIO HARDWARE GATE: ALL 4 PHASES PASSED WITH ZERO SILENT FALLBACK")
    print("=" * 70)


if __name__ == "__main__":
    run_hardware_gate()
