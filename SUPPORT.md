# Getting help with FlowPilot

FlowPilot is maintained through this GitHub repository. Support is best effort; there is no guaranteed response time. For ordinary bugs, [open an issue](https://github.com/abishekvr0910/flowpilot/issues/new/choose). Security reports follow the private process in [SECURITY.md](SECURITY.md).

## Text did not appear

Check the target field first. If the text is already present, do not retry. If it is absent, place the cursor where you want it and use **Copy Last Dictation** from the tray, then paste manually. `Alt+Shift+Z` requests paste recovery in current source. Its behavior depends on the target application. A manual recovery can duplicate text if the original paste arrived late.

The recovery buffer holds the most recent dictation in memory. It can be replaced by a later dictation and does not survive app exit. For an elevated editor or terminal, try manual copy/paste before changing how FlowPilot is launched. Normal dictation does not require administrator privileges.

## Microphone or model setup failed

Confirm the intended Windows recording device and desktop microphone permission. VB-Cable is only needed for controlled audio tests; normal users should select their physical microphone. See [model setup](QUICKSTART.md#running-current-source) if local model weights are missing. The current runtime does not silently download missing weights.

## What to include in a bug report

- Release tag or source commit, and whether the worktree was modified. For an executable, include its SHA-256 if possible.
- Windows version, CPU/RAM, microphone type, Whisper model and language.
- Target application/version and whether it ran as administrator.
- Steps using a made-up test phrase, expected result, actual result, and whether manual recovery worked or duplicated text.
- Relevant error messages, with personal information removed. If tested, distinguish first-attempt insertion, recovery, and a safe refusal on a non-interactive desktop.

Logs can contain window titles, local paths, and exception details. Inspect them before attaching. Do not upload your `.flowpilot` directory, real recordings, transcripts, clipboard contents, credentials, or private documents. The diagnostic collector runs local checks; review any resulting report before sharing it.

## Downloads and Windows warnings

Use the repository's [GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases), compare the archive hash against the matching release manifest, and inspect the executable's signature. A matching checksum is not a malware assessment or a publisher certificate. If Windows blocks an unfamiliar build, stop and verify its origin; support instructions do not require disabling Defender or SmartScreen.

See [Evaluating FlowPilot](TRUST.md) for evidence, release boundaries, and remaining work.
