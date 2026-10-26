# FlowPilot audit summary

Updated 2026-10-26 for the RC8 pilot candidate. This page is a map to current evidence, not a claim that every feature or target app is verified.

## What was checked

- **Automated test suites**: The 59-suite audit runner reported **59 passed, 0 skipped, 0 failed** in a strict local interactive session. In headless CI ([Run 40348691736](https://github.com/abishekvr0910/flowpilot/actions/runs/40348691736)), it reported **50 passed, 9 honest hardware/desktop skips, 0 failed**. See the [RC8 manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) for exact archive, digest, and test accounting.
- **Packaged artifact integrity**: The candidate archive (`FlowPilot-v3.1.0-RC8-win64.zip`, SHA-256 `2DFB83BCC98068389E6962FCC7A0A25131C90F7D546B8CD3ABDBC6E54A43F69F`) passed 1,297-member ZIP CRC verification. The embedded executable (`FlowPilot.exe`, SHA-256 `67C93341837DBD2D317633DC3B2AAA15136A76BB0C887D019F0EC6AFD23FF156`) matches the smoke-tested binary.
- **Packaged smoke & offline self-test**: The extracted executable loaded bundled `base` model weights, transcribed a SAPI fixture, cleanly exited 0, and confirmed an empty isolated Hugging Face model cache without network egress.
- **Physical hardware & terminal delivery**: Physical microphone disconnect, dynamic reconnect, and device renumbering checks passed on host candidate hardware without silent fallback to unexpected endpoints. Windows Terminal console delivery passed 10/10 verified insertions via dual-mode typing.
- **Full stack integration**: `npm test` verified loopback REST and WebSocket lifecycle on `127.0.0.1`.

## What remains open

- **Consented pilot field evaluation**: Controlled real-world deployment across Microsoft Word, Slack, Notion, VS Code, and Chrome to measure verified paste rates, clipboard retention, and recovery hotkey invocations under user typing load.
- **Acoustic speech reality in Indic languages**: Bundled models showed high error rates on real human speech in Hindi, Tamil, and Malayalam ([diagnostic report](../evaluation/EN_HI_TA_ML_REAL_VOICE_BASELINE_2026-10-26.md)). These languages remain strictly experimental. Local SLM text repair (Spec 0004) operates post-ASR and cannot substitute for acoustic speech training.
- **Paired competitor trial**: Paired benchmark versus Wispr Flow measuring time-to-correct, settled delivery latency, and memory footprints under identical audio fixtures.
- **Authenticode code signing**: RC8 remains an unsigned pilot prerelease (`NotSigned`); production release requires an EV Authenticode certificate.
