# Release and trust

This area distinguishes code, a local candidate, and a public download. The current release claim should describe the exact artifact that users receive.

## Release prerequisites and gates

### Mandatory release completion criteria
Before promoting any candidate to public release, satisfy the [current release review](../reviews/2026-10-26-ad3dce9-release-review.md), [release guide](../release/flowpilot_build_and_release.md), and [release evidence template](../release/RELEASE_EVIDENCE_TEMPLATE.md):

1. **Strict regression runner**: Execution of `python -X utf8 tests/run_all_tests.py --require-all` on an interactive desktop. Any failed or skipped suite prevents release promotion.
2. **Hosted CI verification**: Green GitHub Actions CI for the exact intended source commit, including Node.js integration (`npm test`) and binary smoke validation. Hosted skips remain visible and require explicit physical desktop evidence before signoff.
3. **External transform safety repair**: Unsupported external Replace and Revert refuse without any input dispatch, including when a caller supplies a supposed verified transaction. Preview and Copy Output remain available, as does guarded scratchpad editing.
4. **Physical hardware and editor validation**: Live microphone capture, audio ducking restoration, and confirmed text insertion across diverse target editors (Notepad, VS Code, Word, Terminal).
5. **Fresh artifact provenance and verification**: Build the new candidate from its recorded source identity. Keep the original RC8 archive and hashes historical. After code changes or signing, test the final bytes, verify ZIP CRC, and compute fresh executable and archive hashes in the matching manifest. A development build from a dirty tree remains a development candidate with a recorded patch identity.
6. **Dual profile lifecycle testing**: Test a fresh profile with `save_history_text: false` and upgrades from supported existing profiles, preserving privacy choices, dictionary, snippets, companion settings, and old records. The RC8 source includes the Smart companion policy; test its default and migration against the exact candidate. Do not apply an older candidate feature boundary to RC8 or a future build.
7. **Documented rollback and downgrade limits**: Record the previous public download and tested profile compatibility. Do not assert that migrations are additive or older binaries can read them without evidence.
8. **Measured performance**: Use the [runtime protocol](../testing/RUNTIME_PERFORMANCE_PROTOCOL.md). Processing duration and unverified dispatch must not be described as confirmed visible text latency. Record unmeasured hardware classes and resource phases explicitly.

## Existing foundation

### 11. Optional local API · existing

An optional token protected server exposes a subset of audio endpoints on loopback. It is not required for normal desktop dictation, and client compatibility is not universal. Code in `engine/server.py` and `tests/test_api_and_websocket.py`.

### 12. Local storage and privacy controls · existing

New profiles default to no persisted dictation history (`save_history_text: false`), while meetings, scratchpad, settings, and the last in-memory recovery text have separate lifecycles. Selected paths have socket-level egress tests. Code in `engine/config.py`, `engine/orchestrator.py`, `engine/history_vault.py`, and `tests/test_network_egress.py`.

### 13. Published Windows builds · existing

The latest published application download checked on 2026-11-14 is v3.1.3, with unsigned installer and ZIP artifacts. Source is version 3.2.3. The [artifact manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) distinguishes published downloads from local build records, including historical RC8 results. Any current source repair requires a new candidate build and fresh verification. See [current status](../STATUS.md); hosted skips do not prove physical desktop behavior.

## Next release

### 32. Pilot reliability hardening · in-progress

Current source contains bounded microphone open and close handling, capture stall detection, fail-safe elevated-window insertion, bounded opt-in local metrics, and Indic model guidance. RC9 includes PortAudio hot-plug re-enumeration and WASAPI worker-thread COM initialization; physical 3.5mm Realtek WASAPI hot-plug unplug/reconnect is verified in [`PHYSICAL_USB_UNPLUG_RECEIPT_20261027_000556.md`](../testing/PHYSICAL_USB_UNPLUG_RECEIPT_20261027_000556.md) (`analog_jack_hd_audio_endpoint`, `is_usb_bus_device=false`) alongside `scripts/verify_audio_device_gate.py`, and dedicated USB bus hot-plug has a [dated candidate receipt](../testing/PHYSICAL_USB_BUS_UNPLUG_RECEIPT_20261028_203758.md). Broad editor reliability (Word, Slack, Notion), wider hardware coverage, and real speech quality across Indic speakers remain open evidence gates. See the [pilot hardening review](../reviews/2026-10-25-pilot-reliability-and-competitive-position.md) and [real speech diagnostic](../evaluation/EN_HI_TA_ML_REAL_VOICE_BASELINE_2026-10-26.md).

**Done when:** the new candidate passes the full strict desktop gate, a real USB disconnect and reconnect trial, elevated and opaque editor safety trials, a fresh package smoke and offline self-test, and hosted CI from its source commit. Metrics and public copy must describe measured boundaries.

### 14. Consented Windows pilot · planned · needs a decision

Let a small group use the exact candidate archive on their own Windows machines and report what happens during normal work. Keep sensitive transcript collection off by default.

**Done when:** the repaired pilot candidate has consent, reviewed instructions, a fixed artifact hash, clear tasks, separate delivery outcome counts, and a decision to fix, continue testing, or release. Select the current candidate from the artifact manifest; any source repair requires a new artifact.

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
