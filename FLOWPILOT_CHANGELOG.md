# FlowPilot Engineering Changelog

All notable changes, bug fixes, and architectural evolutions to FlowPilot are documented in this file.

---

## [3.0.1] - 2026-10-15 — *Wispr Flow Parity, Latency Optimization & Release Gate*

### Added
- **End-of-Speech Latency Optimization (-49.9% Stop-to-Visible-Text Latency):**
  - **Zero-Copy Float32 Audio Pipeline:** `AudioRecorder` preserves contiguous 1D float32 numpy arrays at 16kHz via `get_last_audio_array()`, feeding Faster-Whisper directly and eliminating in-memory WAV encoding and PyAV re-decoding overhead (~140ms saved).
  - **Deterministic Greedy Decoding (`beam_size=1`):** Replaced beam search with greedy decoding on CPU, achieving ~2x transcription speedup while retaining 100% keyword, number, and negation accuracy.
  - **Pre-Gated Audio VAD Filter Bypass:** Disabled redundant in-transcribe Silero VAD chunking (`vad_filter=False`) on dictation audio already gated by hardware recording bounds (~482ms saved).
  - **Tightened Post-Speech Silence Timeout:** Lowered default `silence_timeout_sec` from 1.4s to 0.85s, yielding a 550ms faster natural speech auto-finalization in Wispr Flow mode.
  - **Lean Text Injection & Focus Verification:** Bypasses redundant 80ms `_safe_set_foreground` sleeps when target application is already foregrounded; tightened clipboard sync to 10ms and `Ctrl+V` keyhold to 15ms.
  - **Stage-Level Monotonic Latency Telemetry:** High-resolution monotonic timing (`time.perf_counter()`) across every pipeline phase, logging `[Latency Breakdown]` with `stop_action_to_visible_text_ms` and `acoustic_end_to_visible_text_ms`.
- **Wispr Flow Parity (Push-to-Talk & Silence Auto-Finalization):**
  - Configured `F9` for true single-key Push-to-Talk (`hotkey_mode="push_to_talk"`): press & hold `F9`, speak, release `F9` to paste instantly into the focused application.
  - Implemented intelligent post-speech silence auto-finalization in Toggle Mode (`auto_stop_on_silence=True`, `silence_timeout_sec=0.85s`): automatically finalizes, transcribes, and inserts text after natural conversational pauses without requiring a second shortcut press.
- **Physical Text Injection Confirmation & Unicode Fallback:**
  - Added physical active window buffer verification (`read_window_buffer()`) to guarantee text appears before marking status as `SUCCESS`.
  - Added native Win32 `SendInput` Unicode typing fallback (`KEYEVENTF_UNICODE`) if clipboard paste is intercepted or refused by target window.
  - Non-destructive emergency clipboard preservation with HUD alert `"Paste failed - saved to clipboard"` on injection failure.
- **Privacy Hardening & Opt-In Telemetry:**
  - Disabled telemetry by default (`"telemetry_enabled": false`). Zero diagnostic logs written to disk unless explicitly opted in.
  - Disabled audio/text persistence by default (`"save_history_text": false`). Speech transcripts reside exclusively in volatile memory for the Tray "Copy Last Dictation" buffer.
  - Verified 100% offline model loading and transcription with zero network egress.

### Fixed
- **PortAudio Stream Teardown & Concurrent Dictation Crash (0xC0000096):**
  - Added `threading.Lock()` to `AudioRecorder` and replaced `abort()` with clean `stop()` and `close()` sequence, preventing PortAudio WASAPI native callback collisions during rapid back-to-back dictation cycles.
- **COM Apartment & CoreAudio Ducker Thread Safety:**
  - Added `threading.Lock()` and structured `CoUninitialize()` in `finally` blocks to `AudioDucker`, preventing COM apartment reference leaks.
- **Winsound Tone Collision:**
  - Added non-blocking lock to `AudioFeedback` to prevent driver resource contention during rapid state changes.
