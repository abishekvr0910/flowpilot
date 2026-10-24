# FlowPilot release artifact manifest

Updated 2026-10-24. A locally verified candidate is not a published general release.

## Validation candidate: v3.1.0-RC4, Windows x64

The application source was fixed at `2710397` before the local PyInstaller build. Follow-up commits through `19c3e57` changed only tests; `git diff 2710397..19c3e57 -- desktop_app.py engine ui flowpilot.spec requirements.txt pyproject.toml` is empty. The exact executable below passed the packaged smoke and offline self-test. It was the `FLOWPILOT_TEST_EXE` used by the final local strict runner. Hosted CI [run 40114775331](https://github.com/abishekvr0910/flowpilot/actions/runs/40114775331) passed on `19c3e57` after test fixtures were given explicit virtual audio in microphone-free CI. Earlier failed CI runs remain historical evidence.

| Item | Measured value |
|---|---|
| Archive | `dist/FlowPilot-v3.1.0-RC4-win64.zip` |
| Archive size | 772,971,321 bytes |
| Archive SHA-256 | `1EDEF319984F222B611F54A2B81CAA5C758BC1379662A93F5E344949ED51864E` |
| Unpacked application | `dist/RC4-2710397/FlowPilot/`, 1,111,654,982 bytes across 1,203 files |
| Executable | `FlowPilot.exe`, 24,894,766 bytes |
| Executable SHA-256 | `3059851502943858457C76B345C154E025241D9D0D11E95410319285928D10F0` |
| Bundled assets | Faster-Whisper base and small; Silero VAD ONNX encoder and decoder |
| Signing | `NotSigned` by Windows Authenticode inspection |
| Local strict gate | 56 passed, 0 skipped, 0 failed in 123.07 seconds against this executable |
| Hosted Windows CI | [Run 40114775331](https://github.com/abishekvr0910/flowpilot/actions/runs/40114775331) on `19c3e57`: 47 passed, 9 honest hardware/desktop skips, 0 failed; Node integration and packaged smoke passed |
| Node integration | `npm test` passed local REST and WebSocket lifecycle checks |
| Packaged smoke | Named mutex, duplicate launch, bundled asset presence, isolated profile and process termination passed |
| Offline self-test | Bundled base model recognized the SAPI fixture with offline flags and an empty Hugging Face cache; exit 0, cache remained empty |
| Archive integrity | All 1,207 members passed CRC; embedded executable SHA-256 matches the disk file |

The ZIP includes `LICENSE`, `THIRD_PARTY_LICENSES.md`, `PRIVACY.md`, and `README.md` at its root. A member-name scan found no `wispr_renderer`, `wispr_bridge`, `flow.sqlite`, `access_token`, `.env`, or `private/` path. These checks do not constitute a complete rights audit or whole-process network capture. The local build used Python 3.11.15, PyInstaller 6.22.3 and PySide6 6.12.0; hosted CI uses Python 3.12 and builds independently.

RC4 remains a pilot prerelease candidate. Physical microphone disconnect and reconnect behavior, real-speaker language quality, paired competitor trials, publisher signing, and broader pilot reliability remain open. The prior RC3 and RC2 hashes below are historical and must not be applied to this archive.

## Historical local candidate: v3.1.0-RC3, Windows x64

The RC3 candidate used the exact executable that passed the five live
companion checks after source repair commit `681363e`. It occupied the
unpacked app at `dist/FlowPilot/` at the time. The RC2 archive below is
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
| Hosted CI gate | [Run 40005496898](https://github.com/abishekvr0910/flowpilot/actions/runs/40005496898) passed on Windows for commit `2d3d5c4`: 47 passed, 7 headless skips, 0 failed; Node integration and binary smoke passed |
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

The hosted runner cannot perform physical keyboard and window checks; those
seven skips are not passes. The local `--require-all` run supplies that
separate evidence. A public general release remains held for real user
pilot feedback, including paste reliability and real speaker language
accuracy.

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
