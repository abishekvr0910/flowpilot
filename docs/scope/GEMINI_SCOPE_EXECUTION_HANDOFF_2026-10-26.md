# Gemini Scope Execution Handoff

Status date: 2026-10-26

## Repository cleanup completed

Superseded local release packages and historical scratch outputs were moved out of the repository to:

`<local-backup-path>\FlowPilot_local_archive_20261026`

The move reclaimed approximately 28.48 GB from the working folder. The archive is recoverable and was not uploaded to GitHub.

The following items were deliberately preserved:

- `dist\FlowPilot\`, the current unpacked RC8 build
- `dist\FlowPilot-v3.1.0-RC8-win64.zip`
- `models\faster-whisper-base` and `models\faster-whisper-small`
- Current RC8 self-test, cross-application, evaluation, and benchmark evidence
- Active scratch worktrees

No tracked source files were deleted by this cleanup. The working tree already contained uncommitted sandbox edits; those edits were preserved.

## Scope execution order

Gemini must execute these steps in order and record evidence for each step. Do not promote the release or claim completion from mocked tests alone.

### Step 1: Physical hardware gate

Run the packaged RC8 build through microphone disconnect, reconnect, default-device change, and device-index change scenarios. Confirm that recording stops safely, no wrong microphone is selected, the UI remains responsive, and a later recording works. Record the exact build hash, device names, timestamps, and result.

### Step 2: Consented pilot intake

Distribute only the published RC8 prerelease to a small consented Windows pilot. Collect confirmed delivery, safe-abort, clipboard preservation, recovery-hotkey, and crash results across Notepad, VS Code, Chrome, Word, Slack, Notion, and Terminal. Do not store audio or transcript text by default. Record only anonymized metrics.

### Step 3: Real-speaker language evaluation

Collect consented human speech for English, Hindi, Tamil, and Malayalam, including code-switching and developer vocabulary. Measure WER or CER, factual-token preservation, negation preservation, latency, and failure cases. Keep Hindi, Tamil, and Malayalam labelled experimental until real evidence supports a stronger claim.

### Step 4: Paired Wispr comparison

Use identical audio fixtures and equivalent Windows targets. Measure stop-to-first-visible-text, settled delivery, correction time, memory, CPU, paste recovery, and network behavior. Report FlowPilot results and Wispr results separately. Do not claim superiority where a metric was not measured.

### Step 5: Local text repair sandbox

Keep `feature/local-slm-repair-sandbox` isolated from RC8 until review is complete. Before merging:

1. Add the missing `import os` in `engine/local_text_repair.py`.
2. Replace the synchronous inference call with a genuinely bounded worker or cancellable executor so the 400 ms deadline is enforceable.
3. Register `tests/test_local_text_repair.py` in the master test runner.
4. Add tests for model-load failure, timeout, malformed output, FactGuard veto, and unchanged-text fallback.
5. Re-run compile, focused tests, the complete suite, offline self-test, and network-egress tests.

## Release rules

- RC8 remains a controlled pilot prerelease, not a general release.
- Authenticode signing, physical desktop gates, and real-speaker evidence remain release requirements.
- Zero cloud egress and truthful delivery status are non-negotiable.
- Historical artifacts remain outside the repository and must not be reintroduced into `dist` or `scratch` without a documented reason.
- Update `docs/audit`, `docs/scope`, pilot instructions, privacy review dates, and license wording when evidence changes.

## Required handoff output

For every step, Gemini must provide the command used, the exact artifact or commit tested, pass and failure counts, skipped tests with reasons, and links to the evidence file. No step may be marked complete based only on a generated summary.
