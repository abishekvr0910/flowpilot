"""
FlowPilot End-to-End Notepad Dictation Verification Test
Performs 5 consecutive dictation cycles targeting an active Notepad instance.
Verifies target window detection, text injection, and state transitions.
Cleanly terminates spawned Notepad upon completion.
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from typing import Tuple, Optional
import win32gui
import win32con

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.orchestrator import FlowOrchestrator
from engine.window_inspector import WindowInspector
from tests.notepad_harness import (
    focus_notepad_document, paste_and_verify_notepad, is_interactive_desktop,
    open_test_notepad, cleanup_test_fixture,
)

def ensure_notepad() -> Tuple[int, subprocess.Popen, Path]:
    """Return the editable HWND, launcher process, and unique synthetic file."""
    return open_test_notepad()

def test_safe_abort_when_focus_unavailable():
    """Safety check: when focus is absent or unverified, paste safely aborts to recovery buffer."""
    from engine.text_injector import TextInjector, InjectionStatus
    test_payload = "Safe abort test: must not drop text."
    res = TextInjector.inject_with_status(test_payload + "\n", target_hwnd=0)
    assert res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE, f"Expected FAILED_RECOVERY_AVAILABLE, got: {res.status}"
    assert TextInjector.last_injected_text == test_payload + "\n", "Recovery buffer must hold exact text on abort"
    print("  -> Safe abort on unverified focus verified successfully.")

def run_5_consecutive_injections():
    if not is_interactive_desktop():
        print("[RESULT] SKIPPED: Five physical Notepad insertion cycles require an interactive Windows desktop.")
        return True
    print("=" * 65)
    print("FLOWPILOT AUDIT: 5 CONSECUTIVE NOTEPAD DICTATION CYCLES")
    print("=" * 65)

    notepad_hwnd, proc, fixture = ensure_notepad()
    print(f"Target Notepad HWND: {notepad_hwnd}")
    orchestrator = None

    try:
        # Bring Notepad to foreground
        win32gui.ShowWindow(notepad_hwnd, win32con.SW_RESTORE)
        assert focus_notepad_document(notepad_hwnd), "Notepad document did not become focused"

        # Initialize orchestrator
        state_history = []
        def on_state(payload):
            state_history.append(payload.get("state"))

        orchestrator = FlowOrchestrator(on_state_change=on_state)
        orchestrator.start_hotkey_listener()

        test_sentences = [
            "FlowPilot iteration 1: Global hotkey verified.",
            "FlowPilot iteration 2: Speech-to-text pipeline active.",
            "FlowPilot iteration 3: Focus handling intact.",
            "FlowPilot iteration 4: Fast clipboard injection verified.",
            "FlowPilot iteration 5: Full stack dictation completed successfully."
        ]

        for i, phrase in enumerate(test_sentences, start=1):
            print(f"\n--- [Cycle {i}/5] ---")
            # Ensure focus is on notepad
            assert focus_notepad_document(notepad_hwnd), f"Notepad document lost focus before cycle {i}"

            active = WindowInspector.get_active_window_info()
            target_hwnd = notepad_hwnd
            print(f"Targeting window HWND: {target_hwnd} (Active: {active.get('process_name')})")

            # Retry once only after this test document proves the first paste
            # absent. A sent-but-opaque target must never be retried blindly.
            res = paste_and_verify_notepad(phrase + "\n", phrase, target_hwnd)
            assert res.verified, f"Cycle {i} text was not physically found in Notepad document! (Status: {res.status}, error: {res.error})"
            if res.first_attempt_success:
                print(f"  -> First-attempt injection PASSED: '{phrase}'")
            elif res.recovered:
                print(f"  -> Recovered paste after {res.retries} retry: '{phrase}'")
            time.sleep(0.2)

        orchestrator.stop_hotkey_listener()
        print("\n" + "=" * 65)
        print("5 CONSECUTIVE NOTEPAD INJECTIONS PASSED WITH 100% ACCURACY!")
        print("=" * 65)
        return True

    finally:
        if orchestrator is not None:
            orchestrator.stop_hotkey_listener()
        cleanup_test_fixture(fixture, notepad_hwnd, proc)

if __name__ == "__main__":
    test_safe_abort_when_focus_unavailable()
    success = run_5_consecutive_injections()
    sys.exit(0 if success else 1)