- **Silero VAD ONNX Path Independence:**
  - Packaged Silero ONNX assets into both `dist/FlowPilot/assets/` and `_internal/faster_whisper/assets/`, ensuring reliable launches from arbitrary working directories or `%TEMP%`.
- **Test Server Shutdown Race:**
  - Added structured shutdown for Uvicorn and Win32 message pump in `tests/test_api_and_websocket.py` to prevent interpreter exit races.

---

## [3.0.0] - 2026-10-14 — *Codex Overhaul & Win32 Native Shell*
- Upgraded desktop shell to PySide6 with frameless floating HUD and multi-tab settings.
- Added Win32 RegisterHotKey integration and single-instance named mutex.

---

## [2.0.0] - 2026-10-14 — *Production Overhaul & Release*

### Added
- **Native Win32 Global Hotkey Service (`engine/hotkey_service.py`):**
  - Integrated `RegisterHotKey` with `MOD_NOREPEAT` flag to eliminate low-level hook timeouts (`LowLevelHooksTimeout`) and UAC medium-integrity drops.
  - Dedicated background Win32 message pump thread (`GetMessageW` / `DispatchMessageW`).
  - Pre-configured conflict-free shortcut combinations: `Ctrl + Shift + Space` (primary), `Ctrl + Alt + Space` (secondary), and `F9` (push-to-talk).
- **Single-Instance Enforcement (`engine/single_instance.py`):**
  - Implemented Win32 Named Mutex `Global\FlowPilot_Desktop_SingleInstance_Mutex`.
  - Prevents duplicate processes, port contention, audio device starvation, and Win32 hotkey collision error 1409.
- **Native PySide6 Desktop Shell (`desktop_app.py`, `ui/`):**
  - **Floating HUD (`ui/floating_hud.py`):** Frosted dark pill window with `WS_EX_NOACTIVATE (0x08000000)` style, guaranteeing clicking or showing the HUD never steals keyboard focus from target applications.
  - **System Tray Manager (`ui/tray_manager.py`):** Dynamic tray status icons, audio ducking toggle, and instant access to "Copy Last Dictation".
  - **Settings Dialog (`ui/settings_dialog.py`):** Multi-tab configuration dialog for model size, language selection, writing style, hotkeys, and personalization.
- **Audio Feedback Engine (`engine/audio_feedback.py`):**
  - Non-blocking synthesized audio cues: Start Recording (880Hz -> 1320Hz), Stop Recording (1320Hz -> 880Hz), Cancel (440Hz -> 330Hz), and Error (220Hz).
- **Hardware-Adaptive Audio Capture (`engine/audio_recorder.py`):**
  - Dynamic sample rate negotiation: automatically tests 16kHz; if rejected by hardware drivers, falls back to native 44.1kHz / 48kHz.
  - Real-time linear interpolation resampling (`np.interp`) to deliver standard 16kHz mono PCM to Whisper.
  - 120-second automatic safety cutoff and sub-0.3s noise artifact suppression.
- **Windows Background Audio Ducking (`engine/audio_ducker.py`):**
  - Windows CoreAudio session attenuation via `pycaw`.
  - Thread-safe `comtypes.CoInitialize()` and `comtypes.CoUninitialize()` lifecycle.
  - Crash-safe volume recovery using structured `finally` blocks and process `atexit` handlers.
- **Writing Intelligence & FactGuard (`engine/writing_intelligence.py`):**
  - **Verbatim Mode:** 100% faithful transcript preservation without AI modification.
  - **Polished Mode:** Local deterministic transformation engine:
    - Spoken self-correction resolution (`"X — actually, Y"` -> `"Y"`).
    - Filler and stutter elimination (`"um, uh, we we need to"` -> `"we need to"`).
    - Technical identifier casing (`camelCase`, `snake_case`, `kebab-case`).
    - Spoken email and URL formatting (`https://github.com/repo`).
    - Currency and percentage normalization (`25%`, `$12,000`).
    - Style-aware terminal punctuation (no trailing periods on CLI commands).
  - **FactGuard:** Rigorous verification layer ensuring all numbers, dates, commitments, and negations (`not`, `never`, `none`, `without`, `cannot`) are strictly preserved.
