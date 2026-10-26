# FlowPilot v3.1.0 RC8, Windows pilot prerelease

RC8 replaces RC7 for pilot testing. [Hosted Windows CI](https://github.com/abishekvr0910/flowpilot/actions/runs/40348691736) passed with 50 suites passed, 9 honest hardware or desktop skips, and 0 failures. It keeps offline dictation and local text processing. The optional model setup download is user initiated and uses HTTPS; normal speech recognition uses bundled local weights.

## Changes

- Windows Terminal and classic console targets now use focus guarded Unicode typing. The prior `Shift+Insert` path accepted key events without delivering text on the tested Windows Terminal host. Terminal text with newlines is held for manual recovery to avoid command submission.
- Local Faster-Whisper decoding uses one deterministic temperature and a duration-based output token cap. On the same five Malayalam Common Voice clips, small-model mean decode time fell from 70.88 to 2.81 seconds. Recognition on those clips remained unusable.
- Hindi joins Tamil and Malayalam as an **experimental** language choice. The setup and settings screens warn users to test their own speech. A small [real speech diagnostic](../evaluation/EN_HI_TA_ML_REAL_VOICE_BASELINE_2026-10-26.md) documents the measured errors and sample limits.
- The corpus acquisition tool can select English, Hindi, Tamil, and Malayalam from a pinned Common Voice 17.0 mirror revision. Audio remains outside Git; only metadata and the bounded evaluation are public.

## Verification and limits

The exact locally built bundle passed 59/59 strict interactive suites, its packaged smoke test, `npm test`, and an offline self-test after extracting the RC8 ZIP. Ten repeated cross-app runs each confirmed final text in Notepad, Windows Terminal Command Prompt, and a Qt editor. Those results do not establish a first-attempt reliability percentage across other applications or machines.

The executable is **unsigned**. Windows may show a SmartScreen warning. This is a pilot prerelease, not a general release. Hindi, Tamil, and Malayalam must not be presented as production quality. See the [artifact manifest](RELEASE_ARTIFACT_MANIFEST.md) for the exact archive hash and source identity.
