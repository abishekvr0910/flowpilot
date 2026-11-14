# Handy source review and FlowPilot follow-up

Source review date: 2026-11-14. FlowPilot baseline: `409b31d` (source version
3.2.2). Handy reference: [`aca8985190c3ad7f361d8a80cb30f179513ed690`](https://github.com/cjpais/Handy/tree/aca8985190c3ad7f361d8a80cb30f179513ed690),
whose commit message is `release v0.10.1`.

This is static source inspection, not a runtime comparison or performance benchmark.
No Handy source or assets were copied into FlowPilot. The previous Handy handoff was
not found in the searched local documentation, private, and reference directories;
this report records a fresh comparison with an explicit source identity.

## What we can learn

| Pattern observed in Handy | FlowPilot position | Practical follow-up |
| --- | --- | --- |
| Windows reliable paste uses delayed clipboard rendering and consumer read receipts, then a quiet period and sequence checks before restoration. | FlowPilot has guarded clipboard restoration and target-buffer verification, but not this receipt mechanism. | Prototype receipts as a timing signal for restoration. A consumer read must never become `CONFIRMED_INSERTED` without destination-text verification. |
| Windows clipboard opt-out markers include `CanUploadToCloudClipboard`. | FlowPilot used the unrecognized `CanUploadToCloudStore` name and untyped ctypes handles. | Fixed the marker names and moved handle ownership to pywin32; tests cover serialized DWORD values and failure paths. |
| Download tests use a scripted local HTTP server to exercise partial files, correct and wrong ranges, ignored Range headers, HTTP 416, corrupt hashes, oversized responses, cancellation, and stalled transfers. | FlowPilot already has SHA-256 checks, temporary-file replacement, and cancellation checks. | Extend failure-path tests and evaluate resuming interrupted large models. Do not duplicate existing integrity checks or make setup implicit during dictation. |
| A small transcription policy module chooses streaming, pause-based chunking, or whole-clip decoding from loaded-model capabilities. | FlowPilot supports prefix checkpoints and specialist routing, with substantial orchestration in large modules. | Separate capability decisions from execution as needed, and test long recordings at pause boundaries. This does not require a framework rewrite. |
| The README explains model setup, platform limitations, paste timing, beta status, and release signature verification. | FlowPilot's README mixed old pilots, newer source, contradictory defaults, and unsupported editing promises. | Replaced it with a shorter guide, explicit release/source distinction, and links to a current status document. |

Primary sources inspected:

- [Windows paste transaction implementation](https://github.com/cjpais/Handy/blob/aca8985190c3ad7f361d8a80cb30f179513ed690/src-tauri/src/paste_tx/windows.rs).
- [Downloader failure and resume tests](https://github.com/cjpais/Handy/blob/aca8985190c3ad7f361d8a80cb30f179513ed690/src-tauri/src/managers/model/download/tests.rs).
- [Transcription policy](https://github.com/cjpais/Handy/blob/aca8985190c3ad7f361d8a80cb30f179513ed690/src-tauri/src/managers/transcription/policy.rs).
- [README, setup, limitations, and signature instructions](https://github.com/cjpais/Handy/blob/aca8985190c3ad7f361d8a80cb30f179513ed690/README.md).
- [Microsoft clipboard format documentation](https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard-formats), used to verify the marker correction independently.

## Preserve FlowPilot's constraints

Keep PySide6 and the Windows delivery pipeline. Preserve no implicit model downloads,
local dictation, conservative FactGuard behavior, a non-activating HUD, terminal
safeguards, explicit recovery, and observed-text confirmation. Clipboard-read receipts
can come from a reader other than the target editor and are insufficient as proof of
insertion. Handy's auto-submit options are not a reason to send Enter in terminals.

Handy's documentation describes updater signatures. Those are a different verification
mechanism from Windows Authenticode publisher signing. Neither a signing tool nor a
checksum alone establishes the identity or safety of a particular download.

## What remains unknown

No identical-audio, identical-target comparison was run. Accuracy, correction effort,
resource usage, user preference, and real paste reliability cannot be ranked from
this inspection. Handy's beta paste path also has platform and format limitations;
source inspection is not proof that it works in every application.

The immediate priority is a trustworthy FlowPilot release and measurement of the
core dictation journey. See [current status and next steps](../STATUS.md).
