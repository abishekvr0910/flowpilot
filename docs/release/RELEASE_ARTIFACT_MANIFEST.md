# FlowPilot release artifact manifest

Updated 2026-10-22. A locally verified candidate is not a published release.

## Local candidate: v3.1.0-RC2, Windows x64

RC2 was built from local `master` at `06196fa` **plus uncommitted source changes** documented in the [release reassessment](../reviews/2026-10-22-release-reassessment.md). It is not yet a reproducible commit-based release. The older `FlowPilot-v3.1.0-win64.zip` is superseded for local testing; its hashes must not be applied to RC2.

| Item | Measured value |
|---|---|
| Archive | `dist/FlowPilot-v3.1.0-RC2-win64.zip` |
| Archive size | 772,927,221 bytes |
| Archive SHA-256 | `682A7FFC39516FA1C2733D4275E8383D1B5603E46DBA859FC85F7DBAB1B0C51E` |
| Unpacked application | `dist/FlowPilot/` (1,111,616,314 bytes across files) |
| Executable | `dist/FlowPilot/FlowPilot.exe` (24,856,098 bytes) |
| Executable SHA-256 | `FD3E2D7825E6AEDBC745215FF8E64EBD8F561F4E00B01B5FB408AE597304CAC0` |
| Signing | `NotSigned` by Windows Authenticode inspection |
| Bundled models | Faster-Whisper `base` and `small`, plus Silero VAD v5 ONNX assets |
| Source gate | **53 passed, 0 skipped, 0 failed** in 162.12 seconds using `python -X utf8 tests/run_all_tests.py --require-all` on the available interactive desktop |
| Standalone gate | Smoke passed on final `dist/FlowPilot/`: named mutex, duplicate exit, bundled assets, clean termination |
| Offline self-test | Staged executable loaded its bundled base model and transcribed a SAPI fixture in 1.57 seconds with offline flags and an isolated empty cache; exit code 0, cache remained empty |

Archive CRC verification (`python -m zipfile -t`) passed. Its 1,232 members contain one `FlowPilot/FlowPilot.exe` whose SHA-256 matches the unpacked executable. Filename inspection found no `wispr_renderer`, `wispr_bridge`, `flow.sqlite`, or `__pycache__` entry. This is a filename scan, not proof that every dependency or byte has been rights-cleared. The source suite includes a socket-level egress test; no whole-system packet capture was run against this exact binary.

The 461 MiB `small` model and 138.5 MiB `base` model account for most of the unpacked size. Both remain bundled for offline multilingual use. RC2 is unsigned, so Windows SmartScreen may warn. Code signing and broader customer-machine compatibility testing remain before general release.

Local `master` was 26 commits ahead of `origin/master`, and the local `v3.1.0-release` tag was absent from the remote when checked on 2026-10-22. Do not describe RC2 as published or attach the ZIP to a GitHub release until the source changes are committed, remote CI runs on that exact commit, and release sign-off is complete.

### Independent integrity check

```powershell
Get-FileHash -Algorithm SHA256 .\dist\FlowPilot-v3.1.0-RC2-win64.zip
# 682A7FFC39516FA1C2733D4275E8383D1B5603E46DBA859FC85F7DBAB1B0C51E
Get-FileHash -Algorithm SHA256 .\dist\FlowPilot\FlowPilot.exe
# FD3E2D7825E6AEDBC745215FF8E64EBD8F561F4E00B01B5FB408AE597304CAC0
python -m zipfile -t .\dist\FlowPilot-v3.1.0-RC2-win64.zip
```

## Historical published release: v3.0.2

The previous published release is [`v3.0.2-release`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release), source commit `b9bd76396b2883fa2e87e8b131d231dc39c34515`. Its published asset was `FlowPilot-v3.0.2-win64.zip` (252,311,634 bytes; SHA-256 `985e031c7af2617e4c03138d1a00472607ff9f9e1d2cff636827f26077f63f74`). These historical values do not validate RC2.
