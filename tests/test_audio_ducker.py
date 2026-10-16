import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pycaw.pycaw import AudioUtilities
from engine.audio_ducker import AudioDucker

def test_audio_ducking():
    print("=" * 60)
    print("AUDIT TEST 4: AUDIO DUCKING & RESTORATION (NORMAL & ERROR)")
    print("=" * 60)

    try:
        speakers = AudioUtilities.GetSpeakers()
    except Exception as e:
        print(f"[RESULT] SKIPPED: No Windows audio endpoint volume found ({e}). Headless CI environment detected.")
        return True

    if not speakers or not getattr(speakers, "EndpointVolume", None):
        print("[RESULT] SKIPPED: No Windows audio endpoint volume found. Headless CI environment detected.")
        return True

    endpoint = speakers.EndpointVolume
    initial_mute = endpoint.GetMute()
    initial_vol = endpoint.GetMasterVolumeLevelScalar()
    print(f"Initial State -> Mute: {bool(initial_mute)}, Volume: {initial_vol * 100:.1f}%")

    ducker = AudioDucker(duck_mode="mute")

    # --- 1. Test Normal Ducking & Restoration ---
    print("\n[Phase 1] Testing Normal Ducking Cycle...")
    ducker.start_ducking()
    ducked_mute = endpoint.GetMute()
    print(f"During Ducking -> Mute: {bool(ducked_mute)}")
    if not ducked_mute:
        print("FAILED: Audio was not muted during ducking phase.")
        return False

    time.sleep(0.5)
    ducker.stop_ducking()
    restored_mute = endpoint.GetMute()
    restored_vol = endpoint.GetMasterVolumeLevelScalar()
    print(f"After Normal Restoration -> Mute: {bool(restored_mute)}, Volume: {restored_vol * 100:.1f}%")

    if bool(restored_mute) != bool(initial_mute):
        print("FAILED: Mute state was not restored after normal cycle.")
        return False
    if abs(restored_vol - initial_vol) > 0.01:
        print("FAILED: Master volume was not restored after normal cycle.")
        return False

    # --- 2. Test Exception/Error Safety ---
    print("\n[Phase 2] Testing Error Handling & Cleanup...")
    try:
        ducker.start_ducking()
        # Simulate an unexpected engine error during dictation
        raise RuntimeError("Simulated crash during speech transcription")
    except Exception as err:
        print(f"Caught simulated engine error: {err}")
    finally:
        ducker.stop_ducking()

    final_mute = endpoint.GetMute()
    final_vol = endpoint.GetMasterVolumeLevelScalar()
    print(f"After Error Recovery -> Mute: {bool(final_mute)}, Volume: {final_vol * 100:.1f}%")

    if bool(final_mute) != bool(initial_mute) or abs(final_vol - initial_vol) > 0.01:
        print("FAILED: Audio volume was left muted after simulated engine crash!")
        return False

    print("\n[RESULT] Audio ducking and fail-safe volume restoration PASSED.")
    return True

if __name__ == "__main__":
    success = test_audio_ducking()
    sys.exit(0 if success else 1)
