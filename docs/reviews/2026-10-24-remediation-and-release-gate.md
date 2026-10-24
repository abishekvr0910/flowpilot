# FlowPilot remediation and release gate, 24 October 2026

This record follows the earlier [adversarial review](2026-10-24-master-verification.md). It describes the working source on top of `6555e3d` and a staged development binary. A tagged release and public download require their own exact commit, archive, hosted CI result, and pilot decision.

## Verified repairs

| Area | Repair | Evidence |
| --- | --- | --- |
| Microphone identity | Missing, unavailable, invalid, and ambiguous selections resolve to `-9999`, never PortAudio default. Stored name, host API, and channel count govern both pickers and capture. Config migration saves after closing the read handle. Deferred changes do not reopen a stream after `keep_stream_alive=False`. | `tests/test_audio_devices.py`: 20 tests; `tests/test_user_facing_fixes.py`; 37 local adversarial probes in `scratch/codex_review_20261024.py` |
| Production capture | A failed microphone open raises to the user in a normal session. Synthetic capture is limited to an explicit headless or CI run. | Direct production mode stream failure test in `tests/test_audio_devices.py`; strict interactive suite |
| Delivery observer | Requires a readable pre-dispatch baseline, measures the actual insertion delta, rejects unrelated changes and duplicates, resets timing when text disappears, and bounds slow reader calls. This is isolated benchmark tooling and has no live competitor target adapter yet. | `tests/test_delivery_observer.py`: 17 tests; adversarial probes |
| Workspace scrolling | One application filter prevents wheel changes to closed menus, sliders, and tab headers while allowing page scroll. Repeated wheel movement at the bottom stays stable; mouse and keyboard navigation still work. | `tests/test_workspace_refresh.py` in the strict suite |
| Test honesty | Offscreen Qt has no native UI Automation document. Its physical read now skips in that environment. The Notepad harness also honors explicit headless and offscreen flags. The physical tests still run on the interactive desktop. | First headless run found two focus failures; corrected harness followed by strict interactive gate below |
| Hosted package parity | CI now downloads both `base` and `small` model weights before PyInstaller, matching the local candidate model set. | `.github/workflows/ci.yml`; hosted CI for this revision still pending |

## Exact local checks

| Check | Observed result |
| --- | --- |
| `python -X utf8 tests/run_all_tests.py --require-all` on the interactive Windows desktop | **56 passed, 0 skipped, 0 failed**, 119.81 seconds. Includes physical audio, Notepad, cross-app editor insertion, UI Automation, 18 scenarios, and binary smoke. Log: ignored local `scratch/interactive_gate_20261024.log`. |
| Staged binary smoke with `FLOWPILOT_TEST_EXE` set to `dist/RC4-staging-20261024/FlowPilot/FlowPilot.exe` | Passed named mutex, duplicate process, bundled assets, and clean exit. |
| Staged binary `--self-test` with offline flags and an empty isolated Hugging Face cache | Exit 0; bundled `base` model recognized `FlowPilot offline dictation verified.`; isolated cache remained empty. |
| `npm test` | Passed local REST and WebSocket integration tests. |
| `git diff --check` and Python compile | Passed. |
| Staged executable | 24,894,766 bytes; SHA-256 `09B2F25A066E0463629B5C7DE396534F24CDF97388CCCFF91D957FE9F73D315C`; Authenticode `NotSigned`. |

The first headless full run was **not** a pass: it started before the Notepad headless guard was fixed and reported 53 passed, 1 skipped, 2 failed. The later strict interactive run is the complete passing result. This chronology matters when reading old logs. The staged executable was built before the final test-only guard and CI workflow edits, with no application code changed after its build. It remains a development candidate until a fixed source identity and final archive are recorded.

## Open release decisions

1. Build and archive from a fixed committed source revision. Run smoke, offline self-test, ZIP CRC, embedded executable hash match, and hosted CI on that revision. Do not reuse RC3 hashes.
2. Validate physical disconnect/reconnect and default microphone changes on the exact candidate. Unit tests use mock device inventories; ordinary audio capture passed, but it does not cover unplugging the selected device.
3. Complete remaining companion visibility rows in scope 0001 and the consented real speaker and real application pilot. The current tests do not establish 99.9 percent insertion reliability or superiority over Wispr Flow.
4. Review signing, notices, privacy controls, optional API boundaries, clean and upgraded profiles, and final release claims using the [release guide](../release/flowpilot_build_and_release.md). The executable is unsigned.

**Decision:** the source and staged build passed the local strict gate. Public general release is still held pending the exact candidate CI, remaining hardware and pilot checks. A prerelease for consented testers can be considered with the unsigned status and limitations stated plainly.
