"""
FlowPilot State Machine & Robustness Regression Test Suite
Validates the explicit 9-state machine, rapid shortcut re-activation,
stop-pending queues, cancellation, and error recovery.
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.orchestrator import FlowOrchestrator, AppState

# Budget for waiting on the orchestrator to finish a dictation.
#
# The first transcription in a process pays the lazy model load, which the
# runner itself documents as part of the measured time ("first decode
# includes lazy model load"). On a cold model that load alone was 10.00s on
# this host, against a previous 10.0s budget, so the wait expired at exactly
# the moment the work finished. The budget now covers a cold start with
# headroom instead of racing it.
PROCESS_TIMEOUT = 60.0

def test_explicit_state_machine():
    print("=" * 65)
    print("TEST: FLOWPILOT EXPLICIT 9-STATE MACHINE & TRANSITIONS")
    print("=" * 65)

    events_received = []
    def on_change(payload):
        events_received.append(payload)

    orch = FlowOrchestrator(on_state_change=on_change)
    assert orch.state == AppState.IDLE, f"Initial state must be IDLE, got {orch.state}"
    print("[1] Initial state verified as IDLE.")

    # 1. Test transition to STARTING_RECORDING and RECORDING
    print("\n[Phase 1] Triggering start_dictation...")
    orch.start_dictation()
    assert orch.state in (AppState.STARTING_RECORDING, AppState.RECORDING)
    print(f"  -> State immediately transitioned to: {orch.state}")

    # Wait for recorder to become live (RECORDING)
    t0 = time.time()
    while orch.state != AppState.RECORDING and time.time() - t0 < 3.0:
        time.sleep(0.05)
    assert orch.state == AppState.RECORDING, f"Expected RECORDING, got {orch.state}"
    print(f"  -> Microphone stream live, state: {orch.state} ({time.time() - t0:.2f}s)")

    # 2. Test duplicate start activation while already recording (must be ignored)
    print("\n[Phase 2] Triggering second start while recording...")
    orch.start_dictation()
    assert orch.state == AppState.RECORDING, "Duplicate start must not alter RECORDING state"
    print("  -> Duplicate start safely ignored, state preserved as RECORDING.")

    # 3. Test stop dictation
    print("\n[Phase 3] Triggering stop_dictation_and_process...")
    time.sleep(0.5)  # Record 0.5s of real mic audio
    orch.stop_dictation_and_process()
    assert orch.state in (AppState.STOPPING_RECORDING, AppState.TRANSCRIBING, AppState.INSERTING_TEXT, AppState.SUCCESS, AppState.IDLE)
    print(f"  -> Stop triggered, state transitioned to: {orch.state}")

    # Wait for processing to complete and return to IDLE
    t0 = time.time()
    while orch.state not in (AppState.IDLE, AppState.SUCCESS) and time.time() - t0 < PROCESS_TIMEOUT:
        time.sleep(0.1)
    print(f"  -> Processing completed in {time.time() - t0:.2f}s, current state: {orch.state}")

    # Wait for auto-transition to IDLE if in SUCCESS
    if orch.state == AppState.SUCCESS:
        time.sleep(1.0)
    assert orch.state == AppState.IDLE, f"Expected IDLE after processing, got {orch.state}"
    print("  -> Returned to IDLE successfully.")

    # 4. Test Stop-while-Starting Queue (_stop_pending)
    print("\n[Phase 4] Testing rapid press-press (stop requested while starting)...")
    orch.start_dictation()
    # Immediately call toggle (which queues stop because state is STARTING_RECORDING)
    orch.toggle_dictation()
    assert orch._stop_pending is True or orch.state in (AppState.STOPPING_RECORDING, AppState.TRANSCRIBING, AppState.IDLE)
    print(f"  -> Stop successfully queued/processed during initialization (_stop_pending={orch._stop_pending})")

    # Wait for it to settle back to IDLE
    t0 = time.time()
    while orch.state not in (AppState.IDLE, AppState.SUCCESS) and time.time() - t0 < PROCESS_TIMEOUT:
        time.sleep(0.1)
    if orch.state == AppState.SUCCESS:
        time.sleep(1.0)
    assert orch.state == AppState.IDLE, f"Expected IDLE, got {orch.state}"
    print("  -> Settled cleanly to IDLE without deadlock.")

    # 5. Test Emergency Cancellation
    print("\n[Phase 5] Testing emergency cancellation during recording...")
    orch.start_dictation()
    time.sleep(0.3)
    orch.cancel_dictation()
    assert orch.state in (AppState.CANCELLED, AppState.IDLE)
    print(f"  -> Cancelled cleanly, state: {orch.state}")
    time.sleep(0.6)
    assert orch.state == AppState.IDLE
    print("  -> Reset to IDLE after cancellation.")

    # 6. Test Multiple Rapid Cycles (5 Cycles)
    print("\n[Phase 6] Testing 5 rapid back-to-back dictation cycles...")
    for cycle in range(1, 6):
        orch.start_dictation()
        t0 = time.time()
        while orch.state != AppState.RECORDING and time.time() - t0 < 2.0:
            time.sleep(0.02)
        time.sleep(0.4)
        orch.stop_dictation_and_process()
        t0 = time.time()
        while orch.state not in (AppState.IDLE, AppState.SUCCESS) and time.time() - t0 < PROCESS_TIMEOUT:
            time.sleep(0.05)
        # Verify user can immediately start next cycle from SUCCESS
        if orch.state == AppState.SUCCESS:
            orch.start_dictation()
            t0 = time.time()
            while orch.state != AppState.RECORDING and time.time() - t0 < 2.0:
                time.sleep(0.02)
            time.sleep(0.3)
            orch.stop_dictation_and_process()
            t0 = time.time()
            while orch.state not in (AppState.IDLE, AppState.SUCCESS) and time.time() - t0 < PROCESS_TIMEOUT:
                time.sleep(0.05)
        # Ensure settled to IDLE
        t0 = time.time()
        while orch.state != AppState.IDLE and time.time() - t0 < PROCESS_TIMEOUT:
            time.sleep(0.05)
        print(f"  -> Cycle {cycle}/5 completed successfully.")

    orch.stop()
    print("\n[RESULT] State Machine & Robustness Test PASSED 100%.")
    return True

if __name__ == "__main__":
    import traceback
    try:
        success = test_explicit_state_machine()
        sys.exit(0 if success else 1)
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)
