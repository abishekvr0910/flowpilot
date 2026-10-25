# FlowPilot — Technical Hypothesis Register & Reliability Analysis

## 1. Executive Overview

The Hypothesis Register tracks suspected failure modes, edge-case vulnerability vectors, architectural tensions, and behavioral anomalies within FlowPilot. Each entry defines a formal technical hypothesis, observed evidence, reproduction experiment, engineering mitigation, and current verification status.

---

## 2. Hypothesis Index

| ID | Title | Domain | Risk Level | Status |
|:---:|---|---|:---:|:---:|
| **H-001** | Electron Clipboard Restoration Race Condition | Text Injection / Clipboard | HIGH | **Validated & Mitigated** |
| **H-002** | Terminal Raw Mode Control Chord Collision (`^V`) | Terminal Injection | MEDIUM | **Validated & Mitigated** |
| **H-003** | Windows UIPI Cross-Integrity Keystroke Dropping | Security / OS Isolation | HIGH | **Validated & Mitigated** |
| **H-004** | Indic Script Transliteration Degradation under Low SNR | Multilingual STT | MEDIUM | **Validated & Mitigated** |
| **H-005** | Audio Hardware Disconnect Thread Hang | Audio Capture / Sounddevice | HIGH | **Validated & Mitigated** |
| **H-006** | Transient Window Activation Null Focus Gap (`HWND 0`) | Focus / Foreground | HIGH | **Validated & Mitigated** |
| **H-007** | Silero VAD Soft Fricative & Pause Truncation | Voice Activity Detection | MEDIUM | **Validated & Mitigated** |
| **H-008** | Local LLM Voice Command Inference Contention | Local Inference / CPU Load | MEDIUM | **Validated & Mitigated** |

---

## 3. Detailed Hypothesis Records

### H-001: Electron Event Loop Clipboard Restoration Race Condition
- **Statement:** In JavaScript-driven GUI frameworks (Electron, Chromium, Slack, VS Code), DOM paste handling is dispatched asynchronously through the V8 event loop. If FlowPilot restores the user's previous clipboard contents too quickly (e.g., standard 500ms delay), the target application processes the paste event *after* the clipboard has reverted, pasting the user's old clipboard data rather than the dictated text.
- **Failure Mode:** User sees stale clipboard text (or partial dictation) pasted into Slack or VS Code.
- **Observed Evidence:** Early tests showed VS Code occasionally receiving prior copied snippets when CPU load exceeded 70%.
- **Validation Test:** `tests/test_text_injector.py::test_slow_app_timing_and_dwell`.
- **Mitigation Strategy:**
  1. Classify Electron and Chromium executables into `SLOW_APP_PROCESSES`.
  2. Increase clipboard hold duration to `3.5 seconds` (`clipboard_hold_sec = 3.5`).
  3. Increase key dwell time to `40ms` (`key_dwell_sec = 0.040`).
  4. Track Win32 clipboard sequence numbers (`GetClipboardSequenceNumber`) to prevent restoring if the user copies new text during the hold window.
- **Status:** **Validated & Mitigated**.

---

### H-002: Terminal Raw Mode Control Chord Collision (`Ctrl+V` vs `^V`)
- **Statement:** Console host windows (`cmd.exe`, `powershell.exe`) and terminal emulators running in raw character mode interpret `Ctrl+V` (ASCII `0x16`) as a synchronous control character or literal escape sequence rather than a clipboard paste command.
- **Failure Mode:** Terminal displays `^V` on the command line instead of inserting dictated shell commands.
- **Observed Evidence:** Discovered in command prompts and legacy console windows where `Ctrl+V` is not intercepted by Windows Terminal's keymap.
- **Validation Test:** Unit test verification of `is_legacy_console` and terminal process detection.
- **Mitigation Strategy:**
  1. Detect console window classes (`ConsoleWindowClass`) and terminal processes (`TERMINAL_APP_PROCESSES`).
  2. Auto-route paste dispatches to `Shift+Insert` keystroke chords, which are universally honored by terminals across Windows Console Host, Windows Terminal, ConEmu, PuTTY, and Mintty.
  3. Provide direct `SendInput` Unicode typing fallback (`KEYEVENTF_UNICODE`) bypassing the clipboard entirely.
- **Status:** **Validated & Mitigated**.

---

### H-003: Windows UIPI Cross-Integrity Keystroke Dropping
- **Statement:** Under Windows User Interface Privilege Isolation (UIPI), standard-integrity processes are forbidden from posting window messages (`WM_PASTE`) or injecting keystrokes into higher-integrity (Administrator) windows.
- **Failure Mode:** Dispatched keystrokes are silently discarded by the Windows kernel; text never appears in the elevated window, and the user's clipboard remains altered.
- **Observed Evidence:** Running FlowPilot as a standard user while targeting an elevated PowerShell or Administrator Notepad produced no text insertion.
- **Validation Test:** `tests/test_target_verification_modern_apps.py` and `target_has_higher_integrity()` checks.
- **Mitigation Strategy:**
  1. Query process token integrity level before executing clipboard paste or SendInput.
  2. Refuse to dispatch keystrokes to higher-integrity targets.
  3. Return `InjectionStatus.FAILED_RECOVERY_AVAILABLE`.
  4. Preserve text in recovery buffer and guide user with amber HUD banner: *"Target is running as Administrator. Use Copy Last (Shift+Alt+X) and paste manually."*
- **Status:** **Validated & Mitigated**.

---

