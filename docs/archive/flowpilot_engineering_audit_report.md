# FlowPilot Engineering Audit & Verification Report (v2.0 Native Desktop)

> **Historical snapshot - superseded.** Retained for provenance only. Do not use this document as current instructions, test status, performance proof, legal/compliance advice, or up-to-date competitor information. See the [archive index](README.md) for current sources.

**Date:** October 14, 2026  
**Target:** FlowPilot Audio Intelligence Application (`<workspace-root>`)  
**Audit Methodology:** Empirical, evidence-based diagnostic verification across all hardware, OS, speech recognition, window management, and native GUI layers.

---

## 1. Executive Summary

A comprehensive forensic audit of the FlowPilot application was conducted to discover why users experienced failures with global hotkeys and audio dictation. Rather than speculating or using mocked unit tests, every subsystem was empirically tested, diagnosed, and repaired.

**Key Accomplishments in v2.0:**
* **Native Win32 Global Hotkeys:** Replaced unreliable `pynput` low-level keyboard hooks (`WH_KEYBOARD_LL`) with native Win32 `RegisterHotKey` backed by a dedicated message pump. Windows kernel handles keystrokes globally, completely bypassing hook timeouts and UAC drops.
* **Native Desktop Application (Flow Pill):** Eliminated the browser dependency. Built a frameless, translucent, always-on-top PySide6 Floating HUD ("Flow Pill") and System Tray presence.
* **Focus-Preserving Floating HUD:** Applied native Win32 `WS_EX_NOACTIVATE (0x08000000)` to ensure that clicking the microphone button never steals focus from the user's active editor (Notepad, VS Code, Word, Chrome).
* **Comprehensive 9-Test Audit Suite:** **9 / 9 automated test suites passed (100% pass rate, 25.38s total test time).**
* **Empirical 5-Cycle Notepad Dictation:** Verified 5 consecutive cycles of text injection directly into Notepad without errors.

---

## 2. Complete Verified Defect Inventory

| ID | Component | Defect Description | Root Cause | Implemented Fix | Verification Test |
|---|---|---|---|---|---|
| **DEF-01** | Process / Port | Port `8765` locked; server crashing with `Errno 10048` (`socket in use`). | Zombie Python process (`PID 33016`) remained running in background. | Terminated `PID 33016` using `Stop-Process -Force`. Added clean port validation. | Confirmed via `netstat -ano \| findstr :8765`. |
| **DEF-02** | STT Engine | Silent crash during speech transcription: `RuntimeError: Library cublas64_12.dll is not found`. | `faster-whisper` defaulted to `device="auto"`, which tried to load NVIDIA CUDA 12 without runtime DLLs. | Explicitly pinned local Whisper inference to **CPU INT8 mode** (`device="cpu", compute_type="int8"`). | Automated test `tests/test_stt.py` passed in 4.27s. |
| **DEF-03** | Hotkey Hook Dropping | `pynput` listener missed keystrokes across applications; failed live probe test. | Windows `WH_KEYBOARD_LL` hooks time out (`LowLevelHooksTimeout`) or get dropped when message loops run in worker threads. | Built `engine/hotkey_service.py` using native Win32 **`RegisterHotKey`** with dedicated thread message loop. | Automated test `tests/test_win32_hotkey.py` passed in 0.55s. |
| **DEF-04** | Hotkey Normalizer | `Ctrl + Alt + Space` never triggered in `pynput`. | `normalize_key()` omitted `Key.alt`, `Key.alt_l`, and `Key.alt_r`, leaving them as unhandled object strings. | Added `MOD_ALT`, `MOD_CONTROL`, `MOD_SHIFT` bitmask parsing in `hotkey_service.py`. | Automated test `tests/test_hotkey.py` passed in 2.03s. |
| **DEF-05** | Audio Ducker | Background media did not mute; logged `[WinError -2147221008] CoInitialize has not been called`. | Windows Core Audio COM interface (`pycaw`) requires thread-local COM initialization in worker threads. | Added `comtypes.CoInitialize()` inside `start_ducking()` and `stop_ducking()`. | Automated test `tests/test_audio_ducker.py` passed in 1.05s. |
| **DEF-06** | Text Injector Focus | Foreground focus failure: `pywintypes.error: (5, 'SetForegroundWindow', 'Access is denied')`. | Windows UIPI and foreground lock policies block background processes from calling `SetForegroundWindow` on target apps. | Implemented `AttachThreadInput`, `AllowSetForegroundWindow(-1)`, and `SwitchToThisWindow` focus restoration. | Automated test `tests/test_text_injector.py` passed in 2.31s. |
| **DEF-07** | Hotkey Collision | Shortcut conflict with installed Wispr Flow software (`Ctrl + Win`). | `Ctrl + Win` was intercepted by the pre-existing Wispr Flow process. | Removed `Ctrl + Win` completely. Dedicated FlowPilot to `Ctrl + Shift + Space`, `Ctrl + Alt + Space`, and `F9`. | Validated in `tests/test_hotkey.py`. |
| **DEF-08** | Browser Dependency | Web dashboard required user to switch tabs to interact. | Architecture relied on localhost web server and Chrome browser tabs. | Migrated to native desktop app (`desktop_app.py`, `ui/floating_hud.py`, `ui/tray_manager.py`). | Automated test `tests/test_desktop_app.py` passed in 2.61s. |
| **DEF-09** | HUD Focus Stealing | Clicking floating mic button steals focus from target editor. | Standard Qt frameless windows become the active window when clicked, causing text paste to fail. | Applied Win32 extended style **`WS_EX_NOACTIVATE (0x08000000)`** to the HUD window. | Verified in `tests/test_notepad_dictation_e2e.py`. |
| **DEF-10** | End-to-End Dictation | Sequential multi-cycle dictation untested under real conditions. | No automated test simulated repeated user dictation cycles into an active text editor. | Created `tests/test_notepad_dictation_e2e.py` verifying 5 consecutive dictation cycles into Notepad. | 5/5 cycles injected into Notepad (100% accuracy, 6.54s). |

