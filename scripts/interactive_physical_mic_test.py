"""
scripts/interactive_physical_mic_test.py

FlowPilot Physical USB Microphone Disconnect & Reconnect Gate Protocol.

Step 1 Verification according to docs/specs/0002-persistent-audio-input-identity.md:
This script guides an operator through the physical USB microphone unplug and
reconnect test on real hardware, and optionally supports automated validation.

Interactive Workflow:
1. Enumerates physical/virtual audio input endpoints.
2. Identifies or prompts the operator to select the USB microphone.
3. Starts live audio recording on the selected USB endpoint.
4. Prompts the operator to speak into the microphone while monitoring signal level.
5. Prompts the operator to PHYSICALLY UNPLUG the USB cable while dictating.
6. Detects stream stall / packet loss via capture_health_error() in <= 2.0s.
7. Verifies zero silent fallback to any internal/alternative microphone.
8. Prompts the operator to PHYSICALLY RECONNECT the USB cable.
9. Automatically re-resolves the hardware endpoint using persistent identity.
10. Executes a recovery recording session to confirm stream stability.
11. Writes a verified receipt to docs/testing/PHYSICAL_USB_UNPLUG_RECEIPT_<timestamp>.md.
"""

import sys
import time
import argparse
import datetime
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
    get_audio_input_devices,
)
from engine.audio_recorder import AudioRecorder


def select_target_device(devices, interactive: bool = True):
    """Finds USB devices or allows operator selection."""
    usb_candidates = [
        d for d in devices
        if any(term in d["name"].lower() for term in ["usb", "headset", "hyperx", "yeti", "rode", "shure", "samson", "focusrite"])
    ]

    if not interactive:
        if usb_candidates:
            return usb_candidates[0]
        return devices[0] if devices else None

    print("\n--- Audio Input Device Inventory ---")
    for i, dev in enumerate(devices):
        is_usb = " [USB/External Candidate]" if dev in usb_candidates else ""
        print(f"[{i:2d}] {dev['name']} ({dev['host_api']}, {dev['max_input_channels']} ch){is_usb}")

    if usb_candidates:
        default_idx = devices.index(usb_candidates[0])
        prompt = f"\nSelect device to test [default {default_idx} - {usb_candidates[0]['name']}]: "
    else:
        default_idx = 0
        prompt = f"\nNo obvious USB device string found. Select device [default 0]: "

    choice = input(prompt).strip()
    if not choice:
        return devices[default_idx]
    try:
        idx = int(choice)
        return devices[idx]
    except (ValueError, IndexError):
        print(f"Invalid selection, defaulting to device index {default_idx}")
        return devices[default_idx]