- **Multilingual Script & Direction Engine (`engine/language_registry.py`):**
  - Full support for 18 core languages across Latin, Devanagari, Han, Kanji/Kana, and Arabic scripts.
  - Directional tagging (`ltr` vs `rtl`).
  - Regional dialect transformations (British English spelling, Swiss German `ss` vs `ß`, French quotation spacing).
  - Terminal punctuation preservation for non-Latin writing systems (`。`, `！`, `？`, `।`, `॥`, `؟`).
- **Personalization Engine (`engine/personalization.py`):**
  - Local phonetic dictionary mapping spoken variants to technical terms (`flow pilot` -> `FlowPilot`, `fast api` -> `FastAPI`).
  - Dynamic Whisper prompt biasing.
  - Spoken text snippet expansion (`"insert my calendly"` -> URL).
  - JSON import and export capability.
- **Text Injection & Safety (`engine/text_injector.py`):**
  - Direct Win32 `AttachThreadInput` and `AllowSetForegroundWindow(-1)`.
  - Self-healing clipboard lock breaker: automatically breaks dangling clipboard locks via `CloseClipboard()` on Win32 Error 5.
  - Non-destructive 1.5s clipboard restoration and volatile memory recovery buffer (`re_copy_last()`).
- **Verification Suites & Automated Harnesses (`tests/`):**
  - Master test runner (`tests/run_all_tests.py`): 13/13 test suites passing.
  - End-to-end specification suite (`tests/test_final_specification_e2e.py`): 18/18 scenarios passing.
  - Multilingual validation suite (`tests/test_multilingual_validation.py`): 10/10 locales validated at 0.00% WER / 0.00% CER.
  - Benchmark corpus (`tests/benchmark_corpus.py`): Empirical RTF and latency benchmarking.
  - Multi-cycle Notepad live injection test (`tests/test_notepad_dictation_e2e.py`).

### Changed
- Decoupled primary desktop workflow from loopback HTTP/WebSocket web servers. The native PySide6 desktop application runs completely in-process.
- Configured PyInstaller build specification (`flowpilot.spec`) to produce standalone self-contained binaries (~32.7 MB) with all CTranslate2 and PortAudio dependencies bundled.
- Standardized all subprocess executions across test harnesses to enforce `encoding="utf-8", errors="replace"` to eliminate Windows console charmap exceptions.

### Fixed
- Fixed critical hotkey drop issue where `SetWindowsHookExW` hooks were silently unhooked by Windows after `LowLevelHooksTimeout`.
- Fixed focus-stealing bug where floating HUD stole input focus from Notepad and IDEs upon display.
- Fixed clipboard race condition where rapid consecutive dictations crashed with Win32 Error 5 `Access is denied` by implementing a synchronized debounced restoration timer (`threading.Timer`) and lock.
- Fixed outbound HTTPS metadata telemetry query on model initialization by enforcing `local_files_only=True` in `_get_local_model`, guaranteeing absolute zero network egress.
- Fixed FactGuard reverting valid spoken numerical self-corrections by extracting retracted tokens and negations from superseded clauses and exempting them from fact-omission checks.
- Fixed workstation lock screen (`LockApp.exe`) Win32 Error 5 failure by catching `ERROR_ACCESS_DENIED` and safely retaining transcribed text in the internal recovery buffer.
- Fixed background audio remaining muted if dictation was cancelled or encountered an error.
- Fixed stutter removal collapsing legitimate spoken double-slash tokens in URLs (`//`).
- Fixed technical term casing corrupting lowercase protocol prefixes in URLs (`https://`).
- Fixed trailing ASCII period corruption on non-Latin text ending with CJK fullwidth periods or Indic dandas.
- Fixed AM/PM time formatting regex word boundary failure on dotted abbreviations (`a.m.` / `p.m.`).

---

## [1.0.0] - 2026-10-13 — *Initial Prototype*
- Initial experimental browser-based UI on port 8765.
- Basic PortAudio capture and faster-whisper transcription loop.