---

## 3. Automated Audit Suite Results (9/9 Passed)

Executed via [`tests/run_all_tests.py`](../../tests/run_all_tests.py):

```text
======================================================================
           FLOWPILOT AUTOMATED AUDIT SUITE EXECUTION
======================================================================

--- Running: Microphone & Audio Capture (tests/test_audio.py) ---
Status: PASSED (2.64s)

--- Running: Local Whisper Speech-to-Text Model (tests/test_stt.py) ---
Status: PASSED (4.27s)

--- Running: Text Injection & Clipboard Safety (tests/test_text_injector.py) ---
Status: PASSED (2.31s)

--- Running: Windows Audio Ducking & Error Recovery (tests/test_audio_ducker.py) ---
Status: PASSED (1.05s)

--- Running: UI REST API & WebSocket Protocol (tests/test_api_and_websocket.py) ---
Status: PASSED (3.38s)

--- Running: Global Hotkey Resolution & Normalization (tests/test_hotkey.py) ---
Status: PASSED (2.03s)

--- Running: Win32 RegisterHotKey & Message Loop (tests/test_win32_hotkey.py) ---
Status: PASSED (0.55s)

--- Running: Native PySide6 Desktop HUD & Tray Lifecycle (tests/test_desktop_app.py) ---
Status: PASSED (2.61s)

--- Running: End-to-End 5-Cycle Notepad Dictation (tests/test_notepad_dictation_e2e.py) ---
Status: PASSED (6.54s)

======================================================================
                    AUDIT SUMMARY RESULTS
======================================================================
[PASS] Microphone & Audio Capture                    (2.64s)
[PASS] Local Whisper Speech-to-Text Model            (4.27s)
[PASS] Text Injection & Clipboard Safety             (2.31s)
[PASS] Windows Audio Ducking & Error Recovery        (1.05s)
[PASS] UI REST API & WebSocket Protocol              (3.38s)
[PASS] Global Hotkey Resolution & Normalization      (2.03s)
[PASS] Win32 RegisterHotKey & Message Loop           (0.55s)
[PASS] Native PySide6 Desktop HUD & Tray Lifecycle   (2.61s)
[PASS] End-to-End 5-Cycle Notepad Dictation          (6.54s)
----------------------------------------------------------------------
Total Test Time: 25.38s | Overall Verdict: ALL TESTS PASSED
======================================================================
```

---

## 4. Operational Instructions

To launch the native desktop application:
* Double-click [`FlowPilot.bat`](../../FlowPilot.bat), or
* Run `python desktop_app.py`.

The Flow Pill will float at the bottom center of your screen. Pressing **`Ctrl + Shift + Space`** or **`F9`** or clicking the mic icon starts recording and mutes background audio; pressing it again pastes the transcribed text into Notepad, VS Code, Word, or Chrome.
