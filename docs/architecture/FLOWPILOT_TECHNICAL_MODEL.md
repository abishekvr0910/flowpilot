# FlowPilot Architecture & Implementation Technical Model

**System**: FlowPilot Desktop AI Dictation System  
**Version**: 3.1.0 (Pilot / Prerelease Pipeline)  
**Target Environment**: Windows 10/11 64-bit (Native pywin32, WASAPI/MME, CTranslate2 int8 CPU)  
**Date**: 2026-10-25  
**Core Invariant**: Zero Cloud Egress — Dictation, VAD, ASR, formatting, and history never leave `127.0.0.1`.

---

## 1. System Overview & Component Dependency Graph

```
                                      +------------------------+
                                      |     desktop_app.py     |
                                      |  (PySide6 App Shell)   |
                                      +------------------------+
                                         |         |         |
                   +---------------------+         |         +-----------------------+
                   |                               |                                 |
                   v                               v                                 v
        +---------------------+         +---------------------+           +---------------------+
        |   ui.floating_hud   |         | ui.flowpilot_dash   |           |  ui.tray_manager    |
        | (Transparent Mascot |         | (Workspace, Tabs,   |           | (System Tray Menu,  |
        |  Pill / Status HUD) |         |  Scratchpad, Notes) |           |  Recovery Commands) |
        +---------------------+         +---------------------+           +---------------------+
                   |                               |                                 |
                   +-------------------------------+---------------------------------+
                                                   |
                                                   v
                                      +------------------------+
                                      |  FlowOrchestrator      |
                                      | (engine.orchestrator)  |
                                      +------------------------+
                                        /     |       |      \
                  +--------------------+      |       |       +-------------------+
                  |                           |       |                           |
                  v                           v       v                           v
        +--------------------+      +--------------------+      +--------------------+
        | AudioRecorder      |      | STTEngine          |      | TextInjector       |
        | (sounddevice / PA, |      | (Faster-Whisper,   |      | (Win32 SendInput,  |
        |  AudioDeviceResolv)|      |  int8 CPU models)  |      |  UIPI Token Check, |
        +--------------------+      +--------------------+      |  WM_GETTEXT Verif) |
                  |                           |                 +--------------------+
                  v                           v                           |
        +--------------------+      +--------------------+                v
        | SileroVAD          |      | WritingIntel       |      +--------------------+
        | (ONNX Runtime,     |      | (FactGuard v2,     |      | PilotTelemetry     |
        |  Voice Activity)   |      |  CorrectionIntent) |      | (Local JSON Log,   |
        +--------------------+      +--------------------+      |  4MB Rotating)     |
                                                                +--------------------+
```

---

## 2. Core Subsystems & Technical Specifications

### 2.1 Orchestration & State Machine (`engine.orchestrator.FlowOrchestrator`)
- **Responsibility**: Coordinates lifecycle of audio capture, silence detection, transcription, validation, text delivery, and error recovery.
- **State Machine (9 States)**:
  1. `IDLE`: Awaiting user activation.
  2. `STARTING_RECORDING`: Initializing audio hardware and circular pre-roll buffer.
  3. `RECORDING`: Ingesting microphone PCM samples; background RMS and silence tracking.
  4. `STOPPING_RECORDING`: Flushing audio stream and stopping capture cleanly.
  5. `TRANSCRIBING`: Running local faster-whisper int8 model inference on CPU.
  6. `VALIDATING`: Running FactGuard entity verification and CorrectionIntent resolution.
  7. `INSERTING_TEXT`: Dispatching text via TextInjector with UIPI preflight.
  8. `SUCCESS`: Text delivered (truthful status: `CONFIRMED_INSERTED` or `SENT_UNVERIFIED`).
  9. `ERROR`: Structured failure handling with automatic rollback and user notification.
  *(Auxiliary)*: `CANCELLED` when user aborts dictation via `Escape` key.
- **Concurrency**: Worker threads for STT inference (`_process_audio_worker`), dedicated Win32 message pump for hotkeys (`Win32HotkeyService`), non-blocking UI notifications via Qt thread bridge (`desktop_app._on_engine_state_change`).

### 2.2 Audio Ingestion & Device Resolution (`engine.audio_recorder`, `engine.audio_devices`)
- **Hardware Route**: PortAudio / `sounddevice` with bounded open/close timeouts (`_open_stream_bounded`, `_release_stream_bounded` with 1.5s hard deadlines).
- **Persistent Device Identity**:
  - `AudioDeviceResolver`: Matches device name, host API (WASAPI/DirectSound/MME), input channels, and persistent configuration.
  - Sentinel: `DEVICE_MISSING_SENTINEL = -9999` prevents accidental fallback to system default when a chosen external microphone disconnects.
