# Wispr Flow Forensic Technical Dossier

**Target**: Wispr Flow (Desktop AI Dictation Client by Wispr AI, Inc.)  
**Investigated Version**: 1.6.1209 (Windows 64-bit Squirrel / Electron Package)  
**Date of Investigation**: 2026-10-23 – 2026-10-25  
**Evidence Standard**: Directly observed filesystem artifacts, unpacked bundles, local SQLite database schemas, live process telemetry, and official vendor documentation.

---

## 1. Source Register & Evidence Confidence Levels

| Evidence Source | Location / Identifier | Confidence Level | What It Proves |
|---|---|---|---|
| **Shipped Windows Package** | `%LOCALAPPDATA%\WisprFlow\app-1.6.1209\` | Direct Fact (100%) | Shipped executable binaries, DLL dependencies, native addons, and packaging structure. |
| **Electron Main & Renderer Bundle** | `resources\app.asar` (136.2 MB; 213 files, 47.1 MB script extracted) | Direct Fact (100%) | Client JavaScript architecture, API routes, database schemas, feature flags, hotkeys, and UI workflows. |
| **Native Helper Process** | `resources\Release\Wispr Flow Helper.exe` (20.4 MB, 63.8 MB RSS) | Direct Fact (100%) | Native Win32 API imports (`SetWindowsHookEx`, `SendInput`, `UIAutomation`, `IAudioSessionEnumerator`). |
| **Local SQLite Vault** | `%APPDATA%\WisprFlow\flow.sqlite` (332 MB) | Direct Fact (100%) | Local schema, migration history, telemetric schema (`e2eLatency`, `clientNetworkLatency`, `speechDuration`, `numWords`), and field metrics over historical dictation records. |
| **Vendor Documentation & Support** | `wisprflow.ai`, help center, shortcut guide | Evidence-Backed Fact | Public interface commitments, enterprise HIPAA/SOC2 terms, officially documented recovery shortcuts (`Shift+Alt+Z`, `Shift+Alt+X`). |
| **Process & Resource Telemetry** | Windows Task Manager / `Get-Process` | Direct Fact (100%) | 12 processes, 814.7 MB idle RSS, multi-process memory footprint. |

---

## 2. System Architecture & Component Inventory

```
+-----------------------------------------------------------------------------------+
|                                Wispr Flow (Client)                                |
|                                                                                   |
|  +---------------------------+     IPC      +----------------------------------+  |
|  |     Electron Renderer     |<------------>|          Electron Main           |  |
|  |   (Chromium, React UI,    |              | (Node.js, SQLite Vault, Hotkeys, |  |
|  |    Settings, Notes View)  |              |  Audio Streamer, Config Store)   |  |
|  +---------------------------+              +----------------------------------+  |
|                |                                              |                   |
|                v                                              v                   |
|  +---------------------------+              +----------------------------------+  |
|  |     Pill / HUD Window     |              |       Wispr Flow Helper.exe      |  |
|  |    (Native Floating Bar)  |              |   (Native Win32 Hooks, UIA,      |  |
|  +---------------------------+              |    Audio Metering, SendInput)    |  |
+---------------------------------------------------------------|-------------------+
                                                                |
                                             WSS / TLS (OPUS)   |
                                                                v
                                              +-----------------------------------+
                                              |       Wispr Cloud Backend         |
                                              |  - Cloud STT (Whisper Large-v3)   |
                                              |  - Cloud LLM Contextual Cleanup   |
                                              |  - Note Summarization & Chat      |
                                              +-----------------------------------+
```

### 2.1 Process Footprint & Resource Utilization
- **Process Count**: 12 processes running concurrently:
  - 1 Electron Browser Main process.
  - 1 Crashpad handler process.
  - 1 GPU process.
  - 6 Chromium utility/render processes.
  - 2 Node worker threads / background processes.
  - 1 Persistent native helper process (`Wispr Flow Helper.exe`).
- **Memory Consumption**:
  - Baseline idle footprint: **814.7 MB** resident set size (RSS).
  - Active dictation peak: **>1,350 MB** RAM across all 12 processes.
- **Binary Footprint on Disk**:
  - `Wispr Flow.exe`: 235.4 MB.
  - `resources\app.asar`: 136.2 MB.
  - `Wispr Flow Helper.exe`: 20.4 MB.
  - Total directory size: **~480 MB** (excluding local SQLite databases and Chromium cache).

---

## 3. Audio Capture, VAD, and Streaming Pipeline

### 3.1 Audio Ingestion
- Audio is captured using standard Windows multimedia APIs and hardware integrations:
  - Jabra Device SDK (`GNAudio DeviceApis` DLLs + `jabra-device-conn` node addon) enables direct hardware button integration for headset push-to-talk (`speedDial`, `pushToTalkRoip`, `customButton1-3`).
- Audio samples are packaged into OPUS audio chunks (`opusChunks`) at 16 kHz or 24 kHz.

### 3.2 Voice Activity Detection (VAD) & Silence Detection
- Employs silence streak analysis in client code:
  - Tracks `longestSilentStreakMs`, `audioActiveRatio`, `gracePeriodMs`.
  - Automatically terminates dictation session (`autoEnded=true`) upon sustained silence exceeding threshold.

### 3.3 Streaming Protocol
- Streams OPUS chunks in real-time over WebSocket TLS connections (`wss://api.wisprflow.ai/` or regional endpoints).
- No on-device speech-to-text inference. If network is disconnected, dictation cannot start or transcribe.

