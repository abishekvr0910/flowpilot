# Get started with FlowPilot on Windows

FlowPilot turns speech into text using a local CPU model. You need a Windows PC, a microphone, and locally installed model weights. VB-Cable and traffic-capture tools are only for benchmarks.

The recorded published download is [v3.0.2](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release). Current source contains newer features and fixes. This guide labels those separately; check the release notes for the build you install.

## Install a published build

1. Download the Windows ZIP from the repository's GitHub release page. Check its SHA-256 against the matching [artifact manifest](docs/release/RELEASE_ARTIFACT_MANIFEST.md).
2. Extract the **whole folder**, including supporting libraries, and inspect the executable's publisher signature using the [release guide](docs/release/flowpilot_build_and_release.md). If Windows blocks the build, verify its origin before proceeding.
3. Run `FlowPilot.exe` as a normal user. Use the tray icon to access settings and quit.
4. Allow desktop microphone access in Windows Settings and select your intended recording device. Check that local model weights are available; current source will report a missing-model error rather than silently downloading them.

A ZIP's presence does not establish that it contains the latest fixes or a complete offline model cache. Check its release-specific notes.

## Running current source

Use Windows and Python 3.12, matching the current CI configuration:

```powershell
git clone https://github.com/abishekvr0910/flowpilot.git
cd flowpilot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On a connected machine, explicitly provision the default `base` model once. This setup command can contact Hugging Face and download model files; it does not capture speech:

```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

After provisioning, verify that the cache is readable without downloads, then start the app:

```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8', local_files_only=True)"
python desktop_app.py
```

If you select a different model, provision that model separately. For a disconnected deployment, prepare weights on a connected machine and transfer a complete model directory/cache through your normal approved process. Do not assume an empty Hugging Face cache folder contains model weights.

Linux and macOS adapters exist for development; the documented packaged-release target is Windows.

## Check privacy before the first dictation

New source profiles default to `save_history_text: false`. Existing profiles keep their saved choice. To inspect it, quit FlowPilot and review `%USERPROFILE%\.flowpilot\config.json`; restart after editing. Leave `telemetry_enabled` false unless you intentionally enable local pilot metrics.

History-off prevents new completed dictations from being saved through the vault/history path. It does not erase older entries or turn off meeting-note and scratchpad storage. The app keeps a short audio pre-roll in memory, so the microphone can remain open while FlowPilot is idle. See [PRIVACY.md](PRIVACY.md) for clipboard, log, and integration boundaries.

## Try one sentence

1. Open an ordinary, non-administrator Notepad window and click in its document.
2. Press **Ctrl+Shift+Space**, say a made-up sentence, and press the shortcut again to stop. Automatic silence finalization may stop recording first.
3. Wait for transcription and check the actual text in the document.
4. Try your normal editor next; compatibility and timing can differ by application.

Other controls in current source:

| Action | Control |
| --- | --- |
| Push to talk | Hold F9, speak, then release |
| Hands-free latch | Double-tap F9; tap again to stop |
| Recover the latest dictation | Alt+Shift+Z, or tray > Copy Last Dictation |
| Change appearance | Companion context menu or Companion Studio |
| Move the companion | Drag, or use its placement menu |

On laptops, F9 may require the Fn key or function-lock setting. Shortcut behavior also depends on your selected mode and conflicts with other apps.

## If text does not arrive

Check whether it appeared late before retrying. Place the cursor in the desired field, choose **Copy Last Dictation**, and paste manually. The in-memory buffer holds only the most recent dictation and is lost on exit. Repeating recovery can duplicate text.

See [SUPPORT.md](SUPPORT.md) for microphone, model, elevated-window, and reporting guidance. Use a synthetic phrase for reports and review diagnostic logs before attaching them.

## Voice formatting

Current-source formatting supports commands such as `comma`, `new line`, `new paragraph`, `scratch that`, `camel case user profile`, and `snake case api key`. Recognition and formatting can still be wrong: review numbers, negations, identifiers, and commands before using the result. Choose verbatim mode when minimal post-processing is preferred.

For configuration, optional local integrations, and architecture, see the [README](README.md). For release evidence and remaining limitations, see [Evaluating FlowPilot](TRUST.md).
