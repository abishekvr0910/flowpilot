# FlowPilot Privacy Policy & Architecture Disclosure

**Last reviewed:** October 18, 2026  
**Scope:** Current `master` source (v3.1.0-pilot). The published v3.0.2 release is a different build.  

---

## 🔒 Executive Summary

FlowPilot is designed for local speech processing. This page describes what the current source code does; it is not a third-party privacy certification.

1. **100% Offline Local Inference:** All speech recognition is performed locally on your computer's CPU using `faster-whisper` and quantized INT8 models.
2. **Zero Audio Uploads:** Your microphone audio is never transmitted across the local network or internet.
3. **Zero Screen Captures:** Unlike cloud-based dictation services that capture screenshots for context, FlowPilot inspects only the foreground window's process name (e.g. `code.exe`) locally via Win32 OS APIs.
4. **Local History Storage:** The current history vault saves completed dictation transcripts and WAV audio locally by default. Meeting notes are also saved locally when that feature is used.
5. **No Remote Telemetry by Default:** Optional pilot diagnostic metrics are disabled by default (`telemetry_enabled: false`). These settings do not disable the history vault.

---

## 1. What Data FlowPilot Processes

| Data Type | Processed Locally? | Sent Over Network? | Stored on Disk? |
|:---|:---:|:---:|:---:|
| **Microphone Audio** | Yes | No upload in the local dictation path | Yes: completed dictation WAV files in the local history vault |
| **Transcribed Text** | Yes | No upload in the local dictation path | Yes: completed dictations in the local history vault; meeting notes when used |
| **Active App Window Name** | Yes (Win32 API) | No upload in the local dictation path | Yes: the local history vault records the target application |
| **Configuration Settings** | Yes | **Never** | Yes (`%USERPROFILE%\.flowpilot\config.json`) |
| **Pilot Diagnostic Metrics** | Optional | No remote telemetry in the current implementation | Yes, if `telemetry_enabled` is enabled |

---

## 2. Local Data Lifecycle

- **Recording Buffer:** Audio frames are captured in RAM for transcription. Completed dictation audio is also saved as a WAV file in the history vault. Python memory management does not guarantee forensic erasure of old buffers.
- **Dictation History:** By default, `~/.flowpilot/history/history_vault.json` stores the raw and formatted transcript, date, language, duration, and target application; `~/.flowpilot/history/audio/` stores associated WAV files. `FLOWPILOT_CONFIG_DIR` can relocate this data. The `save_history_text` setting controls a separate legacy config history list; it does **not** disable the history vault. The History view can delete individual entries or clear unstarred entries. Starred entries remain until separately deleted.
- **Meeting Notes:** Meeting transcription and notes are stored locally under `~/.flowpilot/meetings/` when the meeting feature is used.
- **Clipboard Recovery Buffer:** The most recent dictation text is also cached in process memory for "Copy Last Dictation". This is separate from the persistent history vault.
- **Console Output Privacy:** FlowPilot's stdout logs duration metrics and character counts only (`chars=42`). Raw user transcripts are never printed to terminal consoles or piped logs.

---

## 3. Network Egress Audit

The [network egress regression test](tests/test_network_egress.py) blocks attempted non-loopback socket calls in its tested paths during:
- Model loading
- Hotkey registration
- Microphone capture
- Transcription
- Text formatting
- Text injection

This test is useful evidence for those paths, not a guarantee about every runtime configuration or a replacement for an independent network audit. The optional local integration API binds to loopback. Any separately configured local LLM integration should be evaluated under the user's own network policy.

---

## 4. Cloud Mode

Cloud transcription is disabled in the current source. Setting `engine_mode` to `"cloud"` raises an error; it is not a supported fallback. The local OpenAI-compatible API is an integration endpoint on `127.0.0.1`, not an OpenAI cloud connection.

---

## 5. Contact & Auditing

FlowPilot is open-source under the MIT license. You are encouraged to inspect the source code, verify network isolation via Wireshark or Sysinternals TCPView, and report any concerns via GitHub Issues.
