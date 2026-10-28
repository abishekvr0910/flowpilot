# FlowPilot: Whole-Product Master Scope & Acceptance Criteria

**Document Version:** 3.1.0-GA-SPEC  
**Status:** Authoritative Product Scope & Verification Standard  
**Target Release:** FlowPilot v3.1.0  
**Target Architecture:** Windows 10/11 (64-bit, x64), Native Host-Isolated  

---

## Executive Summary & Product Invariants

FlowPilot is an offline, private, Windows-first intelligent dictation and developer writing system. This master specification defines the complete functional scope of the **entire product** across all 13 core subsystems.

For every subsystem, this document establishes:
1. **Functional Scope & Capabilities**: What the subsystem must achieve in production.
2. **Passing Criteria & Acceptance Gates**: The verifiable technical conditions, command lines, thresholds, and evidence receipts required to declare the section **PASSED**.
3. **Hard Kill / Failure Criteria**: Explicit conditions that cause an immediate rejection or release block.

### Absolute Non-Negotiable Product Invariants

Across all subsystems and builds, FlowPilot enforces four unalterable architectural invariants:

1. **Zero Cloud Egress Invariant:** Audio tensors, captured PCM buffers, acoustic models, transcripts, recovery buffers, and local SLM repairs strictly execute host-locally on the user's CPU/GPU. No network socket may transmit dictation data off `127.0.0.1`.
2. **Focus Safety Invariant:** Floating HUDs, overlays, notifications, and companion animations must strictly maintain Win32 `WS_EX_NOACTIVATE (0x08000000)` and `Qt.WindowDoesNotAcceptFocus`. FlowPilot must never steal keyboard focus or window activation from target applications.
3. **Truthful Delivery Status Invariant:** Never report an injection as `CONFIRMED` unless the target window buffer was verified via Win32 `WM_GETTEXT`, `GetWindowTextW`, or UI Automation `IUIAutomationValuePattern`.
4. **Clean-Room License Boundary:** Zero GPL code, schemas, or foreign proprietary binary components may be ingested, copied, or linked into FlowPilot. All competitors (Wispr Flow, FluidVoice, FreeFlow) are studied strictly under clean-room protocol.

---

## Subsystem 1: Audio Capture, WASAPI & Device Lifecycle

### 1.1 Scope & Functional Requirements
* **Audio Capture Engine:** Capture microphone audio at 16 kHz mono PCM 16-bit float via PortAudio / WASAPI. Warm-buffer ring capacity of at least 3 seconds.
* **Persistent Endpoint Contract (Spec 0002):** Persist chosen physical input device via immutable contract tuple `(name, host_api, max_channels)`. Disambiguate identical device names across host APIs (WASAPI vs DirectSound vs MME).
* **Missing Device Sentinel:** When a persisted device is unplugged or missing, resolve to `DEVICE_MISSING_SENTINEL = -9999` and halt recording safely. **Never silently fall back to an internal default laptop microphone.**
* **Dynamic Hot-Plug Re-Enumeration:** Support physical USB and 3.5mm jack disconnect and reconnect while the app is running. Re-enumerate PortAudio device indices dynamically.
* **Windows Audio Ducking & Restore:** Duck background application audio (Spotify, Chrome, games) via `pycaw` / `IAudioMeterInformation` / `ISimpleAudioVolume` during active dictation, and restore original volumes with fade within 250ms of session completion.

