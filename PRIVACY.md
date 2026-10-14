# FlowPilot Privacy Policy & Architecture Disclosure

**Effective Date:** October 15, 2026  
**Product Version:** FlowPilot Desktop v3.0.2  

---

## 🔒 Executive Summary

FlowPilot is engineered from the ground up on the principle of **Zero Knowledge, Zero Egress, Local Execution**:

1. **100% Offline Local Inference:** All speech recognition is performed locally on your computer's CPU using `faster-whisper` and quantized INT8 models.
2. **Zero Audio Uploads:** Your microphone audio is never transmitted across the local network or internet.
3. **Zero Screen Captures:** Unlike cloud-based dictation services that capture screenshots for context, FlowPilot inspects only the foreground window's process name (e.g. `code.exe`) locally via Win32 OS APIs.
4. **Zero Persistent Dictation Logging:** FlowPilot does not log what you say to disk. Transcripts are processed in volatile memory (RAM) and immediately cleared.
5. **No Telemetry by Default:** All diagnostic telemetry is disabled out of the box (`telemetry_enabled: false`).

---

## 1. What Data FlowPilot Processes

| Data Type | Processed Locally? | Sent Over Network? | Stored on Disk? |
|:---|:---:|:---:|:---:|
| **Microphone Audio** | Yes (in RAM only) | **Never** | **Never** |
| **Transcribed Text** | Yes (in RAM only) | **Never** | **Never** (unless user enables history) |
| **Active App Window Name** | Yes (Win32 API) | **Never** | **Never** |
| **Configuration Settings** | Yes | **Never** | Yes (`%USERPROFILE%\.flowpilot\config.json`) |
| **Crash / Diagnostic Logs** | Yes (sanitized) | **Never** | No (opt-in only) |

---

## 2. In-Memory Processing & Volatile Lifecycle

- **Recording Buffer:** Audio frames are captured into a circular memory buffer in RAM. When recording stops, the buffer is fed to the local Whisper model. Once transcription completes, the audio buffer is wiped from memory.
- **Clipboard Recovery Buffer:** The most recent dictation text is temporarily cached in process memory so that the user can retrieve it via "Copy Last Dictation" from the System Tray if an application blocks pasting. This text is never written to disk and is destroyed when FlowPilot exits.
- **Console Output Privacy:** FlowPilot's stdout logs duration metrics and character counts only (`chars=42`). Raw user transcripts are never printed to terminal consoles or piped logs.

---

## 3. Network Egress Audit

FlowPilot has undergone automated forensic testing ([`tests/test_network_egress.py`](file:///S:/APPs/New%20folder/tests/test_network_egress.py)) verifying that during:
- Model loading
- Hotkey registration
- Microphone capture
- Transcription
- Text formatting
- Text injection

...exactly **zero** network socket connections (TCP/UDP) are established. FlowPilot operates with identical performance with your internet connection disabled.

---

## 4. Optional Cloud Provider Fallback (BYOK)

If you explicitly choose to switch `engine_mode` from `"local"` to `"cloud"` in settings, FlowPilot requires you to provide your own API key (Groq or OpenAI). In this scenario:
- Audio is sent only to the endpoint you specified using standard HTTPS.
- FlowPilot operates strictly as a client to your own cloud account; FlowPilot developers have no access to your API keys, audio, or transcripts.
- Local mode remains the default at all times.

---

## 5. Contact & Auditing

FlowPilot is open-source under the MIT license. You are encouraged to inspect the source code, verify network isolation via Wireshark or Sysinternals TCPView, and report any concerns via GitHub Issues.