---

## 4. Transcription, Formatting, and LLM Post-Processing

### 4.1 Speech-to-Text Layer
- Cloud-hosted STT (primarily OpenAI Whisper Large-v3 or fine-tuned variants).
- Schema records `defaultAsrText` and `fallbackAsrText` with `fallbackLevel`.
- In the investigated user vault (1,851 sessions), fallback ASR was triggered 0 times, confirming high cloud uptime but complete reliance on remote cluster availability.

### 4.2 Formatting & Disfluency Removal
- Cloud LLM cleans and structures raw transcripts:
  - Automatically strips fillers ("um", "ah", "like").
  - Resolves self-corrections (e.g., "meet at 4 pm actually 3 pm" -> "meet at 3:00 PM").
  - Formats punctuation, capitalization, lists, and numbers.
  - Calculates `formattingDivergenceScore` and tracks `editDistanceToDictated`.
- Tone matching: supports conversational dictation with tone matching pairs (`toneMatchedText`, `toneMatchPairs`).

---

## 5. Text Insertion, Application Compatibility, and Recovery

### 5.1 Text Injection Mechanics
1. **Target Window Inspection**: Inspects target window using `UIAutomation` and `GetForegroundWindow` to gather window metadata and accessible controls (`axText`, `axHTML`).
2. **Clipboard Caching**: Reads and stores existing system clipboard content into memory.
3. **Clipboard Population**: Writes formatted transcript onto system clipboard.
4. **Keystroke Simulation**: Dispatches `Ctrl + V` via native `SendInput` using `Wispr Flow Helper.exe`.
5. **Delayed Clipboard Restore**: Spawns a timer (~500 ms) to restore the user's prior clipboard data.

### 5.2 Failure Modes & Real-World Latency Lag
- **Slow-Application Paste Lag**: In heavy target applications (Slack, Notion, Visual Studio, IntelliJ IDEA), the application's response to `Ctrl + V` often exceeds the 500 ms restore delay. Consequently, the application pastes the *restored* prior clipboard rather than the dictation text, or pastes incomplete fragments.
- **UIPI Privilege Boundary (Error 5 / Elevation Conflict)**: Wispr Flow runs at medium integrity by default. When the user targets an elevated application (e.g. Administrator Command Prompt, PowerShell, Task Manager), Windows UIPI silently blocks simulated keystrokes. Official vendor troubleshooting explicitly instructs users to configure Wispr Flow to "Run as Administrator".
- **Target Lost Focus**: If the user clicks another window before the cloud response arrives, keystrokes are pasted into the newly focused application.

### 5.3 Dedicated Recovery Hotkeys
To mitigate injection failures and clipboard race conditions, Wispr Flow provides dedicated, hardware-bound recovery commands:
- **`Shift + Alt + Z`** ("Paste Last"): Re-injects the most recently generated transcript into the currently active window.
- **`Shift + Alt + X`** ("Copy Last"): Places the most recently generated transcript onto the clipboard without executing a paste keystroke.
- **Mac Equivalents**: `Cmd + Ctrl + V` (Paste Last) and `Cmd + Ctrl + C` (Copy Last).

---

## 6. Empirical Performance Metrics (Local SQLite Audit)

Analysis of the `History` table in `flow.sqlite` across **1,847 dictation sessions** (66,895 words, average speech duration 14.0 seconds, average length 36.2 words):

| Metric | Measured Value | Distribution / Significance |
|---|---|---|
| **Mean End-to-End Latency (`e2eLatency`)** | **906.6 ms** | Monotonic stop-to-cloud-response roundtrip |
| **Share under 500 ms** | **31.3%** (578 / 1,847) | Short commands (<5 words) |
| **Share under 1,000 ms** | **70.3%** (1,299 / 1,847) | Standard sentences |
| **Minimum Latency** | 26.0 ms | Cached / immediate response |
| **Maximum Latency** | 6,897.0 ms | Long dictation with LLM post-processing retry |
| **Mean Network RTT (`clientNetworkLatency`)** | **195.0 ms** | Baseline physical latency floor imposed by cloud egress |

---

## 7. Security, Privacy, and Data Governance

- **Network Egress**: 100% of recorded dictations leave the device.
- **Data at Rest**: Telemetry, transcripts, meeting notes, and audio active ratios are stored locally in unencrypted SQLite (`flow.sqlite`) and synchronized to Wispr's cloud.
- **Compliance Commitments**:
  - SOC 2 Type II certified.
  - HIPAA Business Associate Agreement (BAA) offered for healthcare plans.
  - "Privacy Mode": Opt-out of model training, but audio and text are still processed through cloud infrastructure.
  - Zero local offline capability: Cannot be deployed in air-gapped, high-security, defense, or strict privacy environments.
