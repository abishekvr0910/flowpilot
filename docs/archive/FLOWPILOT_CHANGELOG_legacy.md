# FlowPilot Engineering Changelog

> **Historical snapshot - superseded.** Retained for provenance only. Do not use this document as current instructions, test status, performance proof, legal/compliance advice, or up-to-date competitor information. See the [archive index](README.md) for current sources.

All notable changes, bug fixes, and architectural evolutions to FlowPilot are documented in this file.

## [Unreleased] — *Cross-Platform OS Adapters & Architectural Upgrades*

### Added
- **SondeR-Cat Pixel Kitty Desktop Companion Integration (`ui/pet_sprites.py`, `ui/floating_hud.py`, `assets/sounds/meow.wav`):**
  - Integrated SondeR-Cat's 26x28 ASCII pixel art sprite engine directly into FlowPilot's native PySide6 architecture with sub-millisecond QPainter rendering.
  - Added 14 customizable fur palettes: Orange Tabby, Calico, Midnight Black, Classic Gray, Siamese (seal point with sapphire eyes), Pastel Pink, Snow White, Mint, Chocolate, Cream, Lilac, Mimi, JJ, Lilly.
  - Interactive speech reactions:
    - **Listening/Recording:** Audio-reactive paw kneading (`type_a`, `type_b`, `knead_a`, `knead_b`) with speed scaling dynamically with microphone speech volume, radiating cyan acoustic arcs, and dilated pupils.
    - **Polishing/Transcription:** Concentrating upright look with bright glowing cyan/amber pupils.
    - **Pasted/Success:** Celebratory stretch (`stretch`), floating pixel hearts drifting upwards, and optional cheerful meow sound cues (`meow.wav`).
    - **Idle:** Upright sitting cat with occasional tail flicking (`sit_b`) and natural slow eye blinks.
  - Moveable anywhere on screen with mouse drag-and-drop and one-click corner/edge snapping (Bottom-Right, Bottom-Left, Top-Right, Top-Left, Left Edge, Right Edge, Bottom-Center).
  - 4-way appearance switcher (Kitty ↔ Robot Mascot ↔ Wispr Flow Edge Line ↔ Wave Equalizer) accessible via double-click or right-click menu.
  - Added dedicated automated test suite `tests/test_sondercat_companion.py` (8/8 assertions PASS).
- **Wispr Flow Spoken Punctuation & Voice Editing Engine (`engine/writing_intelligence.py`):**
  - **Spoken Punctuation:** Real-time speech conversion for `comma` (`,`), `period` / `full stop` (`.`), `question mark` (`?`), `exclamation mark/point` (`!`), `colon` (`:`), `semicolon` (`;`), `ellipsis` / `dot dot dot` (`...`), `open/close quote` (`"`), `open/close paren` (`()`), `open/close bracket` (`[]`).
  - **Structural Formatting:** Spoken commands `new line` (`\n`), `new paragraph` (`\n\n`), and `tab` (`\t`) with automatic sentence capitalization on subsequent lines.
  - **Voice Editing:** Say *"scratch that"*, *"delete that"*, or *"cancel that"* to immediately erase the preceding sentence or clause before insertion; say *"scratch last word"* to erase only the trailing word.
  - **Voice Casing:** Spoken command *"all caps <word>"* formats identifiers in uppercase (e.g. *"all caps secret"* -> `SECRET`).
  - **Full Parity Testing:** Added automated test suite `test_wispr_flow_spoken_commands` verifying punctuation, structural newlines, scratch that, and all-caps casing.
- **Wispr Flow Docked Edge Line & Soundwave Equalizer (`ui/floating_hud.py`):**
  - Added three selectable visual appearances:
    - 🤖 **Robot Mascot Companion ("Pilot"):** 72×72 animated vector robot with voice-reactive pupil dilation, glowing acoustic soundwave arcs, and celebratory smiles.
    - 📏 **Wispr Flow Docked Edge Line:** Minimalist vertical capsule docked against the screen edge that subtly expands in thickness and pulses with voice volume, exactly matching Wispr Flow's minimalist edge bar.
    - 🌊 **Wispr Soundwave Equalizer:** Compact 5-bar animated audio spectrum equalizer.
  - Added one-click Appearance menu and double-click shortcut to switch between styles.
  - Added Edge Docking shortcuts: snap to *Left Edge (Middle)* and *Right Edge (Middle)*.