### 1.2 How Section 1 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_audio.py
  python -X utf8 tests/test_audio_devices.py
  python -X utf8 tests/test_audio_ducker.py
  ```
  *Verdict Requirement:* 100% Passed (45+ unit assertions), 0 failures, 0 errors.
* **Interactive Physical Hardware Gate (Spec 0002):**
  Execute `scripts/interactive_physical_mic_test.py` with physical hardware:
  1. *Unplug during idle:* UI displays orange/red `Disconnected` indicator; no crash.
  2. *Unplug during recording:* Audio capture aborts safely without hung threads; UI shows `Microphone Disconnected`; audio buffer drains cleanly.
  3. *Reconnect:* Device automatically re-acquired within 2.0s; next dictation records and transcribes properly.
  *Evidence Receipt:* Verified `PHYSICAL_USB_UNPLUG_RECEIPT_*.md` generated with SHA-256 digest.
* **Kill Criteria:** Any unhandled PortAudio deadlock, silent fallback to built-in mic when external mic is chosen, or background audio failing to restore volume.

---

## Subsystem 2: Voice Activity Detection (Silero VAD)

### 2.1 Scope & Functional Requirements
* **ONNX Runtime Silero VAD:** Run Silero VAD v4/v5 ONNX model locally on CPU via `onnxruntime`. Process 512-sample (32ms at 16kHz) audio chunks.
* **Dynamic Speech Boundary Detection:** Detect speech onset within $\le 96\text{ms}$ (3 chunks). Detect speech termination after configurable silence window (default 1.2s–1.5s).
* **Speech Threshold Tuning:** Configurable speech probability threshold (default 0.50). Reject non-speech acoustic artifacts (mouse clicks, mechanical keyboard clatter, breathing, chair squeaks).
* **Asset Resolution & Fallback:** Locate `silero_vad.onnx` reliably across dev source tree, PyInstaller `_MEIPASS` bundle, and local user application directory without network lookups.

### 2.2 How Section 2 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_silero_vad_resolution.py
  ```
  *Verdict Requirement:* 100% Passed.
* **Acoustic Boundary Benchmark:**
  Run synthetic audio fixtures (`tests/fixtures/speech_with_leading_trailing_silence.wav`):
  * Speech onset detected $\le 100\text{ms}$ from true voice onset.
  * Silence cutoff triggers between $1200\text{ms} \pm 100\text{ms}$ after last voiced frame.
  * Clean speech segmentation verified with zero truncated syllables.
* **Kill Criteria:** Missing ONNX model raises runtime crash; continuous recording indefinitely when speaker is silent; audio buffer starvation or memory leak in VAD circular buffer.

---

## Subsystem 3: Local Speech Recognition (ASR Engine)

### 3.1 Scope & Functional Requirements
* **CTranslate2 Faster-Whisper:** Run quantized `int8` CTranslate2 faster-whisper models entirely on CPU (with optional CUDA acceleration if compatible NVIDIA GPU present).
* **Dual Model Profiles:** Bundled `faster-whisper-base` (default for low latency) and optional `faster-whisper-small` (for higher accuracy).
* **Warm Model Initialization:** Model weights loaded once and kept warm during active dictation. No model reloading on subsequent recordings.
* **Multilingual Registry & Script Validation:** Standard registry for English (`en`), Hindi (`hi`), Tamil (`ta`), and Malayalam (`ml`). Strict Unicode script validation: Indic text must never output mangled ASCII, replacement characters `\uFFFD`, or mixed unrenderable glyphs.
* **Vocabulary & Prompt Biasing:** Inject user personal dictionary terms and active window title tokens into Whisper `initial_prompt` (capped at 224 tokens) to bias transcription towards technical jargon and domain terms.

