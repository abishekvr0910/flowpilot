# Release and trust

This area distinguishes code, a local candidate, and a public download. The current release claim should describe the exact artifact that users receive.

## Release prerequisites and gates

### Mandatory release completion criteria
Before promoting any candidate to public release, satisfy the [engineering directive](../architecture/CODEX_DIRECTIVE.md), [release guide](../release/flowpilot_build_and_release.md), and [release evidence template](../release/RELEASE_EVIDENCE_TEMPLATE.md):

1. **Strict regression runner**: Execution of `python -X utf8 tests/run_all_tests.py --require-all` on an interactive desktop. Any failed or skipped suite prevents release promotion.
2. **Hosted CI verification**: Green GitHub Actions CI for the exact intended source commit, including Node.js integration (`npm test`) and binary smoke validation. Hosted skips remain visible and require explicit physical desktop evidence before signoff.
3. **External transform safety repair**: Unsupported external Replace and Revert refuse without any input dispatch, including when a caller supplies a supposed verified transaction. Preview and Copy Output remain available, as does guarded scratchpad editing.
4. **Physical hardware and editor validation**: Live microphone capture, audio ducking restoration, and confirmed text insertion across diverse target editors (Notepad, VS Code, Word, Terminal).
5. **Fresh artifact provenance and verification**: Build the new candidate from its recorded source identity. Keep the original RC2 archive and hashes historical. After code changes or signing, test the final bytes, verify ZIP CRC, and compute fresh executable and archive hashes in the matching manifest. A development build from a dirty tree remains a development candidate with a recorded patch identity.
6. **Dual profile lifecycle testing**: Test a fresh profile with `save_history_text: false` and upgrades from supported existing profiles, preserving privacy choices, dictionary, snippets, companion settings, and old records. RC3 includes the Smart companion policy; test its default and migration against the exact candidate. Do not apply the older RC2 feature boundary to RC3.
7. **Documented rollback and downgrade limits**: Record the previous public download and tested profile compatibility. Do not assert that migrations are additive or older binaries can read them without evidence.
8. **Measured performance**: Use the [runtime protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md). Processing duration and unverified dispatch must not be described as confirmed visible text latency. Record unmeasured hardware classes and resource phases explicitly.

## Existing foundation

### 11. Optional local API · existing

An optional token protected server exposes a subset of audio endpoints on loopback. It is not required for normal desktop dictation, and client compatibility is not universal. Code in `engine/server.py` and `tests/test_api_and_websocket.py`.

### 12. Local storage and privacy controls · existing

New profiles default to no persisted dictation history (`save_history_text: false`), while meetings, scratchpad, settings, and the last in-memory recovery text have separate lifecycles. Selected paths have socket-level egress tests. Code in `engine/config.py`, `engine/orchestrator.py`, `engine/history_vault.py`, and `tests/test_network_egress.py`.

### 13. Windows RC2 candidate · existing

This foundation row preserves the historical RC2 milestone. The current candidate is RC4, built from committed packaging source at `2baa2f9`, with bundled base and small models. Hosted CI [run 40116350311](https://github.com/abishekvr0910/flowpilot/actions/runs/40116350311) passed with 47 suites and 9 honest hardware or desktop skips. An initial exact-candidate local run passed 55 suites and failed one physical Notepad focus suite; the targeted suite and full strict interactive rerun then passed against the same executable, ending at 56 passed, 0 skipped, 0 failed. The first failure remains in the release record. RC4 is unsigned and remains a pilot candidate; RC2 and RC3 results and hashes are historical, and hosted skips are not physical desktop passes. See the [artifact manifest](../release/RELEASE_ARTIFACT_MANIFEST.md).

## Next release

### 14. Consented Windows pilot · planned · needs a decision

Let a small group use the exact candidate archive on their own Windows machines and report what happens during normal work. Keep sensitive transcript collection off by default.

**Done when:** the repaired pilot candidate has consent, reviewed instructions, a fixed artifact hash, clear tasks, separate delivery outcome counts, and a decision to fix, continue testing, or release. The old RC2 archive is not evidence for a source repair.

- [ ] Design it (spec): `/architect consented Windows pilot`

### 17. Distribution size and publisher identity · planned · needs a decision · GA

Make the offline Windows package easier to download and trust without silently removing the chosen language model or requiring a network connection on first launch.

**Done when:** the mandatory gates above are met for the final bytes, clean and upgraded profiles pass, contents and size are explained, signing status is verified, rollback limits are recorded, and published hashes match the tested artifact. Disclose unsigned status plainly when applicable.

- [ ] Design it (spec): `/architect Windows distribution and signing`

### 18. Trust, security, and public claims review · planned · needs a decision · GA

Review privacy, dependencies, artwork rights, API exposure, release instructions, and benchmark language before public distribution. Keep competitor comparisons evidence based. Reconcile documentation drift against the current runner rather than reusing historical suite counts.

**Done when:** claims match current build evidence, third party notices cover packaged assets, no competitor code or credentials are present, documented storage paths match runtime behavior, and unresolved security or reliability risks are visible to users.

- [ ] Design it (spec): `/architect public release trust review`

Runtime evaluation is owned once, in [voice scope, feature 25](voice.md). Its results are a prerequisite for release claims.
