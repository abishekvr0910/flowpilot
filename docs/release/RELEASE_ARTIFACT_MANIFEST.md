# FlowPilot release artifact manifest

Updated 2026-10-26. A locally verified candidate is not a published general release.

## Release candidate: v3.1.0-RC5, Windows x64

The application source was integrated and committed at `4b7bbca` after peer review of `feature/reviewed-v310`. RC5 includes generation counters for session-isolated dictation recovery, dashboard de-duplication, truthful model detection and guidance in settings/wizard, full model license notices (OpenAI Whisper MIT and Silero VAD MIT), and fail-closed Authenticode packaging.

| Item | Measured value |
|---|---|
| Archive | `dist/FlowPilot-v3.1.0-RC5-win64.zip` |
| Archive size | 770,701,235 bytes |
| Archive SHA-256 | `8B57F3C74EB05874AE2C5839767567A33DBF2613E9873ECB4E6950AD6B276713` |
| Archive checksum file | `dist/FlowPilot-v3.1.0-RC5-win64.zip.sha256` |
| Embedded executable | `FlowPilot.exe`, 24,908,667 bytes |
| Embedded SHA-256 | `AEB7F817B7E2482A18EE52123C3F1F24327D9779F9D79A2139E8FDAC32C5145C` |
| Bundled assets | Faster-Whisper base and small models; Silero VAD v5 ONNX assets |
| License notices | 93 license notices under `licenses/` included |
| Signing | `NotSigned` developer candidate (Authenticode signing pending corporate certificate) |
| Local automated audit | **53 passed, 5 skipped (hardware/physical desktop), 0 failed** in 176.34 s across all 58 audit suites (`python -X utf8 tests/run_all_tests.py`) |
| Standalone smoke | Passed on packaged candidate (`tests/test_standalone_binary_smoke.py`) |
| Dictation recovery tests | Passed (`tests/test_recovery_feedback.py`) |
| Release integrity guards | Passed (`tests/test_release_integrity_fixes.py`) |

## Validation candidate: v3.1.0-RC4, Windows x64

The application source was fixed at `2710397`. The RC4 package was rebuilt from committed source at `2baa2f9`, which excludes unused Qt Virtual Keyboard and PDF modules and adds an archive notice set. The executable below passed packaged smoke and offline self-test. Hosted CI [run 40116350311](https://github.com/abishekvr0910/flowpilot/actions/runs/40116350311) passed on `2baa2f9`. An initial strict run against the exact rebuilt executable passed 55 suites and failed one physical Notepad focus suite. After a test-only change at `b4fe12c` removed synthetic microphone fallback and added focus diagnostics, the targeted 18-scenario suite passed; a full interactive rerun against the **same executable bytes** passed 56 suites with no skips or failures. The earlier failure remains recorded in the local `scratch/rc4-final-strict.log`. This repeat establishes one clean run, not a reliability rate.

| Item | Measured value |
|---|---|
| Archive | `dist/FlowPilot-v3.1.0-RC4-win64.zip` (byte-for-byte copy of the verified archive under `dist/RC4-final-2baa2f9/`) |
| Archive size | 770,634,494 bytes |
| Archive SHA-256 | `55918EB873499001A34E85F6F636DB701D4F5937B340C3A051BAC332DB8F8C88` |
| Unpacked application | `dist/RC4-final-2baa2f9/FlowPilot/`, 1,106,528,102 bytes across 1,199 files |
| Executable | `FlowPilot.exe`, 24,894,766 bytes |
| Executable SHA-256 | `4655DB97D46AC7DA795AF4DDF2228901CB816CF8E8DC829CC1D0BD4CE3EED225` |
| Bundled assets | Faster-Whisper base and small; Silero VAD ONNX encoder and decoder |
| Signing | `NotSigned` by Windows Authenticode inspection |
| Local strict gate | Initial final-executable run: 55 passed, 0 skipped, 1 failed (Notepad focus unavailable). Exact-executable rerun: **56 passed, 0 skipped, 0 failed in 133.93 s** with `--require-all`; targeted 18-scenario retry also passed. |
| Hosted Windows CI | [Run 40116350311](https://github.com/abishekvr0910/flowpilot/actions/runs/40116350311) on packaging commit `2baa2f9` and [run 40116943044](https://github.com/abishekvr0910/flowpilot/actions/runs/40116943044) on test-only commit `b4fe12c`: each 47 passed, 9 honest hardware/desktop skips, 0 failed; Node integration and packaged smoke passed |
| Node integration | `npm test` passed local REST and WebSocket lifecycle checks |
| Packaged smoke | Named mutex, duplicate launch, bundled asset presence, isolated profile and process termination passed |
| Offline self-test | Bundled base model recognized the SAPI fixture with offline flags and an empty Hugging Face cache; exit 0, cache remained empty |
| Archive integrity | All 1,296 members passed CRC; embedded executable SHA-256 matches the disk file |

The ZIP includes `LICENSE`, `THIRD_PARTY_LICENSES.md`, `PRIVACY.md`, `README.md`, and 93 files under `licenses/` at its root. The unused Qt Virtual Keyboard and Qt PDF binaries are absent. A member-name scan found no `wispr_renderer`, `wispr_bridge`, `flow.sqlite`, `access_token`, `.env`, or `private/` path. These checks do not constitute a complete rights audit or whole-process network capture. The local build used Python 3.11.15, PyInstaller 6.22.3 and PySide6 6.12.0; hosted CI uses Python 3.12 and builds independently. The verified executable is inside this ZIP and under `dist/RC4-final-2baa2f9/FlowPilot/`; an older `dist/FlowPilot/` tree may remain while its process is running and is not the RC4 test target.

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
