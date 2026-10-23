# FlowPilot remediation verification

**Date:** 2026-10-23  
**Baseline:** local `master` at `367185c3fc6de06ef50af1d18fab65ed1d2aeb1f`  
**State:** source changes and a separate development executable; no commit, push, tag, or public release

## Decision

The four work packages in the [handoff directive](../design/GEMINI_SCOPE_AND_RELEASE_REMEDIATION.md) now have a source implementation and reviewable evidence. The external transform refusal is complete in source and in the isolated executable. Release promotion remains open because this is a dirty-tree development build, the current changes have no hosted CI run or final archive, and real-speaker, visible-delivery, sustained runtime, and broader upgrade evidence are still missing.

The old v3.1.0-RC2 ZIP in `dist/` and its [manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) were preserved. Its hashes and CI results belong to the old bytes, not this repair. Local `master` is 31 commits ahead of `origin/master`; no remote state was changed here.

## What changed

| Work package | Implemented result | Evidence and remaining limit |
|---|---|---|
| External transform safety | `TransformsEngine.replace_selection()` and `revert_last_transform()` refuse external mutation with `InjectionResult`, retain recovery text in memory, and never dispatch keys or write the clipboard. A caller object labelled `verified` or `scratchpad` cannot authorize an edit. The Qt view keeps preview and Copy Output; external Replace and Revert stay disabled. The scratchpad uses its separate guarded `VoiceEditor` transaction path. | The new regressions first reproduced a forged-label dispatch and an enabled Replace button, then passed after the repair. Standalone transform tests passed 20/20. External editing in arbitrary apps is still a future feature. |
| Direct Unicode focus guard | The direct Unicode helper checks the verified foreground both at entry and immediately before `SendInput`. It aborts if focus is missing or changes while preparing the input array. | Mocked Win32 dispatch tests assert zero key events and retained recovery text. Ordinary dictation paths still require their own physical reliability sampling. |
| Production timing labels | `FlowOrchestrator` now records stop action to injection result and acoustic end to injection result. Its legacy visible-text field is explicitly `null` with `visible_delivery_status: not_measured`; the console output and opt-in telemetry use the same boundary. | The timing contract regression checks the numeric boundary and absence of an invented acoustic-to-visible measurement. An observed document event still needs a separate physical measurement. |
| Scope and pilot instructions | Release scope now requires a strict zero-skip local gate, exact-commit CI, physical app tests, final-byte artifact checks, profile preservation, signing checks, rollback limits, and measured performance. The quickstart describes the fresh `save_history_text: false` default, preserves an existing user's choice, and separates history from meetings, scratchpad, and clipboard state. | A fresh profile test checks the default without creating a vault. A packaged existing-profile smoke retains F9, Hindi, opt-in history, dictionary, snippet, companion settings, and a prior vault record. This fixture is one supported-shape sample, not a universal migration proof. |
| Runtime evidence | The existing real-voice evaluator now records cold and warm processing separately, host and model identity, process CPU time, sampled process-tree RSS, sample counts, and model weight fingerprints. Its report explicitly leaves visible delivery and other unmeasured phases unknown. | [Protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md) and [raw source smoke evidence](../evaluation/RUNTIME_PROCESSING_SMOKE_2026-10-22.json) are available. Real speaker, packaged desktop, low-resource machine, and long-session measurements remain open. |

The previously uncommitted worktree was retained and improved. In particular, a partial earlier guard that accepted an arbitrary `target_type` label was removed after a controlled no-input probe demonstrated the bypass. No real keystrokes were sent in that probe.

## Checks performed

| Check | Result | Boundary |
|---|---|---|
| Strict local runner, `python -B -X utf8 tests/run_all_tests.py --require-all`, with `FLOWPILOT_TEST_EXE` set to the final isolated executable | **53 passed, 0 skipped, 0 failed in 113.79 s; exit 0.** The final run includes the saved-profile and timing-label regressions. | Interactive desktop was available; physical microphone, Notepad, cross-app, and specification suites ran. A green suite is not a 99.9% field reliability measurement. |
| Packaged smoke | Passed against the final isolated executable: bundled model and VAD assets, mutex, duplicate-instance exit, clean owned-process termination. The release-integrity suite also passed against that same executable with an isolated saved profile. | Current development executable, not the old RC2 archive. |
| Clean-cache offline self-test | Passed, exit 0. The final executable loaded its bundled `base` model and transcribed the SAPI fixture; isolated Hugging Face cache remained empty. Recognition stage reported **11.95 s** in this cold run, with **23.53 s** wall time for the self-test process. | Fresh cache and offline environment flags; no whole-system packet capture. Self-test duration does not equal warm stop-to-visible delivery. |
| Node.js REST/WebSocket integration | Passed with Node v24.15.0 under an isolated temporary profile; exit 0 after the final source change. Static files, REST config, and bidirectional WebSocket lifecycle succeeded. | Source API integration, not a packaged desktop network capture. |
| Focused tests | The transform suite passed 20/20, evaluation metrics passed 7/7, and session lifecycle passed 5/5 including the new timing-boundary regression. | The final strict runner is the authoritative aggregate. |
| Diff hygiene | `git diff --check` passed. | Does not validate runtime behavior. |