- **VAD**: Silero VAD v5 ONNX engine (`engine.silero_vad.SileroVAD`) operates on 512-sample (32ms) windows at 16 kHz. Pre-roll circular buffer captures ~350ms of audio prior to VAD speech onset.

### 2.3 Local Speech-to-Text (`engine.stt_engine.STTEngine`)
- **Backend**: CTranslate2 int8 execution on CPU with multi-threading (default: 8 threads).
- **Bundled Models**: Faster-Whisper `base` (74M parameters) and `small` (244M parameters) bundled locally under `_internal/models/`.
- **Egress Guarantee**: Verified by `tests/test_network_egress.py`: Zero socket connections outside `127.0.0.1`.

### 2.4 Text Post-Processing & Entity Protection (`engine.writing_intelligence`, `engine.correction_intent`)
- **Correction Intent Resolver** (`engine.correction_intent.CorrectionIntentResolver`):
  - Deterministic parsing of spoken self-corrections (e.g., "Tuesday, actually Wednesday", "5 copies, no wait, 10 copies", "send to John sorry Jane").
  - Consumes trigger tokens and reports retracted spans to prevent false semantic violation alarms.
- **FactGuard v2** (`engine.writing_intelligence.FactGuard`):
  - Invariant preservation: regex entity extractor protects numbers, currency amounts, dates, times, URLs, email addresses, and technical code identifiers.
  - If post-processing mutates or drops a critical entity, FactGuard automatically falls back to raw transcript to preserve truth.

### 2.5 Text Injection & Windows Safety (`engine.text_injector.TextInjector`)
- **Injection Pipeline**:
  1. *Target Inspection*: Resolves target HWND, process name, and leaf edit control (`_find_edit_control`).
  2. *UIPI Preflight*: `windows_integrity.target_has_higher_integrity` inspects token integrity level (Low, Medium, High, System). Safely refuses blind keystroke dispatch if target is elevated to prevent silent UIPI drops.
  3. *Clipboard Sequence Protection*: Tracks `GetClipboardSequenceNumber` before and after paste; restores clipboard after verified sequence progression.
  4. *Slow-App Profile Delay*: Configurable per-app delays for heavyweight Electron/IDE targets (Slack, Notion, VS Code).
  5. *Truthful Status Verification*: Performs `WM_GETTEXT` before and after paste. Returns structured `InjectionResult` (`CONFIRMED_INSERTED`, `SENT_UNVERIFIED`, `FAILED_RECOVERY_AVAILABLE`, `ERROR`). Never reports success unless physical insertion is verified.
- **Dedicated Recovery**:
  - `inject_last()`: Re-injects previous dictation into external editor.
  - `re_copy_last()`: Copies previous dictation text directly into clipboard.

---

## 3. End-to-End User Execution Flow

```
[User Action: Hotkey Press (e.g. F9 or Ctrl+Alt+Space)]
                        |
                        v
         [Orchestrator: STARTING_RECORDING]
         - Snapshots target foreground window HWND
         - Opens audio stream via AudioDeviceResolver
         - Ingests circular pre-roll buffer
                        |
                        v
              [Orchestrator: RECORDING]
         - Streams 16 kHz mono PCM into memory buffer
         - Audio level RMS updates FloatingHUD animation
         - Silero VAD monitors speech presence & silence
                        |
[User Action: Hotkey Release (Push-to-Talk) or Hotkey Toggle]
                        |
                        v
         [Orchestrator: STOPPING_RECORDING]
         - Closes sounddevice stream with bounded timeout
         - Passes WAV bytes to worker thread
                        |
                        v
            [Orchestrator: TRANSCRIBING]
         - Faster-Whisper int8 decodes audio on CPU
         - Emits raw text transcript
                        |
                        v
             [Orchestrator: VALIDATING]
         - CorrectionIntent resolves spoken self-corrections
         - FactGuard protects entity invariants
         - ContextProcessor formats code / technical terms
                        |
                        v
           [Orchestrator: INSERTING_TEXT]
         - TextInjector verifies UIPI integrity & target focus
         - Caches clipboard, sets transcript, simulates Ctrl+V
         - Observes WM_GETTEXT / document sequence changes
                        |
                        v
              [Orchestrator: SUCCESS]
         - Truthful notification: "Inserted & confirmed" OR
           "Sent — unverified target (please check)"
         - Updates FloatingHUD & local rotating telemetry
         - Auto-resets to IDLE after 0.8s
```