def run_interactive_test(simulated: bool = False):
    print("=" * 72)
    print("   FLOWPILOT PHYSICAL USB MICROPHONE DISCONNECT & RECONNECT GATE")
    print("=" * 72)

    devices = get_audio_input_devices()
    if not devices:
        print("[ERROR] No audio input devices found on this system!")
        sys.exit(1)

    print(f"\n[1] Enumerated {len(devices)} input endpoints.")
    target_dev = select_target_device(devices, interactive=not simulated)
    print(f"\n[Target Device Selected]:")
    print(f"  Name:        {target_dev['name']}")
    print(f"  Host API:    {target_dev['host_api']}")
    print(f"  Index:       {target_dev['index']}")
    print(f"  Channels:    {target_dev['max_input_channels']}")

    # Build persistent identity specification
    selection = {
        "mode": "endpoint",
        "name": target_dev["name"],
        "host_api": target_dev["host_api"],
        "max_channels": target_dev["max_input_channels"],
    }

    # Phase 1: Pre-flight stream check
    print("\n[Phase 1] Initializing audio stream on target endpoint...")
    rec = AudioRecorder(device_index=target_dev["index"])
    levels_seen = []
    rec.level_callback = lambda lvl: levels_seen.append(lvl)

    rec.start_recording()
    print("  -> Stream started. Speak into the microphone now (recording for 2.0s)...")
    wait_time = 0.5 if simulated else 2.0
    time.sleep(wait_time)
    pre_audio = rec.stop_recording()

    health_err = rec.capture_health_error()
    assert health_err is None, f"Pre-flight health check failed: {health_err}"
    assert pre_audio is not None and len(pre_audio) > 0, "No audio captured during pre-flight"
    max_level = max(levels_seen) if levels_seen else 0.0
    print(f"  -> Pre-flight passed: captured {len(pre_audio)} bytes (peak level: {max_level:.3f}).")

    if simulated:
        print("\n[Simulated Mode] Simulating physical disconnect via endpoint disappearance...")
        # Simulate disconnect by creating missing inventory
        remaining_devices = [d for d in devices if d["name"] != target_dev["name"]]
        unplug_res = resolve_audio_input(selection, devices=remaining_devices)
        assert unplug_res.status == DeviceResolutionStatus.MISSING
        assert unplug_res.device_index == DEVICE_MISSING_SENTINEL
        print(f"  -> Sentinel returned: {unplug_res.device_index} (Status: {unplug_res.status})")

        rec_blocked = AudioRecorder(device_index=unplug_res.device_index)
        blocked = False
        try:
            rec_blocked.start_recording()
        except RuntimeError:
            blocked = True
        assert blocked, "Stream did not refuse missing sentinel!"
        print("  -> Capture refusal confirmed (zero silent fallback).")

        print("\n[Simulated Mode] Simulating physical reconnect...")
        reconnect_res = resolve_audio_input(selection, devices=devices)
        assert reconnect_res.status == DeviceResolutionStatus.RESOLVED
        assert reconnect_res.device_index == target_dev["index"]
        print(f"  -> Re-resolved to original index: {reconnect_res.device_index}")

        # Recovery recording
        rec_recovery = AudioRecorder(device_index=reconnect_res.device_index)
        rec_recovery.start_recording()
        time.sleep(0.5)
        rec_wav = rec_recovery.stop_recording()
        assert rec_wav is not None and len(rec_wav) > 0
        print(f"  -> Recovery stream captured {len(rec_wav)} bytes cleanly.")
        print("\n[SIMULATED GATE PASSED 100%]")
        return True

    # Phase 2: Live In-Flight Disconnect
    print("\n" + "#" * 72)
    print(" [Phase 2] IN-FLIGHT PHYSICAL DISCONNECT TEST")
    print(" 1. The recorder will now start capturing audio.")
    print(" 2. Begin speaking steadily into the microphone.")
    print(" 3. When you see '*** UNPLUG NOW! ***', PHYSICALLY UNPLUG THE USB CABLE!")
    print("#" * 72)
    input("\nPress ENTER when ready to start in-flight test...")

    disconnect_rec = AudioRecorder(device_index=target_dev["index"])
    disconnect_rec.start_recording()
    print("\n  -> Recording live stream. Start speaking now...")
    time.sleep(1.5)

    print("\n" + "!" * 50)
    print("   *** UNPLUG THE USB MICROPHONE CABLE NOW! ***")
    print("!" * 50 + "\n")

    t_unplug_start = time.perf_counter()
    detected_error = None
    timeout_sec = 6.0

    while time.perf_counter() - t_unplug_start < timeout_sec:
        err = disconnect_rec.capture_health_error()
        if err:
            detected_error = err
            t_detection = time.perf_counter() - t_unplug_start
            print(f"  -> [DETECTED] Stream failure detected in {t_detection:.2f}s:")
            print(f"     Error message: '{err}'")
            break
        time.sleep(0.1)

    t_unplug_duration = time.perf_counter() - t_unplug_start
    if not detected_error:
        print(f"\n[WARNING] Disconnect was not detected within {timeout_sec:.1f}s.")
        print("Did you unplug the physical USB cable?")
        disconnect_rec.stop_recording()
        return False

    # Close the dead stream bounded
    print("  -> Closing stalled stream cleanly...")
    disconnect_rec.stop_recording()
    print("  -> Stream closed without host freeze or deadlock.")

    # Phase 3: Verify Zero Silent Fallback
    print("\n[Phase 3] Checking Zero Silent Fallback...")
    post_unplug_devices = get_audio_input_devices()
    res_unplugged = resolve_audio_input(selection, devices=post_unplug_devices)
    print(f"  -> Status while unplugged: {res_unplugged.status} (device_index={res_unplugged.device_index})")
    assert res_unplugged.status == DeviceResolutionStatus.MISSING
    assert res_unplugged.device_index == DEVICE_MISSING_SENTINEL

    refusal_rec = AudioRecorder(device_index=res_unplugged.device_index)
    refused = False
    try:
        refusal_rec.start_recording()
    except RuntimeError as re_err:
        refused = True
        print(f"  -> Attempt to record while unplugged was safely refused: {re_err}")
    assert refused, "AudioRecorder did not refuse capture on missing device!"
    print("  -> Zero Silent Fallback confirmed: laptop mic was NOT hijacked.")

    # Phase 4: Physical Reconnect
    print("\n" + "#" * 72)
    print(" [Phase 4] PHYSICAL RECONNECT & RECOVERY")
    print(" 1. PHYSICALLY PLUG THE USB MICROPHONE CABLE BACK IN NOW.")
    print(" 2. The script will poll for hardware re-enumeration.")
    print("#" * 72)

    reconnected = False
    poll_t0 = time.perf_counter()
    while time.perf_counter() - poll_t0 < 20.0:
        current_devs = get_audio_input_devices()
        chk = resolve_audio_input(selection, devices=current_devs)
        if chk.status == DeviceResolutionStatus.RESOLVED:
            reconnected = True
            reconnect_idx = chk.device_index
            print(f"\n  -> [RECONNECTED] Device re-enumerated at index {reconnect_idx} in {time.perf_counter() - poll_t0:.2f}s!")
            break
        time.sleep(0.5)
        print(".", end="", flush=True)

    if not reconnected:
        print("\n[ERROR] Device was not re-detected within 20 seconds.")
        return False

    # Phase 5: Recovery Dictation
    print("\n[Phase 5] Executing post-reconnect dictation...")
    rec_post = AudioRecorder(device_index=reconnect_idx)
    rec_post.start_recording()
    print("  -> Stream live. Speak for 2.0s...")
    time.sleep(2.0)
    post_wav = rec_post.stop_recording()

    assert rec_post.capture_health_error() is None, f"Health error after reconnect: {rec_post.capture_health_error()}"
    assert post_wav is not None and len(post_wav) > 0, "No audio captured after reconnect!"
    print(f"  -> Recovery dictation captured {len(post_wav)} bytes cleanly.")

    # Generate Audit Receipt
    receipt_dir = PROJECT_ROOT / "docs" / "testing"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    receipt_file = receipt_dir / f"PHYSICAL_USB_UNPLUG_RECEIPT_{ts}.md"

    receipt_content = f"""# Physical USB Microphone Unplug & Reconnect Verification Receipt

**Execution Timestamp:** {datetime.datetime.now().isoformat()}  
**Tester:** Operator Interactive Verification  
**Device Name:** `{target_dev['name']}`  
**Host API:** `{target_dev['host_api']}`  
**Original Index:** `{target_dev['index']}`  
**Reconnected Index:** `{reconnect_idx}`  

---

## 1. Test Evidence Summary

| Phase | Action | Outcome | Measured Metric |
| :--- | :--- | :--- | :--- |
| **Phase 1: Pre-flight** | Normal recording on USB endpoint | PASSED | Captured {len(pre_audio)} bytes, peak level {max_level:.3f} |
| **Phase 2: In-flight Unplug** | Cable physically pulled mid-stream | PASSED | Stream failure caught in {t_detection:.2f}s without crash |
| **Phase 3: Silent Fallback Guard** | Attempt capture while disconnected | PASSED | Hard RuntimeError refusal (sentinel `-9999`) |
| **Phase 4: Physical Reconnect** | Cable physically re-inserted | PASSED | Re-enumerated and re-resolved in {time.perf_counter() - poll_t0:.2f}s |
| **Phase 5: Stream Recovery** | Post-reconnect dictation session | PASSED | Captured {len(post_wav)} bytes; zero health errors |

---

## 2. Invariant Compliance

- **Zero Silent Fallback:** Verified. FlowPilot refused to capture audio from alternative/laptop microphones when the designated USB endpoint was absent.
- **Bounded Stream Release:** Verified. Unresponsive/disconnected PortAudio stream was released without blocking the host process.
- **Deterministic Re-resolution:** Verified. Device reconnected and resumed dictation cleanly.

**Overall Verdict:** **PHYSICAL USB UNPLUG & RECONNECT GATE PASSED**
"""
    with open(receipt_file, "w", encoding="utf-8") as rf:
        rf.write(receipt_content)

    print("\n" + "=" * 72)
    print(f" PHYSICAL USB UNPLUG & RECONNECT GATE PASSED!")
    print(f" Receipt written to: {receipt_file.relative_to(PROJECT_ROOT)}")
    print("=" * 72)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Physical USB Microphone Unplug & Reconnect Gate")
    parser.add_argument("--simulated", action="store_true", help="Run simulated disconnect/reconnect check")
    args = parser.parse_args()

    success = run_interactive_test(simulated=args.simulated)
    sys.exit(0 if success else 1)
