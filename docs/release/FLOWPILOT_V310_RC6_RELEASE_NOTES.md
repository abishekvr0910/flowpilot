# FlowPilot v3.1.0 RC6, Windows pilot prerelease

RC6 is for Windows pilot testing. Speech recognition and text processing run locally. The archive includes base and small Whisper models. A model can also be downloaded on demand only after the user requests it in Setup or Settings.

## Changes from RC4

- Recovery feedback and model readiness wording from the reviewed RC5 source are included.
- Direct Unicode fallback now uses the correct 64 bit Windows input layout and supports characters outside the basic multilingual plane. Multiline fallback into a terminal refuses to type Enter automatically.
- Model downloads use unique temporary files and atomic replacement. Closing Setup or Settings cancels the download without destroying its running thread.
- Requested Authenticode signing fails the package step if the certificate is invalid or signature verification fails.
- Public source documentation no longer includes reports derived from a local competitor user database or the generated audit pages with stale measurements.

## Verification and limits

The local 59 suite audit reported **54 passed, 5 skipped, 0 failed** in a headless session. Node integration, packaged smoke, offline packaged self test with an empty model cache, ZIP CRC, and embedded executable hash comparison passed. The five skipped suites require a physical Windows desktop. Real speaker accuracy, broad target app paste rates, and physical microphone unplug behavior remain pilot checks. The executable is unsigned, so Windows may warn before first run. This candidate is not a certified or general release.

The exact SHA-256 values and byte sizes are in the [release artifact manifest](RELEASE_ARTIFACT_MANIFEST.md). Close an older FlowPilot instance before extracting and launching this archive.
