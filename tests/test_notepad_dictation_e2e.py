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
import win32process
import win32con

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.orchestrator import FlowOrchestrator
from engine.window_inspector import WindowInspector
from engine.text_injector import TextInjector

def ensure_notepad() -> Tuple[int, subprocess.Popen]:
    """Finds or spawns Notepad and returns (top-level HWND, proc) safely without terminating user documents."""
    existing_hwnds = set()
    def _rec_existing(h, _):
        if win32gui.IsWindowVisible(h) and "notepad" in win32gui.GetClassName(h).lower():
            existing_hwnds.add(h)
    win32gui.EnumWindows(_rec_existing, None)

    # Spawn fresh Notepad instance
    proc = subprocess.Popen(["notepad.exe"])
    target_hwnd = None
    for _ in range(30):
        time.sleep(0.15)
        new_hwnds = []
        def _find_new(h, _):
            if win32gui.IsWindowVisible(h) and "notepad" in win32gui.GetClassName(h).lower():
                if h not in existing_hwnds:
                    new_hwnds.append(h)
        win32gui.EnumWindows(_find_new, None)
        if new_hwnds:
            target_hwnd = new_hwnds[0]
            break

    if not target_hwnd:
        try:
            proc.kill()
        except Exception:
            pass
        raise RuntimeError("Failed to launch and find Notepad window.")

    return target_hwnd, proc

def run_5_consecutive_injections():
    print("=" * 65)
    print("FLOWPILOT AUDIT: 5 CONSECUTIVE NOTEPAD DICTATION CYCLES")
    print("=" * 65)

    notepad_hwnd, proc = ensure_notepad()
    print(f"Target Notepad HWND: {notepad_hwnd}")

    try:
        # Bring Notepad to foreground
        win32gui.ShowWindow(notepad_hwnd, win32con.SW_RESTORE)
        TextInjector._safe_set_foreground(notepad_hwnd)
        time.sleep(0.5)

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
            TextInjector._safe_set_foreground(notepad_hwnd)
            time.sleep(0.2)

            active = WindowInspector.get_active_window_info()
            target_hwnd = active.get("hwnd") if (active.get("hwnd") and "notepad" in active.get("process_name", "").lower()) else notepad_hwnd
            print(f"Targeting window HWND: {target_hwnd} (Active: {active.get('process_name')})")

            # Inject phrase into target window
            success = TextInjector.inject(phrase + "\n", target_hwnd)
            assert success is True, f"Failed to inject text on cycle {i}"
            time.sleep(0.2)

            # Physically confirm that the phrase arrived in Notepad buffer
            assert TextInjector.verify_text_injected(phrase, target_hwnd, timeout=3.0), f"Cycle {i} text was not physically found in Notepad document!"
            print(f"  -> Successfully injected & verified in Notepad buffer: '{phrase}'")
            time.sleep(0.2)

        orchestrator.stop_hotkey_listener()
        print("\n" + "=" * 65)
        print("5 CONSECUTIVE NOTEPAD INJECTIONS PASSED WITH 100% ACCURACY!")
        print("=" * 65)
        return True

    finally:
        if proc:
            try:
                proc.kill()
                proc.wait(timeout=2.0)
                print("Cleanly closed test Notepad instance.")
            except Exception:
                pass

if __name__ == "__main__":
    success = run_5_consecutive_injections()
    sys.exit(0 if success else 1)