### 3.2 How Section 3 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_stt.py
  python -X utf8 tests/test_language_registry.py
  python -X utf8 tests/test_multilingual_validation.py
  python -X utf8 tests/test_multilingual_speech_reality.py
  python -X utf8 tests/test_model_benchmarks_extended.py
  ```
  *Verdict Requirement:* 100% Passed across all 5 suites.
* **Offline Self-Test Gate:**
  ```powershell
  python desktop_app.py --self-test
  ```
  *Verdict Requirement:* Synthesizes test phrase via Windows SAPI, captures audio, transcribes through local Whisper CPU int8 engine, verifies $\text{WER} \le 5\%$ against ground truth, and exits with code 0.
* **Kill Criteria:** Transcription attempts any network call; model crashes on non-ASCII input; Unicode replacement character `\uFFFD` present in output.

---

## Subsystem 4: Writing Intelligence, Post-Processing & FactGuard

### 4.1 Scope & Functional Requirements
* **Deterministic FactGuard (Specs 0004 & Invariants):**
  Strictly preserve numbers (`1,000`, `42.5`), currencies (`$50`, `€100`), dates (`October 28, 2026`), URLs/paths, technical code identifiers (`camelCase`, `snake_case`), and critical negations (`not`, `never`, `no`, `cannot`). If any post-processing transform alters, adds, or drops these tokens, **FactGuard must veto the transform and fall back to raw transcript**.
* **Spoken Self-Correction Engine:** Detect verbal self-corrections (*"meet Thursday, no actually Wednesday"* $\rightarrow$ *"meet Wednesday"*; *"twenty no thirty dollars"* $\rightarrow$ *"$30"*).
* **Instruction Execution Guard (FreeFlow Parity):** Detect when an SLM attempts to answer or execute an imperative command (*"Write an email to John saying I'm sick"* $\rightarrow$ drafting an email instead of transcribing the words). Detect assistant preambles (`Sure, here is...`) or token overlap collapse ($< 35\%$) and veto immediately.
* **Local SLM Repair Sandbox (Spec 0004):** Optional opt-in local SLM (`Qwen2.5-0.5B-Instruct` GGUF via `llama-cpp-python`). Hard timeout of 400ms. If inference exceeds 400ms or fails, fallback to verbatim transcript instantly without user disruption.
* **Template & Prompt Leakage Protection:** Ensure small SLM outputs never leak system prompt fragments or internal template tokens (`<|im_start|>`, `You are a helpful...`) into the document buffer.

### 4.2 How Section 4 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_writing_intelligence.py
  python -X utf8 tests/test_factguard_adversarial.py
  python -X utf8 tests/test_factguard_v2.py
  python -X utf8 tests/test_correction_intent.py
  python -X utf8 tests/test_local_text_repair.py
  ```
  *Verdict Requirement:* 100% Passed across all 5 suites.
* **Adversarial FactGuard Benchmark:**
  100% pass on 50+ adversarial entity corruption fixtures (e.g. `$100M` altered to `$10M`, `do not delete` altered to `delete`). FactGuard must catch 100.0% of numerical/negation mutations.
* **Kill Criteria:** FactGuard permits a dropped negation or corrupted number; SLM repair hangs > 400ms; template prompt tokens leak into the output string.

---

## Subsystem 5: Text Injection, Focus Safety & Delivery Observer

### 5.1 Scope & Functional Requirements
* **Non-Activating Focus Invariant:** Inject text into target window without stealing focus or activating HUD windows. Maintain Win32 `WS_EX_NOACTIVATE` and `Qt.WindowDoesNotAcceptFocus`.
* **Dual-Mode Delivery:**
  1. *Primary Mode:* Clipboard paste (`Ctrl+V` / `Shift+Insert`) with clipboard preservation (original user clipboard backed up and restored within 150ms).
  2. *Fallback / Direct Mode:* Direct Win32 `SendInput` Unicode typing (`KEYEVENTF_UNICODE`) when clipboard access is blocked or restricted.
* **Physical Modifier Release Polling:** Before dispatching synthetic `Ctrl+V`, poll `GetAsyncKeyState()` for `VK_CONTROL`, `VK_SHIFT`, `VK_MENU` (Alt), and `VK_LWIN/RWIN`. Wait up to 250ms for the user to physically release hotkey modifiers to prevent `Ctrl+Alt+V` corruption.
* **Truthful Delivery Status (Spec 0003):** Use independent `DeliveryObserver` reading Win32 `WM_GETTEXT`, `GetWindowTextW`, or UI Automation `IUIAutomationValuePattern`.
  * Status reported as `CONFIRMED` only when verified in the document buffer.
  * Status reported as `DISPATCHED_UNVERIFIED` in opaque canvases / terminals.
  * Status reported as `ABORTED_SAFE` when focus shifts to an unsafe/elevated window.
