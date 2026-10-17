<div align="center">

# FlowPilot ⚡

### Windows-First High-Performance Voice Dictation (with Cross-Platform Architecture)
**100% Offline • Measured ~1.2s Median Latency • Local OpenAI STT Endpoint • Verified Zero Cloud Egress**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Windows-First | Linux | macOS](https://img.shields.io/badge/Platform-Windows--First%20%7C%20Linux%20%7C%20macOS-0078D6.svg)](README.md)
[![Engine: faster--whisper](https://img.shields.io/badge/ASR-faster--whisper%20(INT8)-orange.svg)](https://github.com/SYSTRAN/faster-whisper)
[![UI: PySide6 / Qt](https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-41CD52.svg?logo=qt)](https://www.qt.io/)
[![Zero Cloud Egress](https://img.shields.io/badge/Privacy-100%25%20Local%20Offline-success.svg)](PRIVACY.md)

</div>

---

## 📖 Overview

**FlowPilot** is an open-source, local-first desktop voice dictation assistant built for power users, developers, and privacy-conscious professionals.

FlowPilot delivers seamless voice-to-text directly at your cursor in desktop applications without cloud subscriptions, without network latency variance, and without sending private audio recordings or screen captures to remote servers.

---

## ✨ Key Capabilities

| Feature | Description |
|:---|:---|
| 🔒 **100% Offline & Private** | Powered by local `faster-whisper` INT8 on CPU. Zero network egress during core dictation loop. No accounts, no telemetry, no cloud dependencies. |
| 🔌 **Local OpenAI-Compatible API** | Drop-in `POST /v1/audio/transcriptions` and `GET /v1/models` local endpoint (`http://127.0.0.1:8765/v1`) for seamless integration with Cursor IDE, Open WebUI, and Obsidian plugins. |
| 🛡️ **FactGuard™ & Writing Intelligence** | Deterministic post-processing engineered to remove stutter and vocal fillers (`um`, `uh`), clean repeated words, auto-punctuate, and preserve numbers, dates, negations, and technical symbols. |
| 🤖 **Optional Local LLM Pass** | Connects strictly to localhost Ollama (`http://127.0.0.1:11434`), LM Studio, or llama.cpp for generative Command Mode and tone transformations while remaining 100% offline. **Target Safety:** Selected-Text Transforms (`Ctrl+Alt+T`) operate directly on highlighted text (or the last dictation buffer if nothing is selected). Original text is always restorable instantly via **`Alt+Shift+Z`**. |
| ⚡ **Measured Fast Local Latency** | Direct float32 audio streaming, greedy decoding (`beam_size=1`), and instant native text injection (**measured median 1,202 ms stop-to-text, p95 1,460 ms** on 8-thread CPU test host for direct Whisper base INT8 inference). *Optional local LLM rewrite passes add ~0.5–2s depending on local hardware and model choice.* |
| 🎙️ **Flexible Voice Controls & TapLatch™** | Choose between **F9 Push-to-Talk** (hold to speak, release to paste), **TapLatch™** (double-tap <350ms to lock hands-free, tap to stop), or **Ctrl+Shift+Space Toggle** with automatic 0.85s conversational pause finalization. |
| 🔄 **Continuous Pre-Roll Ring Buffer** | 350ms sliding float32 audio ring buffer with background stream warmup (`warmup_stream()`) completely eliminates PortAudio latency and guarantees zero first-syllable speech loss. |
| 📋 **Atomic Win32 & POSIX Clipboard Guard** | Hardware sequence counter (`GetClipboardSequenceNumber`) prevents clobbering user clipboard data during paste restoration; includes instant **Alt+Shift+Z** re-paste recovery. |
| 💻 **Developer Vocabulary Biasing** | Built-in terminology dictionary biasing for engineering terms (`Kubernetes`, `GraphQL`, `FastAPI`, `Pydantic`, `TypeScript`, `Docker`, `PostgreSQL`). |
| 📝 **Meeting Notetaker & History Vault** | Continuous meeting capture with extractive action items, plus a local dictation vault with `.wav` audio replay and bookmarking. |
| 🐾 **Customizable Desktop Companions** | Moveable desktop companions that sit anywhere on your screen (snaps to any corner/edge with zero text clutter). Includes the **SondeR-Cat Pixel Kitty** (with 10 fur palettes and audio-reactive kneading paws), **Robot Mascot ("Pilot")**, **Retro Pixel Companions (Fox, Dino, Ghost, Bunny)**, and custom pixel art. Zero focus-stealing (`WS_EX_NOACTIVATE`). |

---

## 🚀 Quick Start (Choose Your Preferred Method)

*For a 60-second setup walkthrough, see [QUICKSTART.md](QUICKSTART.md).*

### Method A: Standalone Packaged Release (Windows)
*No Python or compiler required.*

- **Distribution Archive:** ~240 MB compressed ZIP ([GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release))
- **Primary Executable:** Standalone entrypoint (`FlowPilot.exe`) or one-click `start_desktop.bat`

1. Download **`FlowPilot-v3.0.2-win64.zip`** (or clone the repository).
2. Double-click **`FlowPilot.bat`** (or `FlowPilot.exe`).
3. The **Pilot Companion** appears on your desktop (draggable anywhere, snaps to any corner), and the FlowPilot icon will sit in your System Tray.

### Method B: Running from Source (Windows-First, Linux, macOS)

```bash
# Windows
.\FlowPilot.bat
# or: python desktop_app.py

# Linux (Debian, Ubuntu, Fedora)
# sudo apt install libportaudio2 xdotool pulseaudio-utils
python3 desktop_app.py

# macOS (Apple Silicon / Intel)
# brew install portaudio
python3 desktop_app.py
```

---

## 🎙️ How to Dictate

1. **Place your cursor** into any text field or editor (VS Code, Notepad, Browser, Discord, Word).
2. **Activate FlowPilot**:
   - **Toggle Mode (Default):** Press **`Ctrl + Shift + Space`**. The HUD glows cyan indicating active listening. Speak naturally. Press **`Ctrl + Shift + Space`** again (or pause for 0.85s) to finalize.
   - **Push-to-Talk Mode:** Press and hold **`F9`**. Speak your thought. Release **`F9`** to finalize.
   - **TapLatch™ Hands-Free:** Rapid double-tap **`F9`** (<350ms) to lock dictation hands-free without holding the key. Tap **`F9`** once to finalize.
   - **Selected-Text Transforms:** Highlight text anywhere and press **`Ctrl + Alt + T`** to reformat, summarize, or fix grammar.
3. FlowPilot transcribes, polishes, and types the text directly at your cursor with zero syllable clipping (powered by our 350ms pre-roll sliding buffer).
4. **Instant Re-Paste Shortcut:** Press **`Alt + Shift + Z`** anywhere in Windows to immediately re-paste your last dictation buffer into the focused window.
5. **Emergency Recovery:** If target application blocks clipboard pasting, your dictation is safely held in memory. Simply right-click the System Tray icon and select **"Copy Last Dictation"**.

---

## 🐾 Desktop Companions & Visual Styles

FlowPilot gives you multiple visual companion options to match your workflow:

| Visual Style | Appearance & Behavior | Interaction |
|:---|:---|:---|
| 🐾 **SondeR-Cat Pixel Kitty** | Upright 26x28 pixel cat with 10 fur palettes (Orange Tabby, Calico, Black, Gray, Siamese, Pink, White, Mint, Chocolate, Cream). Paws knead at voice speed when speaking, eyes glow during transcription, and floating hearts appear on paste with optional cheerful meows! | Right-click → **Appearance Style → SondeR-Cat Pixel Kitty**; choose fur color from **Kitty Fur Color...** |
| 🤖 **Robot Mascot ("Pilot")** | Cute rounded companion robot with radiating acoustic antenna, expressive blinking eyes with real-time voice-reactive pupil dilation, thinking spiral eyes during transcription, and happy smile on paste. | Right-click → **Appearance Style → Robot Mascot Companion ('Pilot')** |
| 🐶 **Pixel Pup & Shiba** | Playful pixelated dog companion with multiple breeds and tail-wag animation. | Right-click → **Appearance Style → Pixel Pup & Shiba** |
| 🦊 **Retro Companion Series** | Pixel Fox, Dino, Ghost, and Bunny retro companion sprites with animated tail wags, hops, and glows. | Selected via Companion Studio dialog or Dashboard |
| 📏 **Edge Line** | Ultra-minimal docked vertical line. Pulses with audio volume; zero screen distraction. | Right-click → **Appearance Style → Edge Line** |
| 🌊 **Acoustic Wave Equalizer** | 5 dancing acoustic frequency bars reacting to speech RMS. | Right-click → **Appearance Style → Acoustic Wave Equalizer** |

### Positioning & Moving Companions
- **Drag & Drop:** Click and hold the companion with your mouse to drag it to any pixel on your desktop.
- **One-Click Snap:** Right-click the companion → **Move Companion to...** → Select **Bottom-Right**, **Bottom-Left**, **Top-Right**, **Top-Left**, **Left Edge (Middle)**, **Right Edge (Middle)**, or **Bottom-Center**.
- **Quick Style Switching:** Double-click the companion anytime to cycle seamlessly through all styles.
- **Zero Focus-Stealing:** All companions use Win32 `WS_EX_NOACTIVATE` and XWayland shims so they never steal focus from your active code editor or browser.

---

## 🔌 OpenAI-Compatible Local STT API

FlowPilot exposes an embedded, zero-cloud drop-in replacement for the OpenAI Audio Transcription API at `http://127.0.0.1:8765/v1`:

- **Transcribe Audio:** `POST http://127.0.0.1:8765/v1/audio/transcriptions` (supports `json`, `text`, and `verbose_json` formats)
- **Model Catalog:** `GET http://127.0.0.1:8765/v1/models` (reports `whisper-1`)

### Connecting Third-Party Tools
- **Cursor IDE / VS Code:** Set OpenAI Audio Base URL to `http://127.0.0.1:8765/v1` and API key to `local`.
- **Open WebUI / LibreChat:** Configure audio transcription service URL to `http://127.0.0.1:8765/v1`.
- **Obsidian Whisper Plugin:** Direct audio requests to local FlowPilot port `8765`.

---

## ⚙️ Configuration & Customization

FlowPilot stores its configuration locally in your user profile:
`%USERPROFILE%\.flowpilot\config.json`

You can customize settings via the System Tray context menu (**Right-Click Tray Icon → Settings**) or by editing `config.json` directly:

```json
{
  "engine_mode": "local",
  "local_model_size": "base",
  "language": "en",
  "hotkey": "<ctrl>+<shift>+<space>",
  "hotkey_mode": "toggle",
  "active_tone_mode": "developer",
  "auto_stop_on_silence": true,
  "silence_timeout_sec": 0.85,
  "custom_vocabulary": [
    "Kubernetes", "GraphQL", "FastAPI", "Pydantic", "PostgreSQL",
    "Next.js", "TypeScript", "Python", "Whisper", "Docker"
  ],
  "telemetry_enabled": false,
  "save_history_text": false
}
```

### Available Tone Modes
- **`developer`** (Default): Preserves code identifiers, acronyms, and formatting while cleaning vocal fillers.
- **`cleaned`**: Standard conversational cleanup with natural punctuation and capitalization.
- **`verbatim`**: 100% exact acoustic transcript — zero filler removal or rewriting.
- **`casual`**: Conversational tone preserving expressive language.
- **`email`**: Structured business formatting.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    HK["Global Hotkey (Ctrl+Shift+Space / F9)"] -->|Win32 RegisterHotKey| ORCH["FlowOrchestrator"]
    ORCH -->|CoreAudio Ducking| DUCK["AudioDucker (pycaw)"]
    ORCH -->|Non-blocking Capture| REC["AudioRecorder (PortAudio)"]
    ORCH -->|WS_EX_NOACTIVATE| HUD["FloatingHUD (PySide6)"]
    
    REC -->|Contiguous Float32 Array| STT["STTEngine (faster-whisper INT8)"]
    STT -->|Raw Acoustic Transcript| WI["ContextProcessor & FactGuard"]
    WI -->|Negation & Number Preservation| FORMAT["Cleaned Formatted Text"]
    
    FORMAT -->|Confirmed Win32 Injection| INJ["TextInjector (SendInput / Paste)"]
    INJ -->|Focus Lock & Verification| APP["Target Application (Active Window)"]
    INJ -->|Safe Restoration| CLIP["Windows System Clipboard"]
```

---

## 🧪 Application Compatibility & Testing Status

| Environment | Tested Scope | Status | Result / Notes |
|:---|:---|:---:|:---|
| **Notepad (`notepad.exe`)** | Automated dictation cycles & 18-scenario E2E specification | **PASS (Verified on Real App)** | 20/20 and 5/5 consecutive cycles with physical Win32 edit buffer read-back verification (`tests/test_win32_e2e_scenarios.py`). |
| **Chromium & Electron Rich Surfaces** | Rich text contenteditable, input fields, and multi-line indent safety | **PASS (Simulated Surface)** | Verified via simulated Chromium/Electron surface in `tests/test_cross_app_injection.py` step 4b; standard Windows clipboard paste (`Ctrl+V`) applies to Chrome/Edge. Physical process readback tests queued. |
| **Modern Code Editors & Markdown (VS Code / Cursor / Obsidian)** | Multi-line code comments, markdown formatting, and atomic clipboard guard | **PASS (Simulated Surface)** | Verified via simulated rich-editor surface in `tests/test_cross_app_injection.py`. Uses standard Win32 clipboard injection with sequence check; physical process readback tests queued. |
| **Multi-Speaker Accent Panel** | Human panel with regional accents and noisy acoustic backgrounds | **OPEN / Field Pilot Scheduled** | Automated synthetic SAPI multilingual suite is passing (`tests/test_multilingual_speech_reality.py`); 10-participant human accent evaluation protocol designed and scheduled for upcoming milestone. |

---

## 🔧 Troubleshooting & FAQ

#### Win32 Hotkey Error 1409 (`ERROR_HOTKEY_ALREADY_REGISTERED`)
- **Cause:** Another running application (e.g., PowerToys, Discord, or an older instance of FlowPilot) is already listening to `Ctrl+Shift+Space`.
- **Solution:** Right-click the Tray icon, open **Settings**, and switch your shortcut to `Ctrl+Alt+Space` or `F9`. FlowPilot includes single-instance mutex enforcement to prevent duplicate background processes.

#### Microphone Not Capturing Sound
- Open Windows **Settings → Privacy & security → Microphone** and verify that desktop apps are permitted to access your microphone.
- FlowPilot automatically detects your default Windows recording device.

#### Text Doesn't Paste into an Elevated Application (Administrator Terminal)
- Under Windows security architecture (UAC), a standard user process cannot inject input into an Administrator/elevated window.
- **Solution:** Launch FlowPilot as Administrator if you frequently dictate into elevated command prompts or terminals.

---

## 🔒 Privacy & Security

FlowPilot is built on a **Local-First, Zero Egress Architecture**:
- **Local Speech Inference:** Speech models (`faster-whisper`, `silero-vad`) execute purely on your local CPU via CTranslate2 and ONNX Runtime with `local_files_only=True`.
- **Zero Screenshots:** FlowPilot never inspects or captures screen images.
- **Tested Network Isolation:** Verified via automated loopback socket monitoring ([`tests/test_network_egress.py`](tests/test_network_egress.py)) confirming 0 open external sockets during speech capture and transcription.
- **No Cloud Telemetry by Default:** Diagnostic telemetry is disabled by default (`telemetry_enabled: false`).
- **Volatile Storage:** Audio buffers and transcripts are kept in RAM and discarded immediately after insertion.

Read our complete [PRIVACY.md](PRIVACY.md) and [SECURITY.md](SECURITY.md) documents.

---

## 📚 Project Documentation

Detailed technical and engineering documentation is structured in [`docs/`](docs/):

- **[Architecture & Design](docs/architecture/):** Desktop internals, Win32 window management, and Wispr Flow feature inventory.
- **[Testing & Benchmarks](docs/testing/):** Automated test reports, acoustic reality assessment, and model benchmark data.
- **[Security & Governance](docs/security/):** Zero-egress network forensics and [Branch Protection Governance](docs/security/GITHUB_BRANCH_PROTECTION.md).
- **[Release & Checklists](docs/release/):** [Artifact Manifest](docs/release/RELEASE_ARTIFACT_MANIFEST.md), v3.0.2 release verification, and PyInstaller build specifications.
- **[Pilot Program](docs/pilot/):** 10-participant testing protocol, feedback frameworks, and evaluation rubrics.

---

## 📜 Licensing & Attribution

FlowPilot application code is released under the **MIT License**. See [LICENSE](LICENSE) for details.

FlowPilot bundles third-party open-source components including:
- **PySide6 / Qt 6** (LGPL v3 — dynamically linked, user relinking supported)
- **faster-whisper** (MIT License, SYSTRAN)
- **CTranslate2** (MIT License, OpenNMT)
- **Silero VAD** (MIT License, Silero Team)
- **sounddevice & PortAudio** (MIT / PortAudio License)

See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for full license texts and attributions.
