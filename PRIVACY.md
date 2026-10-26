# FlowPilot Privacy Policy & Architecture Disclosure

**Last reviewed:** October 26, 2026<br/>
**Scope:** Current `master` source (v3.1.0). The published v3.0.2 release is a different build.

---

## 🔒 Executive Summary

FlowPilot is designed for local speech processing. This page describes what the current source code does; it is not a third-party privacy certification.

1. **100% Offline Local Inference:** All speech recognition is performed locally on your computer's CPU using `faster-whisper` and quantized INT8 models.
2. **Local Dictation Path:** The core dictation path does not upload microphone audio to a remote speech service. Setup downloads, optional integrations, and the application receiving the text have separate network behavior.
3. **Local Window Metadata:** FlowPilot reads the foreground window handle, title, and process name through Win32 APIs; it does not capture screenshots for dictation context. Current diagnostics can print the active window title.
4. **Dictation Never-Store by Default:** With `save_history_text: false`, completed dictation transcripts and WAV audio are not added to the History Vault. Existing saved entries and meeting notes are separate and are not erased by changing this setting.
5. **No Remote Telemetry by Default:** Optional pilot diagnostic metrics are disabled by default (`telemetry_enabled: false`) and are not written for dictations in never-store mode.

---

## 1. What Data FlowPilot Processes

| Data Type | Processed Locally? | Sent Over Network? | Stored on Disk? |
|:---|:---:|:---:|:---:|
| **Microphone Audio** | Yes | No upload in the local dictation path | Only when dictation history is enabled: completed WAV files in the local vault |
| **Transcribed Text** | Yes | No upload in the local dictation path | Only when dictation history is enabled; meeting notes are stored separately when used |
| **Active Window Metadata** | Yes (handle, title, process name) | No upload in the local dictation path | The opt-in vault records the target app; console capture can also retain window titles independently of history |
| **Configuration Settings** | Yes | The optional loopback API exposes settings to connected clients | Yes (`%USERPROFILE%\.flowpilot\config.json`) |
| **Pilot Diagnostic Metrics** | Optional | No remote telemetry in the current implementation | Only if both `telemetry_enabled` and dictation history are enabled |

---

## 2. Local Data Lifecycle

- **Recording Buffer:** Audio frames are captured in RAM for transcription. With dictation history enabled, completed audio is saved as a WAV file in the vault. Python memory management does not guarantee forensic erasure of old buffers.
- **Warm Microphone:** Desktop startup opens a microphone stream to maintain the short pre-roll buffer before a dictation trigger. The microphone can therefore remain open while the app is idle; quitting releases the stream. History-off does not mean the microphone stream is closed.
- **Dictation History:** `save_history_text: false` (default) prevents new dictation audio, transcript text, legacy config history, insights, and pilot metrics from being written. It does not erase existing records. When explicitly enabled, `~/.flowpilot/history/history_vault.json` stores raw and formatted transcripts, date, language, duration, and target application; `~/.flowpilot/history/audio/` stores associated WAV files. `FLOWPILOT_CONFIG_DIR` can relocate this data. The History view can delete individual entries or clear unstarred entries. Starred entries remain until separately deleted.
- **Meeting Notes:** Meeting transcription and notes are stored locally under `~/.flowpilot/meetings/` when the meeting feature is used.
- **Scratchpad:** Text entered into the scratchpad is autosaved separately to `~/.flowpilot/scratchpad_autosave.txt`. Dictation-history settings do not disable this feature's storage.
- **Clipboard Recovery Buffer:** The most recent dictation text is also cached in process memory for "Copy Last Dictation". This is separate from the persistent history vault.
- **Console Output:** Dictation progress messages use counts and timings, but diagnostics can also include window titles, process names, local paths, and exception details. Capturing stdout can persist that metadata even with history disabled. Inspect logs before sharing; complete diagnostic redaction has not been established.

New profiles default to history off; existing profiles retain their saved setting. Disabling history prevents new writes through the completed-dictation persistence path, but does not erase old entries, exports, backups, or data saved by other features. The in-memory recovery buffer is replaced by later dictations and cleared when the process exits.

Local JSON/text/WAV files are not encrypted by FlowPilot. Protection depends on your Windows account, filesystem permissions, and disk encryption. Never-store mode is not a guarantee against Windows paging/crash dumps, third-party clipboard history or synchronization, destination-app storage, or filesystem backups. Clipboard restoration handles text and does not preserve every rich clipboard format.

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

Optional local text transforms send selected text or the latest dictation to the configured loopback model service. That service is a separate process with its own logging, retention, and network configuration. The optional integration API requires a separate user-provided token for REST/WebSocket access; keep it on loopback and do not expose it through LAN bindings, port forwarding, or public tunnels. API uploads are a separate path from desktop microphone dictation, and the desktop never-store setting does not establish zero temporary-file usage in the HTTP framework.

---

## 4. Cloud Mode

Cloud transcription is disabled in the current source. Setting `engine_mode` to `"cloud"` raises an error; it is not a supported fallback. The local OpenAI-compatible API is an integration endpoint on `127.0.0.1`, not an OpenAI cloud connection.

The optional web companion no longer offers cloud transcription or asks for
Groq/OpenAI keys. On the next configuration load, old unused cloud provider and
API key fields are removed from the loaded settings, and the active config file
is rewritten when its storage is writable. Existing backups and copies are not
erased by this migration.

---

## 5. Contact & Auditing

FlowPilot is open-source under the MIT license, with separately licensed dependencies and assets. Use [SUPPORT.md](SUPPORT.md) for ordinary problems and [SECURITY.md](SECURITY.md) for private vulnerability reporting. See [TRUST.md](TRUST.md) for evidence and release scope.
