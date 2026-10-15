"""
FlowPilot Session Lifecycle & Ownership Regression Tests
Verifies explicit DictationSession tokens, legal/illegal state transitions,
cancellation guards, and safe ducking restoration.
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.session import DictationSession, SessionState, LEGAL_TRANSITIONS
from engine.orchestrator import FlowOrchestrator, AppState

def test_session_state_machine_transitions():
    print("=" * 65)
    print("TEST: DICTATION SESSION STATE MACHINE TRANSITIONS")
    print("=" * 65)

    session = DictationSession(target_window_info={"process_name": "notepad.exe", "hwnd": 1234})
    assert session.session_id.startswith("fp-sess-")
    assert session.state == SessionState.IDLE
    assert not session.is_cancelled

    # 1. Legal transition: IDLE -> RECORDING
    assert session.transition_to(SessionState.RECORDING) is True
    assert session.state == SessionState.RECORDING
    assert session.is_active() is True

    # 2. Illegal transition: RECORDING -> INJECTING (skipping FINALIZING/TRANSCRIBING/VALIDATING)
    assert session.transition_to(SessionState.INJECTING) is False
    assert session.state == SessionState.RECORDING

    # 3. Legal progression: RECORDING -> FINALIZING -> TRANSCRIBING -> VALIDATING -> INJECTING -> SUCCESS
    assert session.transition_to(SessionState.FINALIZING) is True
    assert session.transition_to(SessionState.TRANSCRIBING) is True
    assert session.transition_to(SessionState.VALIDATING) is True
    assert session.transition_to(SessionState.INJECTING) is True
    assert session.transition_to(SessionState.SUCCESS) is True
    assert session.is_terminal() is True

    # 4. Reset to IDLE
    assert session.transition_to(SessionState.IDLE) is True
    assert session.state == SessionState.IDLE
    print("[PASS] Legal and illegal state transitions correctly validated.")


def test_session_cancellation_guards():
    print("\n" + "=" * 65)
    print("TEST: DICTATION SESSION CANCELLATION GUARDS")
    print("=" * 65)

    session = DictationSession()
    session.transition_to(SessionState.RECORDING)
    assert session.is_active() is True

    # Cancel session
    session.cancel("test_user_abort")
    assert session.is_cancelled is True
    assert session.state == SessionState.CANCELLED
    assert session.is_active() is False

    # Attempting to transition a cancelled session to TRANSCRIBING or INJECTING must fail
    assert session.transition_to(SessionState.TRANSCRIBING) is False
    assert session.transition_to(SessionState.INJECTING) is False
    assert session.state == SessionState.CANCELLED

    # Allowed transition from CANCELLED is back to IDLE
    assert session.transition_to(SessionState.IDLE) is True
    assert session.state == SessionState.IDLE
    print("[PASS] Session cancellation immediately blocks all downstream pipeline states.")


def test_session_timings():
    print("\n" + "=" * 65)
    print("TEST: MONOTONIC TIMING INSTRUMENTATION")
    print("=" * 65)

    session = DictationSession()
    session.record_timing("stt_ms", 123.456)
    session.record_timing("cleanup_ms", 45.678)
    assert session.timings["stt_ms"] == 123.46
    assert session.timings["cleanup_ms"] == 45.68
    print("[PASS] Monotonic stage timings recorded accurately.")


def test_orchestrator_session_ownership():
    print("\n" + "=" * 65)
    print("TEST: ORCHESTRATOR SESSION OWNERSHIP & CANCELLATION")
    print("=" * 65)

    orch = FlowOrchestrator()
    assert orch._current_session is None

    # Start dictation
    orch.start_dictation()
    session_1 = orch._current_session
    assert session_1 is not None
    assert session_1.session_id.startswith("fp-sess-")

    # Cancel dictation
    orch.cancel_dictation()
    assert session_1.is_cancelled is True
    assert session_1.state in (SessionState.CANCELLED, SessionState.IDLE)
    assert orch.state in (AppState.CANCELLED, AppState.IDLE)

    # Ducking must be stopped (wait up to 0.5s for async ducker thread)
    t0 = time.time()
    while orch.ducker.is_ducked and time.time() - t0 < 1.0:
        time.sleep(0.05)
    assert orch.ducker.is_ducked is False
    print("[PASS] Orchestrator session ownership, cancellation, and ducking safety confirmed.")


if __name__ == "__main__":
    test_session_state_machine_transitions()
    test_session_cancellation_guards()
    test_session_timings()
    test_orchestrator_session_ownership()
    print("\n=======================================================")
    print("ALL SESSION LIFECYCLE TESTS PASSED (4/4)")
    print("=======================================================")