* **Safe Recovery Buffer:** When injection fails or cannot be confirmed, store the exact text in memory and enable 1-click recovery hotkey (`Ctrl+Alt+V` or tray action).

### 5.2 How Section 5 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_text_injector.py
  python -X utf8 tests/test_cross_app_injection.py
  python -X utf8 tests/test_delivery_observer.py
  python -X utf8 tests/test_notepad_dictation_e2e.py
  ```
  *Verdict Requirement:* 100% Passed across all 4 suites.
* **Interactive Cross-Application Gate:**
  Verify confirmed injection across real Windows applications:
  1. *Windows Notepad:* `CONFIRMED` via `WM_GETTEXT`.
  2. *VS Code (Electron):* `CONFIRMED` via UIA ValuePattern or graceful fallback.
  3. *Windows Terminal / PowerShell:* `DISPATCHED_UNVERIFIED` or verified paste via `Shift+Insert`.
  4. *Google Chrome / Brave (Web textarea):* Verified paste with clipboard restored.
  5. *Microsoft Word:* Verified paste without clipboard pollution.
* **Kill Criteria:** Dictation steals window focus away from user; paste reported as `CONFIRMED` when document buffer is actually empty; user's original clipboard content is permanently overwritten.

---

## Subsystem 6: Shortcuts, Session Orchestration & Ergonomics

### 6.1 Scope & Functional Requirements
* **Global Win32 Hotkey Loop:** Native Win32 `RegisterHotKey` message pump on dedicated thread with `UnregisterHotKey` cleanup on shutdown.
* **Orchestrator 9-State Machine:** Robust state transitions (`IDLE`, `WARMING`, `LISTENING`, `MUTED`, `PROCESSING`, `INJECTING`, `RECOVERING`, `ERROR`, `COOLDOWN`). Invalid state transitions rejected deterministically.
* **Hold-to-Mute (Spec 0005):** Holding `Ctrl+Space` during active recording mutes microphone frames without stopping recording session or triggering silence auto-stop. Muted frames excluded from transcription.
* **Hold-to-Toggle Latching:** Pressing Toggle hotkey while in Push-to-Talk mode latches into hands-free Toggle mode without stopping audio capture or dropping frames.
* **Session Ownership & Cancellation:** Pressing `Escape` or secondary cancel hotkey immediately aborts recording, flushes audio buffers, and resets HUD without inserting text.

### 6.2 How Section 6 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_hotkey.py
  python -X utf8 tests/test_win32_hotkey.py
  python -X utf8 tests/test_session_lifecycle.py
  python -X utf8 tests/test_orchestrator_state_machine.py
  python -X utf8 tests/test_hold_to_mute.py
  ```
  *Verdict Requirement:* 100% Passed across all 5 suites.
* **Rapid Toggle Stress Test:**
  Scripted test firing 50 consecutive start/stop/mute cycles with random intervals (50ms to 500ms).
  * 0 deadlocks.
  * 0 thread leaks.
  * Final state returns cleanly to `IDLE`.
* **Kill Criteria:** Hotkey fails to register; unhandled crash on rapid toggling; release of push-to-talk key hangs or drops audio.

---

## Subsystem 7: Floating HUD, Companions & Workspace UI

### 7.1 Scope & Functional Requirements
* **PySide6 Native Desktop HUD:** Lightweight floating pill displaying real-time audio levels, transcription spinner, and truthful status badge.
* **Context-Aware Companion Visibility (Spec 0001):**
  * *Fullscreen Detection:* Automatically hide companion when foreground app enters fullscreen (F11, video playback, presentations). Restore within 500ms when exiting fullscreen.
  * *Per-App Rules:* User-configured rules (Always Show, Quiet Edge, Always Hide) respected per executable (`code.exe`, `devenv.exe`, `chrome.exe`).
* **Media Audio Aware Hiding (Feature 27):**
  Monitor Windows audio session meter (`IAudioMeterInformation`). When audible media (YouTube, Spotify) plays continuously for $> 1.0\text{s}$, companion automatically hides in Smart Mode. Returns after $1.5\text{s}$ of quiet.