---

## 4. Comprehensive Feature Inventory & Status Matrix

| Subsystem / Feature | Module / Source File | Truth Status | Verification Evidence |
|---|---|---|---|
| **Local Speech-to-Text** | `engine/stt_engine.py` | Implemented & Behaviorally Verified | `tests/test_stt.py`, bundled faster-whisper models int8 CPU. |
| **Zero Cloud Egress** | `engine/stt_engine.py`, `engine/orchestrator.py` | Implemented & Behaviorally Verified | `tests/test_network_egress.py` (strict socket binding check). |
| **Audio Capture & Ducking** | `engine/audio_recorder.py`, `engine/audio_ducker.py` | Implemented & Behaviorally Verified | `tests/test_audio.py`, `tests/test_audio_ducker.py`. |
| **Persistent Mic Identity** | `engine/audio_devices.py` | Implemented & Behaviorally Verified | `tests/test_audio_devices.py` (sentinel -9999, name matching). |
| **Bounded Stream Safety** | `engine/audio_recorder.py` | Implemented & Behaviorally Verified | `tests/test_pilot_reliability.py` (PR #1 timeout tests). |
| **Silero VAD v5** | `engine/silero_vad.py` | Implemented & Behaviorally Verified | `tests/test_silero_vad_resolution.py`. |
| **Spoken Self-Correction** | `engine/correction_intent.py` | Implemented & Behaviorally Verified | `tests/test_correction_intent.py` (755 lines deterministic). |
| **FactGuard Entity Guard** | `engine/writing_intelligence.py` | Implemented & Behaviorally Verified | `tests/test_writing_intelligence.py`, `tests/test_factguard_v2.py`. |
| **UIPI Integrity Check** | `engine/windows_integrity.py` | Implemented & Behaviorally Verified | `tests/test_pilot_reliability.py` (token integrity inspection). |
| **Truthful Injection Status** | `engine/text_injector.py` | Implemented & Behaviorally Verified | `tests/test_text_injector.py`, `tests/test_user_facing_fixes.py`. |
| **Recovery Actions & HUD** | `engine/orchestrator.py` | Implemented & Behaviorally Verified | `tests/test_recovery_feedback.py` (Shift+Alt+Z / Shift+Alt+X feedback). |
| **Native Win32 Global Hotkeys**| `engine/hotkey_service.py` | Implemented & Behaviorally Verified | `tests/test_win32_hotkey.py`, `tests/test_hotkey.py`. |
| **PySide6 Mascot & Floating HUD**| `ui/floating_hud.py` | Implemented & Behaviorally Verified | `tests/test_desktop_app.py`, `tests/test_sondercat_companion.py`. |
| **Context Aware Companion Hide**| `ui/companion_visibility_controller.py`| Implemented & Behaviorally Verified | `tests/test_companion_visibility.py` (fullscreen & peak polling).|
| **Local Dictation History** | `engine/history_vault.py` | Implemented & Behaviorally Verified | `tests/test_transforms_and_history.py`. |
| **Meeting Notetaker Engine** | `engine/meeting_notetaker.py` | Implemented & Behaviorally Verified | `tests/test_meeting_notetaker.py`, `tests/test_meeting_notetaker_v2.py`. |
| **Offline Indic ASR** | `ui/settings_dialog.py`, `ui/setup_wizard.py` | Implemented & Behaviorally Verified | `tests/test_pilot_reliability.py` (download notice validation). |
| **Benchmark Delivery Observer**| `benchmarks/delivery_observer.py` | Implemented & Behaviorally Verified | `tests/test_delivery_observer.py` (monotonic deadline observer). |
| **Selected-Text Transforms** | `engine/transforms_engine.py` | Partially Implemented | Scratchpad text edits supported; external window replace/revert disabled until selection adapter is built. |
| **External Window In-Place Revert**| `engine/transforms_engine.py` | Documented but Not Implemented | Stored as spec; requires native accessibility caret selection. |
| **Cross-Platform macOS/Linux** | `engine/cross_platform_adapter.py` | Partially Implemented | Fallback adapters written (`osascript`, `xdotool`); primary focus Windows. |
