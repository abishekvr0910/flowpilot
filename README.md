# FlowPilot

Local voice dictation for Windows, with a native PySide6 interface.

[Get started](QUICKSTART.md) · [Current status and handoff](docs/STATUS.md) · [Privacy](PRIVACY.md) · [Support](SUPPORT.md) · [Downloads](https://github.com/abishekvr0910/flowpilot/releases)

[![CI](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml)
[![MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Current status

As checked on November 14, 2026, the latest published Windows download is [v3.1.3](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.1.3). Its installer and ZIP are unsigned. Source is version **3.2.2** and includes later changes; local build records for 3.2.x do not establish a published release. See the [artifact manifest](docs/release/RELEASE_ARTIFACT_MANIFEST.md) for the distinction and checksums.

FlowPilot has working dictation, formatting, recovery, model setup, and desktop tools. Broad editor compatibility, speech quality across speakers, and release readiness require continued measurement. The [scope](docs/scope/index.md) and [current handoff](docs/STATUS.md) track these limits.

## What it does

- Transcribes locally using faster-whisper. Current source detects CUDA when available and falls back to CPU INT8; downloaded releases may use different device defaults.
- Offers optional local Tamil specialist recognition and explicit model downloads in Settings. Model downloads require a network connection during setup; dictation does not download models.
- Cleans text with deterministic formatting and FactGuard checks for critical facts. Recognition and formatting can still make mistakes.
- Inserts at the active cursor with focus checks. Results distinguish confirmed text, sent but unverified input, and failed delivery with recovery.
- Provides transform previews and Copy Output. External selection rewrite and undo are disabled pending document revision and selection verification. Scratchpad edits use separate transactions.
- Includes optional local history, dictionary, snippets, meeting notes, companions, and a separately started loopback API.

Dictation history is off for new profiles. Existing profiles retain their preferences. The microphone may remain open to maintain an adaptive audio buffer of approximately 0.35 to 0.85 seconds. See [privacy and data lifecycles](PRIVACY.md).

## Install or run

Download the versioned installer or portable ZIP from [GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases). Verify the matching checksum and signing status before opening it.

For source development, use Python 3.12 (CI target; package range is 3.10 through 3.12):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -X utf8 desktop_app.py
```

Provision local models using the explicit setup steps in [QUICKSTART.md](QUICKSTART.md#running-current-source). Normal dictation does not require VB-Cable or traffic capture tools. Windows is the supported release target; Linux and macOS adapters are development paths.

## Dictation and recovery

Place the cursor in your editor. With a new profile, press **Ctrl+Shift+Space**, speak, then press it again. Automatic silence stopping is **off by default**; enabling it uses a default 2.5-second timeout. Saved profiles may differ.

| Action | Control |
| --- | --- |
| Dictation | Shortcut and toggle/push-to-talk mode chosen in Settings |
| Legacy F9 alias / TapLatch | Available while legacy aliases remain enabled; behavior follows the chosen mode |
| Paste last dictation | Ctrl+Alt+V or Alt+Shift+Z |
| Copy last dictation | Alt+Shift+X or the tray action |
| Transform preview | Ctrl+Alt+T |
| Switch language | Ctrl+Alt+L or the tray menu |

Check for delayed text before recovering to avoid duplicate insertion. Use the target editor's own Undo for external edits. Alt+Shift+U remains reserved but does not perform an external rewrite rollback.

## Configuration

Settings are stored at `%USERPROFILE%\.flowpilot\config.json`. Selected defaults in current source:

```json
{
  "engine_mode": "local",
  "local_model_size": "base",
  "device": "auto",
  "compute_type": "auto",
  "language": "en",
  "hotkey": "<ctrl>+<shift>+<space>",
  "hotkey_mode": "toggle",
  "active_tone_mode": "developer",
  "auto_stop_on_silence": false,
  "silence_timeout_sec": 2.5,
  "telemetry_enabled": false,
  "save_history_text": false
}
```

## Optional local API

The desktop launcher does not start the integration server. Set `FLOWPILOT_API_TOKEN` to a random value of at least 32 characters, then run `npm run start:web`. Clients must send that token as a Bearer credential.

The server listens on `127.0.0.1:8765` and provides a subset of OpenAI-style transcription endpoints, including `/v1/audio/transcriptions` and `/v1/models`. Client compatibility must be checked individually. See [security boundaries](SECURITY.md).

## Verification

```powershell
python -X utf8 scripts/check_repository_consistency.py
python -X utf8 tests/run_all_tests.py
npm test
```

The runner prints its suite count and separates passes, skips, and failures. Release verification adds `--require-all` and requires an interactive Windows desktop, microphone, local models, and a freshly built matching executable. Headless checks and an older binary do not verify a new release.

See [known issues](docs/testing/flowpilot_known_issues.md), the [benchmark protocol](docs/testing/FLOWPILOT_BENCHMARK_PROTOCOL.md), and [trust and evidence](TRUST.md). No paired benchmark in this cleanup establishes superiority over Handy or Wispr Flow.

## Documentation and contributions

- [Current status / next agent handoff](docs/STATUS.md)
- [Scope and priorities](docs/scope/index.md)
- [Handy source comparison](docs/research/HANDY_SOURCE_REVIEW_2026-11-14.md)
- [Architecture](docs/architecture/flowpilot_desktop_architecture.md)
- [Build and release](docs/release/flowpilot_build_and_release.md)
- [Contributing](CONTRIBUTING.md)
- [Historical documents](docs/archive/README.md)

Application code is MIT licensed. See [LICENSE](LICENSE) and [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for dependency and asset attribution. Pixel Kitty is adapted from SondeR cat by Verisonder under Apache-2.0.