* **SondeR-Cat & Pixel Creator:** Original pixel pet animation states (idle, listening, typing, sleeping, error). Zero unlicensed franchise sprites.
* **Multi-Monitor & DPI Scaling:** Per-monitor DPI awareness. HUD positioning clamped to `MonitorWorkArea` (respects taskbar). Window geometry scales cleanly when Windows Accessibility *Text size* is set to $125\%+$.

### 7.2 How Section 7 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_desktop_app.py
  python -X utf8 tests/test_companion_visibility.py
  python -X utf8 tests/test_sondercat_companion.py
  ```
  *Verdict Requirement:* 100% Passed across all 3 suites.
* **Interactive Window Transition Gate (Spec 0001):**
  1. *F11 Fullscreen in Browser:* Companion hides $\le 500\text{ms}$; restores on exit $\le 650\text{ms}$.
  2. *Audible Video Playback:* Companion hides after 1.0s sustained audio; restores after 1.5s silence.
  3. *Dictation Override:* Pressing dictation hotkey while hidden temporarily displays HUD/status without altering fullscreen state.
* **Kill Criteria:** HUD steals window focus; companion appears inside fullscreen PowerPoint presentation; memory leak in PySide6 animation timer.

---

## Subsystem 8: Meeting Intelligence & Two-Track Audio

### 8.1 Scope & Functional Requirements
* **Synchronized Meeting Capture:** Capture extended audio sessions (up to 3 hours continuous) without buffer overflow or drift.
* **Two-Track Audio Separation (AEC Alternative):**
  Capture microphone input on Channel 0 (local speaker) and WASAPI system audio loopback on Channel 1 (remote meeting attendees). Transcribe independently to eliminate far-end echo loopback without requiring heavy C++ AEC libraries.
* **Extractive Notetaking & Summary:** Process transcripts into timestamped speaker turns, key discussion points, decisions made, and follow-up action items.
* **Meeting Storage Lifecycle:** Meeting notes, recordings, and deliberation sessions stored in dedicated vault (`data/meetings/`), completely isolated from the default ephemeral dictation pipeline.

### 8.2 How Section 8 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_meeting_notetaker.py
  python -X utf8 tests/test_meeting_deliberation.py
  ```
  *Verdict Requirement:* 100% Passed.
* **Extended Duration Benchmark:**
  Run 60-minute simulated dual-track audio session. Verify memory footprint growth is bounded ($< 50\text{MB}$ delta over 1 hour), audio timestamps remain synchronized within $\pm 50\text{ms}$, and meeting markdown notes generate successfully.
* **Kill Criteria:** Audio drift $> 200\text{ms}$; system loopback echoes remote attendees into local speaker transcript; meeting data leaks into general dictation history.

---

## Subsystem 9: Personalization, Vocabulary & Dynamic Learning

### 9.1 Scope & Functional Requirements
* **Custom Vocabulary & Tombstones:** Allow users to add custom technical terms, acronyms, and names with phonetic hints. Deleted terms persist as tombstones so they are not re-learned.
* **Voice Snippets & Macro Expansions:** Trigger phrase macro expansions (*"insert signature"* $\rightarrow$ multi-line formatted sign-off).
* **Automatic Correction Detection (FluidVoice Parity):**
  Observe post-injection document buffer via UIA/WM_GETTEXT diffing. When a user manually backspaces and fixes a word $\ge 2$ times within 7 days, propose the correction as a dictionary candidate in Companion Studio.
* **Consensus Learning Engine:** 3-day and 14-day consensus evaluation before auto-promoting proposed vocabulary. Never auto-commit vocabulary without user approval.