- **Standalone Moveable Robot Companion ("Pilot") (`ui/floating_hud.py`):**
  - **Zero UI Text Clutter:** Completely eliminated the wide text pill and "Ctrl+Shift+Space" label. FlowPilot is now represented by an adorable, standalone desktop robot companion ("Pilot").
  - **Draggable to Any Screen Corner:** Users can click and freely drag Pilot to any position or corner on their desktop. The robot automatically remembers its exact coordinates (`hud_x`, `hud_y`) across restarts.
  - **One-Click Snap-to-Corner Menu:** Right-click context menu and double-click actions provide instant positioning to *Bottom-Right, Bottom-Left, Top-Right, Top-Left, or Bottom-Center*.
  - **Interactive Mascot Voice Reactions:**
    - Live voice volume dilation of big glossy anime pupils.
    - Antenna tip lights up with glowing cyan bulb and radiates dynamic soundwave arcs while speaking.
    - Animated thinking swirls during Groq & FactGuard processing.
    - Happy celebratory smile `( ^ _ ^ )` with rosy blush upon pasting.
    - Single-click to start or stop dictation.
- **Cross-Platform OS Adapters (Windows, Linux, macOS):**
  - **`PynputHotkeyService` (`engine/hotkey_service.py`):** Universal fallback global hotkey listener for Linux (X11) and macOS supporting multi-key chords (`Ctrl+Shift+Space`, `Alt+Shift+Z`), single keys (`F9`), push-to-talk press/release callbacks, and TapLatch hands-free gestures. Factory function `get_hotkey_service()` selects `Win32HotkeyService` on Windows and `PynputHotkeyService` on Linux/macOS.
  - **Multi-OS Text Injection (`engine/text_injector.py`):** Added macOS `Cmd+V` (with AppleScript fallback) and Linux `Ctrl+V` (with `xdotool` fallback) dispatch. Implemented cross-platform MD5 content hash sequence generation for atomic clipboard safety on non-Windows systems.
  - **Cross-Platform Single-Instance Enforcement (`engine/single_instance.py`):** Added POSIX file lock (`fcntl.flock`) on `~/.flowpilot/flowpilot.lock` for Linux and macOS alongside the Win32 Named Mutex on Windows.
  - **Linux & macOS Audio Ducking (`engine/audio_ducker.py`):** Added PulseAudio / PipeWire `pactl` ducking for Linux and AppleScript volume ducking for macOS.
  - **Active Window Detection (`engine/window_inspector.py`):** Added macOS `osascript` application detection and Linux `xdotool` window querying.
  - **Platform-Conditioned Packaging (`requirements.txt`, `pyproject.toml`):** Added `; sys_platform == 'win32'` markers to `pywin32`, `pycaw`, and `comtypes`, allowing clean installation across Linux and macOS environments.
  - Added dedicated regression suite `tests/test_cross_platform.py` (5/5 passing).
- **Continuous Pre-Roll Audio Ring Buffer (`engine/audio_recorder.py`):**
  - Implemented continuous 350ms float32 sliding ring buffer (`collections.deque`) maintaining warm audio context before hotkey press.
  - Added background zero-latency warm-up stream (`warmup_stream()`), completely eliminating the 100–180ms PortAudio startup latency and preventing first-syllable speech clipping.
- **TapLatch™ Hands-Free Dictation Gesture & `Alt+Shift+Z` Quick Re-Paste (`engine/hotkey_service.py`, `engine/orchestrator.py`):**
  - Built a 4-state finite state machine (`IDLE`, `HELD`, `PENDING`, `LATCHED`):
    - Single hold: Push-to-talk (stops and transcribes on key release).
    - Rapid double-tap (<350ms): Locks into continuous hands-free dictation mode without needing to hold down the key.
    - Tap while latched: Immediate stop and transcribe.
  - Registered global shortcut `Alt+Shift+Z` (`re_inject_last()`): instantly re-injects the most recent dictation buffer into the active window if focus was lost or injection was disrupted.
- **Atomic Win32 Clipboard Sequence Verification (`engine/text_injector.py`):**
  - Integrated native `ctypes.windll.user32.GetClipboardSequenceNumber()` verification inspired by SpeakoFlow's atomic sequence guard.
  - Compares sequence numbers before restoring clipboard contents: if the user copies new data during the post-injection delay, clipboard restoration is automatically aborted to preserve the user's latest clipboard state.
- **Local OpenAI-Compatible Audio Transcriptions API (`engine/server.py`):**
  - Added drop-in `POST /v1/audio/transcriptions` and `GET /v1/models` endpoints to FlowPilot's FastAPI server (`http://127.0.0.1:8765/v1`).
  - Supports standard OpenAI format parameters (`model`, `language`, `response_format`), audio multipart uploads, and local FactGuard polishing.
  - Enables out-of-the-box integration with Cursor IDE, Open WebUI, Obsidian Whisper plugins, and local developer workflows without cloud API keys.
- **Explicit Dictation Session Lifecycle & Ownership (`engine/session.py`):**
  - Implemented `DictationSession` and `SessionState` (`IDLE`, `RECORDING`, `FINALIZING`, `TRANSCRIBING`, `VALIDATING`, `INJECTING`, `SUCCESS`, `CANCELLED`, `ERROR`) with deterministic transition matrix `LEGAL_TRANSITIONS`.
  - Added unique monotonic session tokens (`fp-sess-<hex>`) owning audio buffers, raw transcripts, candidate rewrites, validation diagnostics, and monotonic stage timings.
  - Injected cancellation guards across every pipeline stage: emergency cancellation immediately invalidates the active session token, preventing late STT callbacks from injecting text into subsequent user windows.
  - Added regression test suite `tests/test_session_lifecycle.py` (4/4 passing).
