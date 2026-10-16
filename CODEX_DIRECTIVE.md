# DIRECTIVE TO CODEX: THE FLOWPILOT STANDARD OF ENGINEERING EXCELLENCE

**Document ID:** FP-DIR-2026-CODEX-01  
**Target Audience:** OpenAI Codex, Claude, Autonomous Coding Agents, and Core FlowPilot Maintainers  
**Effective Date:** October 16, 2026  
**Status:** Inviolate / Binding Engineering Specification  
**Repository:** [FlowPilot on GitHub](https://github.com/abishekvr0910/flowpilot)  
**Primary Architecture:** Native Python 3.11+ / PySide6 (Qt6) / CTranslate2 INT8 / Silero VAD v5 / Windows Win32 API  

---

## 1. PREAMBLE & MISSION STATEMENT

FlowPilot is engineered to resolve a critical failure in modern AI voice assistants: **the sacrifice of privacy, speed, and focus for cloud convenience.** 

Proprietary solutions such as *Wispr Flow* and *Superwhisper* have demonstrated that voice dictation is only viable for engineers and power users when it is **instant, context-aware, and invisible**. However, cloud-dependent architectures introduce non-deterministic network latency, telemetry leakage, subscription paywalls, and corporate confidentiality risks.

This Directive establishes the permanent standard of engineering excellence for FlowPilot. Every modification, refactor, and feature addition executed by Codex or any AI agent must adhere strictly to the empirical benchmarks, architectural teardowns, and engineering non-negotiables set forth herein.

---

## 2. THE 7 INVIOLATE COMMANDMENTS OF FLOWPILOT EXCELLENCE

Any code change that violates any of these seven principles is considered a **critical defect** and must be immediately reverted:

1. **Zero Cloud Egress (100% Local-First):**
   Speech-to-text inference (`faster-whisper`), acoustic activity detection (`silero-vad`), and text post-processing (`FactGuard™`) must run 100% on local CPU. No audio frames, transcript tokens, clipboard contents, or screen pixels may ever leave the user's workstation. Loopback sockets are monitored by automated regression tests ([`tests/test_network_egress.py`](tests/test_network_egress.py)).
2. **Zero Syllable Clipping (Continuous 350ms Pre-Roll):**
   Human speech begins before mechanical keys are fully engaged. The audio capture pipeline must continuously maintain an active, sliding float32 ring buffer seeded prior to hotkey trigger. First-syllable loss is unacceptable.
3. **Sub-1.5s End-to-End Latency Target:**
   From the instant speech ceases to the instant verified text is injected at the cursor, median latency must remain **~1,200 ms** (p95 < 1,500 ms) on standard 8-thread consumer CPUs.
4. **Absolute Window Focus Integrity (`WS_EX_NOACTIVATE`):**
   The visual UI (Floating HUD, Desktop Companions, Animations, Context Menus) must never steal window focus from the user's active application (VS Code, Windows Terminal, Browser, Notepad). Keystroke injection requires cursor focus preservation.
5. **Deterministic Semantic Preservation (`FactGuard™`):**
   AI text polishing must never hallucinate, invert negation, alter numbers, corrupt dates, or mutate developer identifiers. If semantic ambiguity arises, verbatim transcription is strictly enforced.
6. **Native Qt6/PySide6 Event Loop Execution (Zero IPC Bloat):**
   All desktop visual elements—including pixel pets and mascots—must render natively via `QPainter` within the primary Qt event loop at 60 FPS in <0.2 ms with <5 MB RAM. Multi-process socket bridges, WebSockets, Electron wrappers, and base64 image streaming are strictly prohibited.
7. **Zero-Crash Mutex & Process Lifecycle:**
   Single-instance mutex enforcement must be absolute. Duplicate process launches must never fail silently, hang in blocking modal loops, or leave orphaned audio listeners competing for microphone hardware.

---

## 3. THE REFERRAL TEARDOWNS: EMPIRICAL BENCHMARKS & COMPETITIVE FOUNDATIONS

FlowPilot's architecture is synthesized from forensic teardowns of industry-leading dictation and desktop companion tools. Codex must understand the origins and rationale for each core component:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                COMPETITIVE SOURCING MATRIX                              │
├───────────────────┬──────────────────────────────────┬──────────────────────────────────┤
│ REFERRAL / SOURCE │ PROVEN CAPABILITY ADOPTED        │ FLOWPILOT IMPLEMENTATION FILE    │
├───────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Wispr Flow        │ Spoken Punctuation & Editing     │ engine/writing_intelligence.py   │
│                   │ Conversational Pause (0.85s)     │ engine/audio_recorder.py         │
│                   │ Docked Edge Line & Equalizer     │ ui/floating_hud.py               │
├───────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ whisper-local     │ 350ms Pre-Roll Ring Buffer       │ engine/audio_recorder.py         │
│                   │ PortAudio Warmup Stream          │ engine/audio_recorder.py         │
│                   │ TapLatch™ Dual Gesture FSM       │ engine/hotkey_service.py         │
├───────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ SpeakoFlow        │ Win32 Clipboard Sequence Check   │ engine/text_injector.py          │
│                   │ Alt+Shift+Z Emergency Re-Paste   │ engine/orchestrator.py           │
├───────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ Superwhisper      │ INT8 Quantization on CPU         │ engine/speech_to_text.py         │
│                   │ Developer Vocabulary Biasing     │ engine/speech_to_text.py         │
├───────────────────┼──────────────────────────────────┼──────────────────────────────────┤
│ SondeR-Cat        │ 26×28 ASCII Pixel Sprite Engine  │ ui/pet_sprites.py                │
│                   │ 14 Fur Palettes & Dynamic Pupils │ ui/floating_hud.py               │
│                   │ Audio-Reactive Paw Kneading      │ ui/floating_hud.py               │
└───────────────────┴──────────────────────────────────┴──────────────────────────────────┘
```

### Referral 1: Wispr Flow (The User Experience & Voice Intelligence Benchmark)
*Forensic Analysis Document:* [`docs/architecture/flowpilot_wispr_feature_inventory.md`](docs/architecture/flowpilot_wispr_feature_inventory.md)
- **Spoken Punctuation Grammar:** Real-time conversion of spoken tokens (`comma` -> `,`, `period` / `full stop` -> `.`, `question mark` -> `?`, `colon` -> `:`, `semicolon` -> `;`, `ellipsis` -> `...`, `quotes` -> `""`, `parens` -> `()`, `brackets` -> `[]`).
- **Voice Editing & Scratch Commands:**
  - *"scratch that"*, *"delete that"*, or *"cancel that"* erases the preceding sentence or clause before clipboard injection.
  - *"scratch last word"* erases only the trailing token.
  - *"all caps <word>"* transforms the target token into uppercase (e.g., *"all caps secret"* -> `SECRET`).
- **Structural Formatting:** Spoken commands `new line` (`\n`), `new paragraph` (`\n\n`), and `tab` (`\t`) with automatic capitalization of subsequent sentences.
- **Conversational Silence Detection:** In toggle mode, an 850ms silence window finalizes speech without requiring manual hotkey release, cutting conversational pause latency by 550ms compared to traditional 1.4s timers.
- **Visual Elegance:** Minimalist docked vertical edge bar that subtly pulses with speech RMS volume, completely eliminating distracting text boxes.

### Referral 2: whisper-local (The Acoustic Latency & Gesture Benchmark)
*Forensic Analysis Document:* [`docs/architecture/flowpilot_desktop_architecture.md`](docs/architecture/flowpilot_desktop_architecture.md)
- **Continuous Sliding Pre-Roll Ring Buffer:** Maintains a 350ms float32 circular buffer (`collections.deque(maxlen=N)`). When recording triggers, the pre-roll buffer is atomically transferred to seed the active recording frames.
- **Zero-Latency Audio Stream Warmup:** `warmup_stream()` initializes the PortAudio device in the background at startup, eliminating the 100–180ms driver spin-up latency on Windows MME/WASAPI.
- **TapLatch™ Finite State Machine:**
  - `IDLE` -> Key Down -> `HELD` (Push-to-Talk mode; release triggers immediate stop and paste).
  - `HELD` -> Release in <350ms -> `PENDING`.
  - `PENDING` -> Second Key Down within 350ms window -> `LATCHED` (Hands-free continuous dictation without holding key).
  - `LATCHED` -> Key Down -> `IDLE` (Stops dictation and pastes).

### Referral 3: SpeakoFlow (The Clipboard Hardware Safety Benchmark)
*Forensic Analysis Document:* [`tests/test_dissected_upgrades.py`](tests/test_dissected_upgrades.py)
- **Atomic Clipboard Hardware Sequence Verification:** Utilizes Win32 `ctypes.windll.user32.GetClipboardSequenceNumber()`.
- **Race Condition Prevention:** Reads sequence $S_1$ before clipboard overwrite, verifies $S_2$ after clipboard paste, and only restores previous clipboard state if $S_2 == S_1 + 1$. If the user copied new data during the paste window, restoration is aborted to prevent data loss.
- **Alt+Shift+Z Quick Re-Paste:** Re-injects the most recent dictation buffer instantly into the active window if focus was disrupted.

### Referral 4: Superwhisper (The Offline Accuracy Benchmark)
*Forensic Analysis Document:* [`docs/testing/flowpilot_benchmark_matrix.md`](docs/testing/flowpilot_benchmark_matrix.md)
- **Local Model Architecture:** `faster-whisper` (CTranslate2) utilizing 8-bit integer quantization (`int8`) on CPU with greedy decoding (`beam_size=1`).
- **Developer Vocabulary Biasing:** Injects engineered domain prompts biasing the beam search toward modern tech stacks (`Kubernetes`, `GraphQL`, `FastAPI`, `Pydantic`, `TypeScript`, `Docker`, `PostgreSQL`).

### Referral 5: SondeR-Cat & Desktop Pet Ecosystem (The Companionship Benchmark)
*Forensic Analysis Document:* [`flowpilot_pet_companion_and_gpt_review_audit.md`](flowpilot_pet_companion_and_gpt_review_audit.md)
- **Rejection of Web/WebSocket Hallucinations:** GPT-generated review documents proposed streaming base64 PNGs over WebSockets to an HTML canvas (50ms+ latency, 20%+ CPU). This was rejected. Both FlowPilot and SondeR-Cat are native **PySide6 / Qt6**.
- **Native ASCII Sprite Grid Engine:** 26×28 ASCII text grids in [`ui/pet_sprites.py`](ui/pet_sprites.py) rendered via `QPainter` at `scale=3` (78×84 px) with 14 fur palettes (Orange Tabby, Calico, Midnight Black, Classic Gray, Siamese, Pastel Pink, Snow White, Mint, Chocolate, Cream, Lilac, Mimi, JJ, Lilly).
- **Interactive Speech Reactivity:**
  - *Dictating:* Front paws knead and type (`type_a`, `type_b`, `knead_a`, `knead_b`) with speed proportional to microphone RMS volume.
  - *Transcribing:* Pupils glow electric cyan/amber (`#38BDF8` / `#F59E0B`).
  - *Pasted:* Celebratory stretch with floating 8-bit hearts (❤️) and optional non-blocking `meow.wav` audio cues.

---

## 4. ARCHITECTURAL BLUEPRINT & SUB-SYSTEM SPECIFICATIONS

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              FLOWPILOT DESKTOP RUNTIME                                 │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. HARDWARE INPUT LAYER                                                                │
│    • PortAudio WASAPI/ALSA/CoreAudio Stream (Warm Background Ring Buffer: 350ms)       │
│    • Win32 RegisterHotKey / POSIX Pynput (Ctrl+Shift+Space, F9, Alt+Shift+Z)           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. CORE ENGINE ORCHESTRATION LAYER (engine/orchestrator.py)                            │
│    • DictationSession State Machine (Monotonic Tokens: fp-sess-<hex>)                  │
│    • State Transitions: IDLE ──► RECORDING ──► FINALIZING ──► TRANSCRIBING ──► INJECT  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. ASR & INTELLIGENCE PIPELINE                                                         │
│    • Audio Capture: Float32 Mono 16kHz Streaming (engine/audio_recorder.py)            │
│    • Acoustic Activity: Silero VAD v5 ONNX Gate (engine/vad.py)                        │
│    • Local STT: faster-whisper INT8 CPU Greedy Decoder (engine/speech_to_text.py)      │
│    • FactGuard™: Punctuation, Negation Guard, Identifier Formatter (engine/writing_..) │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. OS INJECTION & CLIPBOARD HARDWARE GUARD (engine/text_injector.py)                   │
│    • Active Window Inspector (HWND Class / Process Identity)                           │
│    • Win32 GetClipboardSequenceNumber Atomic Verification                             │
│    • SendInput Synthesized Keystrokes (Ctrl+V / Shift+Insert / macOS Cmd+V)            │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. VISUAL COMPANION & HUD SUBSYSTEM (ui/floating_hud.py)                               │
│    • Frameless, Non-Activating Tool Window (WS_EX_NOACTIVATE | WS_EX_TOPMOST)         │
│    • 4-Way Appearance Switcher:                                                        │
│      [1] 🐾 SondeR-Cat Pixel Kitty  (26x28 ASCII Grid, 14 Palettes, RMS Kneading)      │
│      [2] 🤖 Pilot Mascot Robot       (72x72 Vector Mascot, Dilating Pupils, Antenna)    │
│      [3] 📏 Wispr Docked Edge Line   (14x68 Minimalist Docked Vertical Bar)            │
│      [4] 🌊 Wispr Wave Equalizer     (58x26 Animated 5-Bar Spectrum)                   │
│    • One-Click Screen Edge & Corner Snapping (Bottom-Right default, 24px padding)      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 6. SYSTEM TRAY & LIFECYCLE (ui/tray_manager.py, engine/single_instance.py)             │
│    • SingleInstance Named Mutex with Auto-Dismissing MessageBoxTimeoutW (2.5s)         │
│    • Local OpenAI-Compatible REST Server (http://127.0.0.1:8765/v1)                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. NON-NEGOTIABLE IMPLEMENTATION RULES FOR CODEX

When modifying or extending FlowPilot code, Codex must adhere to these exact constraints:

### Rule 1: Never Break the Window Focus Boundary
Whenever creating or editing UI widgets (`QWidget`), you must apply:
```python
self.setWindowFlags(
    Qt.WindowStaysOnTopHint |
    Qt.FramelessWindowHint |
    Qt.Tool |
    Qt.WindowDoesNotAcceptFocus
)
self.setAttribute(Qt.WA_TranslucentBackground, True)
self.setAttribute(Qt.WA_ShowWithoutActivating, True)
```
On Windows, you must reinforce this in `showEvent` using Win32 API:
```python
if sys.platform == "win32":
    hwnd = int(self.winId())
    ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style | 0x08000000 | 0x00000008) # WS_EX_NOACTIVATE | WS_EX_TOPMOST
```

### Rule 2: Single-Instance Mutex Must Never Hang
When detecting a duplicate instance in `desktop_app.py`, never call a blocking `MessageBoxW` that halts automated tests or terminal runners. Always use `MessageBoxTimeoutW` with an automatic 2,500ms timeout:
```python
if self.single_instance and self.single_instance.is_already_running():
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.MessageBoxTimeoutW(
                0,
                "FlowPilot is already running!\n\nLook for the companion on your screen or in your System Tray.",
                "FlowPilot Voice Intelligence",
                0x40, 0, 2500
            )
        except Exception:
            pass
    sys.exit(0)
```

### Rule 3: Companion Screen Placement Bounds
Never park the companion widget at `(0, 0)`! If `hud_x` or `hud_y` are missing, zero, or corrupted in `config.json`, the companion must default to the **Bottom-Right corner** of the primary monitor:
```python
screen = self.app.primaryScreen()
geom = screen.availableGeometry()
saved_x = self.config.get("hud_x")
saved_y = self.config.get("hud_y")
if saved_x is not None and saved_y is not None and saved_x > 20 and saved_y > 20:
    x = max(geom.left() + 20, min(saved_x, geom.right() - self.hud.width() - 20))
    y = max(geom.top() + 20, min(saved_y, geom.bottom() - self.hud.height() - 20))
else:
    x = geom.right() - self.hud.width() - 24
    y = geom.bottom() - self.hud.height() - 24
self.hud.move(x, y)
self.hud.show()
self.hud.raise_()
```

### Rule 4: FactGuard™ Conservative Entity Validation
When enhancing writing intelligence in `engine/writing_intelligence.py`:
- You may strip stutters and filler words (`um`, `uh`, `like`, `you know`).
- You may format identifiers (`camel case user profile` -> `userProfile`).
- You may format spoken punctuation and structural newlines.
- **You must NEVER alter:**
  - Numbers, currencies, or quantities ($12,000 -> $12,000; never rounded or estimated).
  - Dates and timestamps (October 16, 2026).
  - Negative logic words (`not`, `never`, `no`, `don't`, `cannot`).
  - Code keywords (`SELECT`, `WHERE`, `return`, `def`, `class`).

### Rule 5: Audio Pre-Roll Warmup Preservation
In `engine/audio_recorder.py`, never initialize PortAudio streams on-demand inside `start_recording()`. The stream must be kept in a low-overhead warmed state (`warmup_stream()`) with the pre-roll deque continuously buffering:
```python
self._preroll_buffer = deque(maxlen=int(self.sample_rate * 0.35 / self.chunk_size))
```

---

## 6. VERIFICATION GATES & REGRESSION TEST HARNESS

FlowPilot enforces a zero-defect regression protocol. Before any code is committed, **all 27 automated test suites must pass 100%**:

```bash
# Execute Full 27-Suite Master Regression
python tests/run_all_tests.py
```

### The 27 Required Verification Suites:
1. `tests/test_audio.py` — Microphone capture & PortAudio ring buffer
2. `tests/test_stt.py` — Local Faster-Whisper base INT8 speech model
3. `tests/test_text_injector.py` — Keystroke synthesis & Win32 focus lock
4. `tests/test_audio_ducker.py` — Windows CoreAudio / PulseAudio ducking
5. `tests/test_api_and_websocket.py` — REST server & WebSocket protocol
6. `tests/test_hotkey.py` — Hotkey resolution & normalization
7. `tests/test_win32_hotkey.py` — RegisterHotKey message loop
8. `tests/test_desktop_app.py` — Native PySide6 HUD & System Tray lifecycle
9. `tests/test_language_registry.py` — 18-language registry & script safety
10. `tests/test_writing_intelligence.py` — Spoken punctuation & voice editing
11. `tests/test_factguard_adversarial.py` — Adversarial negation & numbers
12. `tests/test_network_egress.py` — Forensics zero external network egress
13. `tests/test_multilingual_validation.py` — Multi-script Unicode preservation
14. `tests/test_multilingual_speech_reality.py` — Acoustic reality evaluation
15. `tests/test_personalization.py` — Snippets & vocabulary dictionary
16. `tests/test_settings_dialog.py` — UI settings & conflict inspector
17. `tests/test_model_benchmarks_extended.py` — Extended Whisper benchmarks
18. `tests/test_orchestrator_state_machine.py` — 9-state machine transitions
19. `tests/test_session_lifecycle.py` — Monotonic session token ownership
20. `tests/test_factguard_v2.py` — Conservative entity guardrails
21. `tests/test_application_profiles.py` — App-specific formatting rules
22. `tests/test_personalization_snippets.py` — Snippet injection safety
23. `tests/test_silero_vad_resolution.py` — Silero VAD v5 ONNX assets
24. `tests/test_notepad_dictation_e2e.py` — 5-cycle Notepad physical read-back
25. `tests/test_dissected_upgrades.py` — Pre-roll, TapLatch, & atomic seq counter
26. `tests/test_cross_platform.py` — Linux & macOS cross-platform shims
27. `tests/test_sondercat_companion.py` — SondeR-Cat pixel kitty & 14 palettes

---

## 7. PACKAGING & DISTRIBUTION VERIFICATION

Whenever a release build is triggered:
1. Rebuild executable using: `python -m PyInstaller flowpilot.spec --noconfirm`
2. Run standalone binary smoke test: `python tests/test_standalone_binary_smoke.py`
3. Verify bundled assets in `dist/FlowPilot/_internal`:
   - `silero_encoder_v5.onnx` & `silero_decoder_v5.onnx`
   - `ui/pet_sprites.py` & `assets/sounds/meow.wav`
   - `assets/flowpilot.ico`
4. Verify root launcher integrity:
   - `FlowPilot.lnk` (Windows Application Shortcut)
   - `FlowPilot.bat` (Batch launcher)
   - `start_desktop.bat` (Console launcher)

---

## 8. SUMMARY FOR CODEX

Codex, when you work on FlowPilot, you are not writing another throwaway script. You are maintaining an industrial-grade, privacy-first, ultra-low-latency voice intelligence platform designed to outperform venture-backed competitors while providing users with an adorable, responsive desktop companion.

**Build for speed. Build for zero cloud leakage. Build for absolute focus integrity. Aim for nothing short of engineering excellence.**