The final packaged development executable is `scratch/remediation-verification/final-dist/FlowPilot/FlowPilot.exe` (**24,858,907 bytes**, SHA-256 `16BB696F1A41AF95C5299360E7096E452488C451CACF676BC37F6CA8356D843A`, Authenticode `NotSigned`). It was built with PyInstaller 6.22.3 and Python 3.11.15 into an isolated directory. No new ZIP was created. Optional hidden-import warnings for `pycparser.lextab`, `pycparser.yacctab`, and `scipy.special._cdflib` appeared; these are recorded rather than silently discarded. The prior isolated development build remains a historical intermediate and lacks the timing-label correction.

Because the source is not committed, the baseline commit alone cannot reproduce this executable. Current file SHA-256 fingerprints for the touched app and evaluator paths are:

| Path | SHA-256 |
|---|---|
| `engine/transforms_engine.py` | `8613587BE95CFF58713C224388B4E2D9FC22AEB9E05A0C83FC64F4CA5162D1B4` |
| `engine/text_injector.py` | `DB49F5AFF33B728D5E58980EFA3E70132285035117A855B8510649A85B288800` |
| `engine/orchestrator.py` | `078AD472FCDB272C5B3221898C79D8465B75BC98C9F4069BF41A228AD0AA1574` |
| `ui/transforms_view.py` | `FAEF40BB6146744452BF64549FBA3DB5447D6B162B83B8BE4364F46E70F831F3` |
| `benchmarks/run_real_voice_eval.py` | `73DA4606A8C6908EF5B3E5092EC59D33448722B43171AF9288E0AEC744F568E1` |
| `benchmarks/runtime_metrics.py` | `5DCB7918A89A8960093DE29DD5395B4CC862C3A73F98B436FBD22608213E9C1D` |
| `flowpilot.spec` | `780EC3C0021D6E95FAADCCC38F4F2F8F68609A875FB2B539085ACADDBFF33A1F` |

## Measured processing smoke

One non-sensitive English SAPI utterance was repeated eight times per model in separate fresh Python processes on an Intel i5-12500H with 16 logical processors and 16,088 MiB RAM. The local model weights and CPU INT8 path were used. These numbers measure WAV recognition plus formatting from buffer delivery; the cold trial includes lazy model loading. They do not measure capture, VAD stop detection, OS insertion, or visible text.

| Model | Cold processing, n=1 | Warm processing p50 / p95, n=7 | Highest sampled process-tree RSS |
|---|---:|---:|---:|
| `base` | 2.493 s | 0.687 / 0.739 s | 288.13 MiB |
| `small` | 4.357 s | 2.093 / 2.117 s | 475.57 MiB |

All 8/8 items per model evaluated without a missing-audio or failed-item result. Seven warm samples are too few for a stable p95. The `small` result exceeds the historical 1.5 s goal even before visible delivery on this host; it should not be advertised as a sub-1.5 s default here. RSS is sampled, not the OS peak counter. The synthetic perfect reference match in the raw file is a fixture check, not human speech accuracy. This runner did not instrument sockets, so the earlier socket tests and the offline self-test have different verification boundaries.

## Remaining release work

1. Commit and review the repaired source, then build a fixed candidate from that exact identity. Record archive and executable hashes, inspect archive contents, rerun CRC, smoke, offline, and signing checks against the final bytes. Run hosted CI for that commit. The isolated development executable is not a distributable RC.
2. Measure physical stop-to-visible text, first-attempt paste outcomes, safe refusals, recovery, duplicates, clipboard preservation, startup, idle/recording/animation CPU, sampled and peak memory, and 30-minute behavior using the [runtime protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md) on each declared hardware/model class. Declare budgets before evaluating results.
3. Test real English, Hindi, Tamil, and Malayalam speakers with consent and a fixed corpus; keep synthetic fixtures separate. The current report does not support multilingual quality or a competitor superiority claim.
4. Exercise fresh and more than one real upgrade profile on actual pilot machines. Confirm that old vault records and user choices survive, and document downgrade/rollback limits. Obtain publisher signing if required for the distribution decision and retest signed bytes.

Until those checks are complete, the repaired source is a validated engineering change and the v3.1.0 public release remains held.