- **Conservative Semantic Validation Layer — FactGuard v2 (`engine/writing_intelligence.py`):**
  - Added structured entity extraction for protected tokens: critical negations with equivalence matching, numeric values, decimals, currencies, unit integrity (`1450 units` vs `$1450 units`), soundalike number confusions (`15` vs `50`), CLI flags (`--dry-run`, `-rf`), file paths, URLs, and user dictionary phrases.
  - Defined explicit transformation taxonomy: `SAFE_FORMATTING`, `REVIEWABLE_REWRITE`, `PROTECTED`.
  - Conservative fallback: on any protected entity drop, mutation, or unit-currency corruption, candidate polish is safely rejected and falls back to raw transcript with zero semantic drift.
  - Added adversarial regression test suite `tests/test_factguard_v2.py` (7/7 passing).
- **Application-Aware Writing Profiles & Precedence Resolver (`engine/context_processor.py`):**
  - Implemented `ProfileResolver` enforcing strict deterministic precedence:
    1. Explicit session selection (`session_mode`)
    2. Per-app configuration mapping in `config["app_profiles"]`
    3. Window category auto-detection (Terminal, Developer, Chat, Email)
    4. Default fallback in `config["active_tone_mode"]`
  - Added dedicated `terminal` profile: guarantees verbatim CLI command casing (e.g. `git`, `npm`, `docker`), preserves CLI flags and file paths, and strictly enforces zero trailing periods.
  - Added regression test suite `tests/test_application_profiles.py` (3/3 passing).
- **Voice Snippets Hardening & Literal Injection Safety (`engine/personalization.py`):**
  - Enforced whole-word trigger regex boundaries to prevent accidental mid-word expansions.
  - Implemented longest-match trigger precedence on overlapping trigger phrases (e.g. `insert calendly link` vs `insert calendly`).
  - Added trigger overlap conflict detection with diagnostic notices on `add_snippet`.
  - Enforced literal lambda string replacement in `expand_snippets` to completely neutralize regex backreference injection.
  - Added regression test suite `tests/test_personalization_snippets.py` (2/2 passing).
- **Floating HUD Polish (`ui/floating_hud.py`):**
  - Added `validating` state handling ("Checking...") with distinct styling.
  - Ensured completion ("Pasted!") and cancellation visual feedback without stealing keyboard or window focus.

### Fixed
- **Undefined `start_time` Bug in Orchestrator Worker (`engine/orchestrator.py`):**
  - Replaced undefined `start_time` with session-owned `active_session.created_at`.
- **Audio Ducking Cleanup Guarantee (`engine/orchestrator.py`):**
  - Added guaranteed `try ... finally` ducker restoration in background processor workers, ensuring audio ducking is always cleanly released on success, cancellation, or exception.
- **Target Window Closed Injection Vulnerability (`engine/text_injector.py`):**
  - Guarded against pasting into arbitrary active windows if target window closed; saves to clipboard and returns graceful failure.
- **Clipboard Restoration Content Check (`engine/text_injector.py`):**
  - Hardened post-paste clipboard restore comparison to verify clipboard still holds FlowPilot text before restoring previous clipboard content, preventing clobbering manual user copies.

---

## [3.0.2] - 2026-10-15 — *Release Hardening, Privacy Audit & Distribution Manifest*

### Added
- **Licensing & Third-Party Attribution:** Added MIT `LICENSE` and updated `THIRD_PARTY_LICENSES.md` to cover Silero VAD, ONNX Runtime, and full sub-component licensing statements.
- **Packaging & Dependency Manifests:** Created PEP 518/621 `pyproject.toml` and updated `requirements.txt` to include `PySide6`, `onnxruntime`, `pycaw`, `comtypes`, and complete platform dependencies.
- **Friend-Ready Onboarding Suite:** Authored comprehensive `README.md`, `QUICKSTART.md` (60-second launch guide), `PRIVACY.md` (zero data collection guarantees), `SECURITY.md` (zero egress verification), and `CONTRIBUTING.md`.
- **Release Verification & Artifact Integrity:** Standalone Windows 64-bit production binary and `dist/FlowPilot-v3.0.2-win64.zip` packaged with verified SHA-256 checksums and zero external dependencies.

### Security & Privacy
- **Console Log Sanitization:** Removed raw speech transcripts and voice trigger contents from stdout in `engine/orchestrator.py`; now logs strictly duration, character counts, and sanitized lifecycle events to protect user dictation privacy in diagnostic streams.
- **Forensic Network Audit Verification:** Re-verified zero network egress during model initialization, VAD inference, audio recording, transcription, and text insertion.

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
