# FlowPilot release review, 2026-10-26

## Scope and evidence

I reviewed the changes from `4721109` through `ad3dce9`, with focused runtime checks of model provisioning, text insertion, signing, release packaging, and public documentation. This is a review of those changed paths, not proof that every application surface has no defects.

The hosted Windows CI run for `ad3dce9` passed. After the repairs in this review, the local 59 suite runner reported **54 passed, 5 skipped, 0 failed** in a headless session. The five skips require a physical desktop. `npm test`, Python compile checks, and focused regression tests also passed. A fresh packaged build and physical desktop checks are separate release gates.

## Findings and repairs

| Severity | Finding | Repair |
|---|---|---|
| High | The direct Unicode fallback declared an incomplete Win32 `INPUT` union and a 32 bit `dwExtraInfo`. On this 64 bit host it passed a 16 byte keyboard structure to an API that needs a 24 byte keyboard structure inside a 40 byte `INPUT`. Non BMP characters were also truncated. | Use the full Win32 input union and pointer sized field, emit UTF 16 surrogate pairs, and test the structure size and scan codes without sending real keys. Multiline direct typing into terminals now refuses dispatch to avoid accidental Enter submission. |
| High | Signing success was reported even when `signtool verify` failed. Invalid CI certificate data could silently fall back to an unsigned archive. | Treat verification failure and malformed configured certificates as release failures. Focused tests assert that no archive is created. |
| Medium | The model downloader deleted an existing model file before renaming the new file. A rename failure could leave neither file available. | Download to a unique temporary file and use one atomic replacement. A regression test proves an existing file survives replacement failure. |
| Medium | The downloader's `QThread` was owned by a settings or setup widget that could close during an HTTPS read, risking destruction of a running thread. | Keep active workers independent of dialog lifetime, cancel them on close, keep a process level reference until they finish, and report worker exceptions to the UI. A focused Qt test closes the parent while a worker completes. |
| Documentation | Two public reports used aggregate data from a local Wispr user database and stated unverified competitor internals as certain facts. | Preserve local copies under ignored `private/review/` and remove those reports from the current public source tree. Their prior Git commits remain reachable in repository history; this change does not erase that history. |

## Remaining release limits

The new code paths have automated coverage, but the five skipped physical desktop suites must not be counted as passes. Real microphone unplug behavior, broad target app insertion rates, and human speaker accuracy for Hindi, Tamil, and Malayalam remain pilot measurements. An unsigned archive is suitable only as a clearly labeled pilot prerelease. No current evidence supports a claim that FlowPilot is universally faster or more accurate than Wispr Flow.