### 9.2 How Section 9 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_personalization.py
  python -X utf8 tests/test_personalization_snippets.py
  python -X utf8 tests/test_companion_studio.py
  ```
  *Verdict Requirement:* 100% Passed. Dynamic sliding-window tests pass regardless of execution date.
* **Correction Diff Verification:**
  Inject *"We use K8s"*, simulate user editing to *"We use Kubernetes"*. Verify correction detector registers candidate `("K8s", "Kubernetes")` with occurrence count 1.
* **Kill Criteria:** Deleted vocabulary reappears; unconsented background learning commits without user review; snippet expansion crashes on special regex characters.

---

## Subsystem 10: Settings, Local API & Profile Migration

### 10.1 Scope & Functional Requirements
* **Encrypted / Structured Configuration:** JSON-backed configuration (`config.json`) with versioned schema migrations (`profile_v1` $\rightarrow$ `profile_v2`).
* **Privacy Defaults:** Default profile enforces `save_history_text: false`. Dictation text is ephemeral by default.
* **Local Integration API (FastAPI):** Optional localhost API and WebSocket running strictly on `127.0.0.1`. Protected by local bearer token generated at first run.
* **Settings Dialog & Hotkey Inspector:** PySide6 settings dialog with interactive hotkey conflict detection (flags conflicts with existing Windows shortcuts like `Win+D`, `Ctrl+C`).

### 10.2 How Section 10 Must Pass
* **Automated Regression Suite:**
  ```powershell
  python -X utf8 tests/test_settings_dialog.py
  python -X utf8 tests/test_application_profiles.py
  python -X utf8 tests/test_api_and_websocket.py
  ```
  *Verdict Requirement:* 100% Passed.
* **Security & Network Boundary Test:**
  ```powershell
  python -X utf8 tests/test_network_egress.py
  ```
  Assert 0 outbound connections to non-loopback IPs during API startup, transcription, and shutdown.
* **Kill Criteria:** Settings file corruption on crash; API binds to `0.0.0.0` instead of `127.0.0.1`; settings change requires application restart for hotkey updates.

---

## Subsystem 11: Packaging, Distribution & Authenticode Signing

### 11.1 Scope & Functional Requirements
* **PyInstaller Desktop Binary:** Compile `desktop_app.py` via `flowpilot.spec` into clean `dist/FlowPilot/` directory and standalone ZIP archive.
* **Zero Missing Dependencies:** Bundle all CTranslate2 DLLs, ONNX Runtime binaries, PySide6 Qt plugins, Silero VAD model, and Whisper base weights. First launch must work 100% offline without downloading models.
* **Authenticode EV Code Signing:** Sign `FlowPilot.exe` and all bundled `.dll` / `.pyd` files with valid Authenticode certificate. Timestamped via RFC 3161 server.
* **Artifact Manifest & Checksums:** Release packaging script `scripts/package_windows_release.py` generates `RELEASE_ARTIFACT_MANIFEST.md` with SHA-256 digests for all binaries and archives.

### 11.2 How Section 11 Must Pass
* **Automated Packaging Smoke Suite:**
  ```powershell
  python -X utf8 tests/test_standalone_binary_smoke.py
  ```
  *Verdict Requirement:* 100% Passed.
* **Binary Integrity Verification:**
  ```powershell
  python scripts/package_windows_release.py --version v3.1.0-GA --verify-only
  ```
  * Verify all DLLs have valid Authenticode signatures via `signtool verify /pa /v dist\FlowPilot\FlowPilot.exe`.
  * Verify ZIP CRC32 and SHA-256 match published release manifest.
  * Launch packaged binary in clean VM without Python or developer tools: app launches $\le 2.5\text{s}$, transcribes audio offline, exits cleanly.
* **Kill Criteria:** Windows SmartScreen block due to missing signature; missing DLL crash on virgin Windows 10/11 machine; package requires internet on first run.

---

## Subsystem 12: Runtime Performance, Latency & Resources

### 12.1 Scope & Functional Requirements
* **Latency Budgets (Runtime Protocol):**
  * *Cold Start:* App launch to tray ready $\le 2.5\text{s}$ on standard SSD.
  * *Stop-to-First-Text (p50):* Stop hotkey release to first visible document text $\le 450\text{ms}$ on CPU.
  * *Stop-to-Settled-Text (p95):* Completed injection and verification $\le 900\text{ms}$.
* **Resource Limits:**
  * *Idle CPU:* $\le 1.0\%$ CPU consumption when not recording.
  * *Active Recording CPU:* $\le 8.0\%$ CPU for audio capture and VAD.
  * *Memory Footprint (Active):* $\le 1.8\text{GB}$ RAM with Whisper base and Silero VAD loaded.
* **Idle Model Memory Unloader (FluidVoice Parity):** After 10 minutes of complete inactivity, release heavy model weights from RAM, reclaiming $\ge 1.0\text{GB}$ memory. Reload in background on hotkey tap or target focus.

### 12.2 How Section 12 Must Pass
* **Benchmark Protocol Runner:**
  ```powershell
  python -X utf8 benchmarks/run_runtime_performance.py
  ```
  * p50 Latency $\le 450\text{ms}$.
  * p95 Latency $\le 900\text{ms}$.
  * 0 memory leaks over 100 consecutive dictation cycles.
* **Idle CPU Assertion:**
  Measure background process for 60 seconds of idle state: average CPU must not exceed 1.0%.
* **Kill Criteria:** Latency p95 $> 1500\text{ms}$; memory leaks $> 5\text{MB}$ per dictation cycle; background polling thread consumes $> 3\%$ CPU.

---

## Subsystem 13: Security, Privacy & Clean-Room Governance

### 13.1 Scope & Functional Requirements
* **Zero Egress Verification:** Low-level Winsock / socket hook asserting that no packets leave host device during audio capture, inference, or injection.
* **Secure Field (Password) Blacklist:** Inspect target window UI Automation role and subrole. If element is `AXSecureTextField` or Win32 `ES_PASSWORD`, **refuse capture, logging, and injection**.
* **Clean-Room Verification:** No code, comments, or schemas derived from GPLv3 (FluidVoice) or competitor binaries. Documented clean-room derivation log.
* **Local Storage Redaction:** Temporary wav files created during self-test or scratch operations scrubbed immediately with zero plain-text transcript dumps in `%TEMP%`.

### 13.2 How Section 13 Must Pass
* **Forensic Egress Suite:**
  ```powershell
  python -X utf8 tests/test_network_egress.py
  ```
  *Verdict Requirement:* 100% Passed. 0 packets transmitted outside `127.0.0.1`.
* **Password Field Shield Gate:**
  Target window with `ES_PASSWORD` style: FlowPilot status displays `Protected Field - Dictation Disabled`; zero text injected; zero keystrokes recorded.
* **Kill Criteria:** Socket connection to external IP detected; password field contents read or logged; GPLv3 code detected in repository.

---

## Master Release Verification Gate (The 60/60 Protocol)

To declare the whole FlowPilot product ready for public General Availability (GA), the release engineer must execute the master audit runner on an interactive Windows desktop:

```powershell
# Set UTF-8 encoding and execute the 60-suite audit runner
$env:PYTHONIOENCODING="utf-8"
python -X utf8 tests/run_all_tests.py --require-all
```

### The Strict GA Promotion Checklist
- [ ] **Automated Master Runner:** **60 total suites, 60 passed, 0 skipped, 0 failed** in $\le 150\text{s}$.
- [ ] **Hosted CI Matrix:** GitHub Actions run on `master` passes 100% green with 0 failures.
- [ ] **Offline Self-Test:** `python desktop_app.py --self-test` passes with $\text{WER} \le 5\%$.
- [ ] **Physical Hardware Gate:** USB and 3.5mm mic disconnect/reconnect verified on physical hardware with signed receipt.
- [ ] **Cross-App Matrix:** Notepad, VS Code, Word, Terminal, and Chrome all achieve confirmed injection without focus loss.
- [ ] **Authenticode Signing:** Binary signed with valid publisher certificate and RFC 3161 timestamp.
- [ ] **Zero Cloud Egress:** Network egress test confirms 0 bytes transmitted outside localhost.
- [ ] **Release Manifest:** `RELEASE_ARTIFACT_MANIFEST.md` updated with exact binary SHA-256 digests.
