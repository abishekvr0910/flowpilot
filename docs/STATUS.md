# FlowPilot current status and agent handoff

Reviewed 2026-11-14. This is the current status entry point. Dated specifications,
pilot receipts, audits, and the October Gemini handoff retain historical context;
their completion labels do not establish the state of newer source or binaries.

## Source, downloads, and verification

| Item | Observed state |
| --- | --- |
| Baseline `master` | `4785a8862eedd3b9ef67fe341baab30925c86b12` (PR #19 merged cleanup, version `3.2.2` before `3.2.3` bump) |
| Post-merge `master` desktop gate | `73 total, 73 passed, 0 skipped, 0 failed` (`342.01s`, `--require-all`, `interactive_desktop: true`) on `4785a88` ([post-merge evidence](reviews/evidence/2026-11-14-postmerge-desktop-gate.json)) |
| Latest published application download | [v3.1.3](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.1.3), published 2026-11-04, unsigned installer and ZIP |
| 3.2.0 / 3.2.1 / 3.2.2 / 3.2.3 artifacts | Local build records in the manifest; no corresponding published GitHub release found on the review date |
| Active candidate branch | `feat/v323-runtime-fixes-and-release` (`3.2.3` source + unsigned Windows x64 candidate); requires PR approval, interactive `Default`-desktop `--require-all` verification, and signing before public release |
| Handy reference | Source at `aca8985190c3ad7f361d8a80cb30f179513ed690` (v0.10.1); [comparison and sources](research/HANDY_SOURCE_REVIEW_2026-11-14.md) |

The [artifact manifest](release/RELEASE_ARTIFACT_MANIFEST.md) preserves older build
hashes. This cleanup does not revalidate those bytes or promote a release.

## Where the product stands

| Area | Implementation and remaining evidence |
| --- | --- |
| Windows dictation | Local capture, VAD, Whisper, formatting, and delivery exist. `device="auto"` now probes `cublas64_12.dll` upfront (`_has_cuda_runtime_libs`) before CTranslate2 load, plus retains lazy CPU fallback. `Win32HotkeyService` wires `WH_KEYBOARD_LL` hook suppression and `0.3s` `WM_HOTKEY` debounce; `WritingIntelligence` adds spoken developer operators with `FactGuard` parity. |
| Text delivery and recovery | Focus checks, status distinctions, terminal protections, and recovery exist. Broad first-attempt reliability across real editors still requires an interactive matrix. |
| External text editing | Transform preview and Copy Output work. External rewrite and undo are disabled because a window handle and a copied selection do not verify the document revision or current range. Scratchpad transactions remain separate. |
| Microphone identity | Persistent identity, missing-device refusal, and `idle_mic_backoff_sec` (`60.0` default) standby WASAPI stream release exist. Dated 3.5mm and USB bus receipts cover specific hardware, not all devices. |
| Languages and models | Whisper and a Tamil ONNX specialist exist, with explicit model provisioning and bounded benchmark reports. Diverse speakers and code switching need further evaluation. |
| Local text repair | Implemented, experimental, disabled by default. Its presence in master supersedes the old claim that it exists only on a sandbox branch. |
| Privacy | Offline model use, history off for new profiles, loopback integrations, and clipboard exclusion requests exist. User scripts, destination apps, clipboard readers, and separately configured model services have separate boundaries. |
| Distribution | Installer and signing tools exist. Published v3.1.3 binaries are unsigned. Tools for signing are not evidence of signed downloads. |
| Companion, meeting, and workspace tools | Implemented features have tests, but broad implementation is not proof of usability or production quality. Core dictation remains the priority. |

## Inconsistencies addressed by this cleanup

- Platform support is explicit: Windows 10/11 x64 releases, experimental macOS/Linux
  source adapters, and no iOS/iPadOS or Android app. Package classifiers advertise
  only the supported Windows target and are checked in CI.
- README defaults now match configuration: manual stop by default, 2.5-second
  optional silence timeout, automatic device selection, and current recovery keys.
- Node metadata agrees with Python, installer, and PE version metadata.
- Test counts come from the runner instead of conflicting copied counts. Strict
  release checks also recognize unittest and pytest skips, including stderr.
- Source version, local build records, and published downloads are distinguished.
- Old scope and handoff documents are labelled historical and point here.
- Unsafe selection rewrite/undo dispatch and its fabricated confirmed status are
  removed. Ctrl+Alt+T consistently opens preview.
- Windows clipboard exclusion uses the documented format names and pywin32 handle
  handling. A request failure is reported by the helper rather than called success.
- CUDA failure during lazy decoding retries the same recording once on CPU;
  subsequent calls reuse CPU, and logs report the actual loaded device.
- Smart Pause now uses pycaw's shipped interfaces for capture endpoints, cancels
  a recording through the complete discard lifecycle, and stops its sampler on shutdown.
- CI checks metadata agreement, documented defaults, suite registration, and links
  in maintained entry documents with `scripts/check_repository_consistency.py`.

## Verification of v3.2.3 candidate and earlier baselines

Prior to `3.2.3` edits, merged `master` commit `4785a8862eedd3b9ef67fe341baab30925c86b12` passed all **73** registered suites with `--require-all` on an interactive desktop (`342.01s`, [post-merge evidence](reviews/evidence/2026-11-14-postmerge-desktop-gate.json)), while the pre-merge PR #19 cleanup baseline is recorded in [2026-11-14-repository-cleanup.json](reviews/evidence/2026-11-14-repository-cleanup.json).

On `feat/v323-runtime-fixes-and-release` (`3.2.3`), `tests/run_all_tests.py` executed **74** registered suites after the clean PyInstaller rebuild and packaging (`166.72s`) with **69 passed, 5 skipped, 0 failed** (`PASSED WITH SKIPPED SUITES`, [2026-11-14-v323-audit.json](reviews/evidence/2026-11-14-v323-audit.json)):

- **Interactive desktop skip blocker:** This command session ran on the isolated Windows desktop `exebox-27ZH55UNHJBDIBCO3FOALXVLJR` (`OpenInputDesktop` resolves to `Default`), so `tests/notepad_harness.py:is_interactive_desktop()` returned `False`. The five live desktop/UIA suites skipped: `Text Injection & Clipboard Safety`, `End-to-End 5-Cycle Notepad Dictation`, `Cross-Application Injection & Focus`, `18-Scenario Full Specification End-to-End`, and `Modern UI Automation & Focus Robustness`.
- **Additional post-build checks passed:** `desktop_app.py --self-test` loaded `CPU (int8, threads=8)` directly without CUDA retry error and transcribed `'FlowPilot offline dictation verified.'` in `0.71s`; `npm test` (`flowpilot@3.2.3`) passed REST/WebSocket integration checks.
- **Signing status:** No `signtool.exe` or Authenticode certificate is present on this build host; `dist/FlowPilot/FlowPilot.exe` (`3.2.3.0`) and `dist/FlowPilot-Setup-v3.2.3.exe` (`3.2.3`) report `NotSigned` (`UNSIGNED_PILOT`).

## Next work, in order

1. Obtain external PR approval on GitHub (`master` branch protection requires 1 approving review) and verify hosted CI passes on the `3.2.3` PR.
2. Run `.\.venv\Scripts\python.exe -X utf8 tests/run_all_tests.py --require-all` from an unlocked interactive Windows `Default` desktop session against the `v3.2.3` build so all 74 suites execute with zero skips (plus manual matrix checks across Notepad, VS Code, Chrome, Word, Slack, Notion, and Terminal).
3. Expand consented speech evaluation across speakers and languages. Report model, host, corpus, errors, fact preservation, and correction time separately.
4. Evaluate Handy's clipboard receipt and download-resume designs in small scoped changes. Preserve FlowPilot's stronger requirement that confirmed delivery means observing text in the destination, not merely a clipboard read.
5. Implement external editing only with verified document revision, selection/range, and post-edit checks. Do not re-enable it by accepting a caller-supplied label.
6. Sign `FlowPilot.exe` and `FlowPilot-Setup-v3.2.3.exe` via Authenticode, reconcile release assets and SHA-256 checksums, and publish only after interactive `--require-all` sign-off.

Historical branches and releases were inspected, not deleted. The absence of a
current file does not prove sensitive material was erased from Git history. No
history rewrite, branch deletion, or release replacement is part of this cleanup.
