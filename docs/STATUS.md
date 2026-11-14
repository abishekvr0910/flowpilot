# FlowPilot current status and agent handoff

Reviewed 2026-11-14. This is the current status entry point. Dated specifications,
pilot receipts, audits, and the October Gemini handoff retain historical context;
their completion labels do not establish the state of newer source or binaries.

## Source, downloads, and verification

| Item | Observed state |
| --- | --- |
| Baseline source | `409b31dfd99cd364a1767cee036d2e5200794259`, package version 3.2.2 |
| Baseline GitHub CI | [Run 43343650063](https://github.com/abishekvr0910/flowpilot/actions/runs/43343650063) completed successfully; this does not prove interactive desktop gates |
| Latest published application download | [v3.1.3](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.1.3), published 2026-11-04, unsigned installer and ZIP |
| 3.2.0 / 3.2.1 / 3.2.2 artifacts | Local build records in the manifest; no corresponding published GitHub release found on the review date |
| Current cleanup | Branch `fix/repository-consistency-handy-review`; proposed changes require review and a new build before reaching installed users |
| Handy reference | Source at `aca8985190c3ad7f361d8a80cb30f179513ed690` (v0.10.1); [comparison and sources](research/HANDY_SOURCE_REVIEW_2026-11-14.md) |

The [artifact manifest](release/RELEASE_ARTIFACT_MANIFEST.md) preserves older build
hashes. This cleanup does not revalidate those bytes or promote a release.

## Where the product stands

| Area | Implementation and remaining evidence |
| --- | --- |
| Windows dictation | Local capture, VAD, Whisper, formatting, and delivery exist. CPU fallback now covers CUDA failure during lazy decoding, as reproduced on this host. |
| Text delivery and recovery | Focus checks, status distinctions, terminal protections, and recovery exist. Broad first-attempt reliability across real editors still requires an interactive matrix. |
| External text editing | Transform preview and Copy Output work. External rewrite and undo are disabled because a window handle and a copied selection do not verify the document revision or current range. Scratchpad transactions remain separate. |
| Microphone identity | Persistent identity and missing-device refusal exist. Dated 3.5mm and USB bus receipts cover specific hardware, not all devices. |
| Languages and models | Whisper and a Tamil ONNX specialist exist, with explicit model provisioning and bounded benchmark reports. Diverse speakers and code switching need further evaluation. |
| Local text repair | Implemented, experimental, disabled by default. Its presence in master supersedes the old claim that it exists only on a sandbox branch. |
| Privacy | Offline model use, history off for new profiles, loopback integrations, and clipboard exclusion requests exist. User scripts, destination apps, clipboard readers, and separately configured model services have separate boundaries. |
| Distribution | Installer and signing tools exist. Published v3.1.3 binaries are unsigned. Tools for signing are not evidence of signed downloads. |
| Companion, meeting, and workspace tools | Implemented features have tests, but broad implementation is not proof of usability or production quality. Core dictation remains the priority. |

## Inconsistencies addressed by this cleanup

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

## Verification of this cleanup

The complete 72-suite headless run finished
with **67 passed, 5 skipped, 0 failed** in 383.12 seconds. The initial run reproduced
the missing-CUDA-library failure; the corrected real STT test passed. Logs remain
locally in `scratch/cleanup-audit.log` and `scratch/cleanup-final-audit.log` (ignored
by Git). Focused model lifecycle/CUDA/skip tests also passed (15 tests), and external
edit refusal/preview passed (7 tests). Repository consistency reported zero errors.

Five interactive desktop suites skipped: clipboard injection, Notepad dictation,
cross-application injection, full specification desktop scenarios, and modern UIA
target verification. Existing-binary smoke/profile checks used the pre-existing
`dist/FlowPilot/FlowPilot.exe`; they do not prove this source patch is in that binary.
The strict release gate is therefore still open.

After the Smart Pause correction, eight affected suites passed again with no skips
or failures (53.76 seconds): call capture/cancellation, hotkeys, orchestrator state,
session lifecycle, companion visibility, pilot reliability, recovery feedback, and
external edit refusal. There are now 73 registered suites; the new Smart Pause suite
was verified in this follow-up, not retroactively included in the earlier full run.
The real read-only Windows capture probe returned `probe_unavailable=False`.
Node REST/WebSocket integration (`npm test`) passed. Repository consistency and
`git diff --check` passed. [Machine-readable evidence](reviews/evidence/2026-11-14-repository-cleanup.json)
retains the per-suite results; raw local logs remain under `scratch/`.

The local audit required normal Windows temporary-directory access outside the
sandbox. No Git index lock or leftover test process was found at the resume check.
The authorized delivery is a pull request; no merge, release promotion, or history
rewrite is authorized by this handoff. Verify the PR's hosted CI before merging.

## Next work, in order

1. Review and merge this cleanup after CI. Build a new candidate from the merged
   commit and record its exact identity; old local binaries cannot verify these fixes.
2. Run the strict interactive Windows gate on that candidate: microphone loss and
   recovery, focus changes, clipboard preservation, terminal insertion, and application
   delivery in Notepad, VS Code, Chrome, Word, Slack, Notion, and Terminal.
3. Expand consented speech evaluation across speakers and languages. Report model,
   host, corpus, errors, fact preservation, and correction time separately.
4. Evaluate Handy's clipboard receipt and download-resume designs in small scoped
   changes. Preserve FlowPilot's stronger requirement that confirmed delivery means
   observing text in the destination, not merely a clipboard read.
5. Implement external editing only with verified document revision, selection/range,
   and post-edit checks. Do not re-enable it by accepting a caller-supplied label.
6. Reconcile release assets, signature status, and documentation when publishing.

Historical branches and releases were inspected, not deleted. The absence of a
current file does not prove sensitive material was erased from Git history. No
history rewrite, branch deletion, or release replacement is part of this cleanup.