### H-004: Indic Script Transliteration Degradation under Low SNR
- **Statement:** Quantized multilingual Whisper models (int8 `small`) experience phoneme drift and script confusion when processing South Asian languages (Hindi, Tamil) in the presence of background acoustic noise (SNR < 12 dB), resulting in Devanagari/Latin script mixing or hallucinated phonetic transliterations.
- **Failure Mode:** Dictation in Hindi outputs garbled Romanized Hinglish or mixed-script tokens rather than clean native Devanagari script.
- **Observed Evidence:** Documented in `tests/test_multilingual_speech_reality.py` under simulated cafeteria noise.
- **Validation Test:** `tests/test_multilingual_validation.py` and `tests/test_multilingual_speech_reality.py`.
- **Mitigation Strategy:**
  1. Implement unicode script validation checking character block boundaries (Devanagari: `U+0900`–`U+097F`, Tamil: `U+0B80`–`U+0BFF`).
  2. Inject language-specific domain prompt context into Whisper's initial prompt tokens.
  3. Surface model status badges in Settings Dialog and Setup Wizard verifying that the verified 244M weights (`models/faster-whisper-small/model.bin`) exist locally before permitting Indic dictation.
- **Status:** **Validated & Mitigated**.

---

### H-005: Audio Hardware Disconnect Thread Hang
- **Statement:** If the active USB microphone is physically unplugged or disconnected by the OS power manager while the `sounddevice` / PortAudio stream is active, the recording callback may hang indefinitely or enter a busy spin loop if driver notifications are dropped.
- **Failure Mode:** FlowPilot freezes in `RECORDING` state; HUD does not respond to hotkey release; CPU spikes to 100% on one core.
- **Observed Evidence:** Addressed in `engine/audio_recorder.py` and verified by device unplug stress testing.
- **Validation Test:** `tests/test_audio_devices.py` and bounded stream duration tests in `tests/test_pilot_reliability.py`.
- **Mitigation Strategy:**
  1. Enforce strict timeout bounds (1.5s max silence, 60s hard dictation ceiling) in the orchestrator state machine.
  2. Guard PortAudio stream close calls with non-blocking worker threads.
  3. Implement persistent audio input device resolution in `AudioDeviceManager` to automatically detect device arrival/removal and fall back gracefully to the Windows Default Endpoint.
- **Status:** **Validated & Mitigated**.

---

### H-006: Transient Window Activation Null Focus Gap (`HWND 0`)
- **Statement:** When an end-user switches applications rapidly (e.g. `Alt+Tab`) or opens a modal dialog, Windows transitions through an intermediate state where `GetForegroundWindow()` returns `0` (`NULL`) for 10–50 milliseconds. Treating `HWND 0` as a valid foreground target results in dropped keystrokes or unintended window activation.
- **Failure Mode:** Text injection occurs during the focus gap; keystrokes are lost or sent to whichever window happens to gain focus milliseconds later.
- **Observed Evidence:** Discovered during rapid multi-window dictation switching tests.
- **Validation Test:** `tests/test_text_injector.py::test_focus_loss_after_staging_preserves_clipboard_and_recovery`.
- **Mitigation Strategy:**
  1. Implement `_resolve_verified_foreground(target_hwnd, max_attempts=5, delay=0.02)`.
  2. Poll up to 100ms for transient activation to settle.
  3. If focus remains `0` or switches to an unrelated window, abort the paste, restore the clipboard, retain the text in the recovery buffer, and notify the user via the amber recovery HUD banner.
- **Status:** **Validated & Mitigated**.

---

### H-007: Silero VAD Soft Fricative & Pause Truncation
- **Statement:** Voice Activity Detection (VAD) algorithms configured with aggressive speech threshold cutoffs (e.g., threshold > 0.6) prematurely truncate soft terminal consonants, unvoiced fricatives (e.g., `/s/`, `/f/`, `/th/`), or natural mid-sentence pauses, clipping the tail of dictated phrases.
- **Failure Mode:** Dictation drops trailing words or cuts off the beginning of spoken sentences.
- **Observed Evidence:** Truncated phrases observed when dictation speech threshold was set above 0.55 without pre-padding.
- **Validation Test:** `tests/test_silero_vad_resolution.py` and audio chunk analysis in `tests/test_audio.py`.
- **Mitigation Strategy:**
  1. Set Silero VAD threshold to a balanced `0.45`.
  2. Implement a 300ms pre-speech audio buffer and a 500ms post-speech hangover window before triggering automatic silence cutoff.
  3. In Push-to-Talk mode, disable automatic silence cutoff entirely, relying strictly on hotkey release for exact user intent.
- **Status:** **Validated & Mitigated**.

---

### H-008: Local LLM Voice Command Inference Contention
- **Statement:** Running local GGUF/llama.cpp inference concurrently with CTranslate2 Whisper transcription on consumer CPU hardware (4–8 cores) saturates compute threads and memory bandwidth, causing severe latency spikes (> 5,000ms) that degrade the interactive desktop experience.
- **Failure Mode:** System UI stutters; dictation latency jumps from 660ms to 6,000ms; audio capture buffer overruns.
- **Observed Evidence:** Measured in experimental LLM rewriting suites when concurrency was unconstrained.
- **Validation Test:** `tests/test_voice_command_and_llm.py` and thread allocation tests in `tests/test_stt.py`.
- **Mitigation Strategy:**
  1. Enforce strict sequential pipeline execution: STT transcription finishes and unloads/yields CPU before any LLM command rewrite begins.
  2. Cap CTranslate2 CPU threads to `max(1, os.cpu_count() - 2)`.
  3. Set local LLM inference to lowest thread priority (`THREAD_PRIORITY_BELOW_NORMAL`) to ensure PySide6 desktop UI and audio capture remain completely responsive.
- **Status:** **Validated & Mitigated**.
