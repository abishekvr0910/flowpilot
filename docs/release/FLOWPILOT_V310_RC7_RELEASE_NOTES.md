# FlowPilot v3.1.0 RC7, Windows pilot prerelease

RC7 replaces the withdrawn RC6 candidate. It contains the reviewed local dictation, recovery, model setup, and Windows input fixes described in the [artifact manifest](RELEASE_ARTIFACT_MANIFEST.md). Speech recognition and text processing run on your device. An optional model download uses HTTPS only when requested in Setup or Settings.

## RC7 corrections

- Microphone failures now stop recording in CI as they do for users. An empty capture never becomes a fabricated silent WAV.
- The REST and WebSocket test supplies a declared virtual input frame and waits for the first audio level event, avoiding a capture watchdog race.
- The pre-roll regression test uses a declared virtual stream, so it tests buffer transfer without depending on hosted runner hardware.

## Verification

The local 59 suite audit with CI environment flags reported **54 passed, 5 skipped, 0 failed**. The five skips require a physical Windows desktop. The newly built executable passed named mutex and bundled asset smoke checks. Its offline self test transcribed a SAPI fixture with an empty isolated model cache. The ZIP passed CRC, embedded executable hash comparison, and required license notice checks. Hosted CI results for the final source are required before pilot publication.

The executable is unsigned. Windows may show a publisher warning. Real speaker accuracy, physical microphone unplug behavior, and paste reliability across a broad set of applications remain pilot measurements. This candidate is not a certified or general release.

Close an older FlowPilot instance before extracting and launching the full archive.
