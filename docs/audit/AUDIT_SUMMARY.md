# FlowPilot audit summary

Updated 2026-10-26 for the RC6 pilot candidate. This page is a map to current evidence, not a claim that every feature or target app is verified.

## What was checked

- The 59 suite local runner reported **54 passed, 5 skipped, 0 failed** in a headless Windows session. The skipped suites require a physical desktop. See the [RC6 manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) for the exact archive and test accounting.
- The packaged executable passed the named mutex smoke test and transcribed a SAPI fixture using bundled base weights with an empty isolated model cache. The bundled small model passed file size and SHA-256 integrity checks.
- `npm test` passed the loopback API and WebSocket lifecycle.
- The release packager passed ZIP CRC, embedded executable hash, required notice, and forbidden filename checks. The candidate remains unsigned.
- The [release review](../reviews/2026-10-26-ad3dce9-release-review.md) records the model download, Unicode typing, signing, and documentation faults found during this pass and the focused repairs.

## What remains open

The five skipped desktop suites are not physical delivery proof for this build. Pilot measurements are still needed for broad paste reliability, microphone disconnect behavior, and real speaker accuracy in English, Hindi, Tamil, and Malayalam. The network test covers selected dictation paths and does not measure every process or the explicit user initiated model download. No paired trial in this audit proves a general advantage over Wispr Flow.

Earlier generated audit files with stale counts and unsupported performance claims were removed from the current public tree. Local copies are retained under ignored `private/review/`. Their old Git commits remain reachable; deleting files in a new commit does not erase public history.
