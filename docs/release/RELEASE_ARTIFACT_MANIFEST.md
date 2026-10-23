# FlowPilot release artifact manifest

Updated 2026-10-23. A locally verified candidate is not a published general release.

## Local candidate: v3.1.0-RC3, Windows x64

The new candidate uses the exact executable that passed the five live
companion checks after source repair commit `681363e`. It replaces the
unpacked app at `dist/FlowPilot/`. The RC2 archive below is retained as
historical evidence and must not be described with RC3 hashes.

| Item | Measured value |
|---|---|
| Archive | `dist/FlowPilot-v3.1.0-RC3-win64.zip` |
| Archive size | 772,950,120 bytes |
| Archive SHA-256 | `FEB13D469622B53DFD4D3B54BC8ED7C90A47DADA4B32BC1EA7432992A89C340C` |
| Unpacked application | `dist/FlowPilot/`, 1,111,645,305 bytes across 1,203 files |
| Executable | `dist/FlowPilot/FlowPilot.exe`, 24,885,089 bytes |
| Executable SHA-256 | `D17FEC1C94918520CAF51B3F250897875671B6BB0B401429315AA08999ABF52E` |
| Bundled assets | Faster-Whisper base and small models; Silero VAD ONNX assets |
| Signing | `NotSigned` developer candidate |
| Local strict gate | 54 passed, 0 skipped, 0 failed in 175.07 s with `--require-all` and this executable |
| Standalone smoke | Passed on the promoted `dist/FlowPilot/` executable, including named mutex, duplicate launch, bundled assets and clean exit |
| Offline self test | Passed on promoted executable with empty isolated Hugging Face cache and offline flags; zero cache files created |

The archive passed a full CRC read of its 1,203 members. Its embedded
`FlowPilot.exe` has the same SHA-256 as the unpacked executable and the one
used for live testing. A filename scan found no `wispr_renderer`,
`wispr_bridge`, `flow.sqlite`, `access_token`, `.env`, or `private` member.
That is a filename scan, not a byte level rights audit or packet capture.
The [live validation note](../testing/MEDIA_AUDIO_PRESENCE_VALIDATION_2026-10-23.md)
records the media, F11, PowerPoint, hidden F9, and mixed DPI evidence,
including failed attempts that were not counted.

Hosted Windows CI for this candidate must be checked before pushing the RC3
tag. A public general release remains held for real user pilot feedback,
including paste reliability and real speaker language accuracy.

The later [remediation verification report](../reviews/2026-10-23-remediation-verification.md) records a separate unsigned development executable built from uncommitted repairs. It does not replace this RC2 archive or its source identity, hashes, hosted CI result, or public release status.

## Local candidate: v3.1.0-RC2, Windows x64

RC2 was rebuilt directly from committed local `master` at [`f398ba6`](https://github.com/abishekvr0910/flowpilot/tree/f398ba6) (tagged `v3.1.0-RC2`). All in-flight fixes for atomic config serialization, count-verified injection, spoken tab commands, meeting decision parsing, hosted CI model provisioning, and offline tokenizer lookup are formally committed and validated.

| Item | Measured value |
|---|---|
| Archive | `dist/FlowPilot-v3.1.0-RC2-win64.zip` |
| Archive size | 772,922,171 bytes |
| Archive SHA-256 | `7BC756F4910D13D2E921FC1B20A784FB25539D02664F474C8BBBCBCB08C66D89` |
| Unpacked application | `dist/FlowPilot/` (1,111,617,128 bytes across 1,203 files) |
| Executable | `dist/FlowPilot/FlowPilot.exe` (24,856,912 bytes) |
| Executable SHA-256 | `42651DB5FE386A323D3C05CA52D1B3D7AB461A0592AA927BA906B7E11F52103F` |
| Signing | `NotSigned` by Windows Authenticode inspection |
| Bundled models | Faster-Whisper `base` and `small`, plus Silero VAD v5 ONNX assets |
| Source gate | **49 passed, 4 skipped, 0 failed** in 106.94 seconds using `python -X utf8 tests/run_all_tests.py` on local desktop (skips are headless injection fixtures) |
| Hosted CI gate | **46 passed, 7 skipped, 0 failed**, plus full-stack Node.js integration and standalone binary smoke test passed on GitHub Actions ([Run 39809935723](https://github.com/abishekvr0910/flowpilot/actions/runs/39809935723), 5m 52s) |
| Standalone gate | Smoke passed on final `dist/FlowPilot/`: named mutex, duplicate exit, bundled assets, clean termination |
| Offline self-test | Staged executable loaded its bundled base model and transcribed a SAPI fixture in 12.52 seconds with offline flags and an isolated empty cache; exit code 0, cache remained empty |

Archive CRC verification (`python -m zipfile -t`) passed. Its 1,203 members contain one `FlowPilot/FlowPilot.exe` whose SHA-256 matches the unpacked executable. Filename inspection found no `wispr_renderer`, `wispr_bridge`, `flow.sqlite`, or `__pycache__` entry. This is a filename scan, not proof that every dependency or byte has been rights-cleared. The source suite includes a socket-level egress test; no whole-system packet capture was run against this exact binary.

The 461 MiB `small` model and 138.5 MiB `base` model account for most of the unpacked size. Both remain bundled for offline multilingual use. RC2 is unsigned, so Windows SmartScreen may warn. Code signing and broader customer-machine compatibility testing remain before general release.

Public distribution remains held pending human pilot testing (measuring paste reliability and real-speaker English, Hindi, Tamil, and Malayalam transcription).

### Independent integrity check

```powershell
Get-FileHash -Algorithm SHA256 .\dist\FlowPilot-v3.1.0-RC2-win64.zip
# 7BC756F4910D13D2E921FC1B20A784FB25539D02664F474C8BBBCBCB08C66D89
Get-FileHash -Algorithm SHA256 .\dist\FlowPilot\FlowPilot.exe
# 42651DB5FE386A323D3C05CA52D1B3D7AB461A0592AA927BA906B7E11F52103F
python -m zipfile -t .\dist\FlowPilot-v3.1.0-RC2-win64.zip
```

## Historical published release: v3.0.2

The previous published release is [`v3.0.2-release`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release), source commit `b9bd76396b2883fa2e87e8b131d231dc39c34515`. Its published asset was `FlowPilot-v3.0.2-win64.zip` (252,311,634 bytes; SHA-256 `985e031c7af2617e4c03138d1a00472607ff9f9e1d2cff636827f26077f63f74`). These historical values do not validate RC2.
