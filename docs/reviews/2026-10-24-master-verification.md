# FlowPilot review of the Gemini handoff and scrolling behavior

**Later result:** The defects below were subsequently repaired and the local strict interactive gate passed 56 of 56 suites. See the [remediation and release gate record](2026-10-24-remediation-and-release-gate.md). This document preserves the original failing probes and is not the current release decision.

Date: 2026-10-24. Source baseline: `6555e3dc9cd507b5fbc31d71f3d0be95d1c4078a` plus the current uncommitted changes.

**Decision: the new microphone and observer features are not ready for release signoff.** The ordinary missing microphone case is fixed, but other resolution paths still attempt capture without a trustworthy selection. The benchmark observer still produces false delivery confirmations. Scrolling over tab headers initially switched sections without a click; Gemini fixed that behavior during this review and the final focused checks passed.

Gemini was still editing the UI during this review, as confirmed by the user. Codex added regression tests before detecting concurrent edits, then stopped production UI changes. The attempted production patch did not apply. This report gives Gemini the remaining work and acceptance checks. It does not certify the running executable or a future source revision.

Final UI recheck: Gemini added `QTabBar` protection to the dashboard application filter. All 27 tests in `tests/test_workspace_refresh.py` then passed in 11.55 seconds, including the three initially failing regressions. This verifies the tested source behavior offscreen, not a rebuilt executable or every physical mouse and touchpad condition.

## Verification performed

All probes used a temporary config profile. Qt ran offscreen. Physical audio streams, model loading and input dispatch were not used. No real clipboard contents, microphone audio or user documents were collected.

| Check | Result |
| --- | --- |
| Gemini audio device and observer suites | 19 passed in 0.423 seconds, with `sounddevice.InputStream` mocked around the run |
| Initial scrolling regression cases | 3 failed, 4 passed in 3.91 seconds |
| Final full workspace suite after Gemini's fix | 27 passed in 11.55 seconds |
| Tab wheel behavior | Reproduced in Meetings, Studio and Settings; fixed and retested during the review |
| Repeated downward wheel at page bottom | Stable in compact Home, Studio Library and Settings Dictation |
| Nested scroll boundary | Inner scroll reaching the bottom did not move the outer scroll area in the test |
| Whitespace | `git diff --check` passed at review time |
| Complete 56 suite gate | Not independently rerun in this review; the 52 pass / 4 skip count is Gemini's reported result |
| Physical desktop, live video and packaged build | Not retested in this review |

The isolated reproduction results are in [review evidence](evidence/2026-10-24-review-probes.json). The local reproduction script is `scratch/codex_review_20261024.py`; it is a local diagnostic, not a shipped tool. Source hashes in the evidence identify the files inspected. The test suite passing does not override the failing adversarial probes below.

## Findings and required corrections

### 1. High: unresolved microphone states can still open an unintended device

Locations: `engine/audio_devices.py:114`, `:152`, `:179`; callers in `engine/orchestrator.py` and `ui/scratchpad_view.py`.

The normal missing headset case now returns `-9999`, and recorder warmup makes zero stream calls. That repair is confirmed. However:

| Resolution | Returned device | Observed recorder action with hardware mocked |
| --- | --- | --- |
| `UNAVAILABLE`, empty enumeration | `None` | Calls `InputStream(device=None)` |
| `MISSING`, empty endpoint name | `None` | Calls `InputStream(device=None)` |
| `AMBIGUOUS`, identical name/API/channels | First matching index, 4 in the probe | Calls `InputStream(device=4)` |

`None` means system default to sounddevice. An enumeration error or invalid stored selection must not authorize that fallback. Identical microphones cannot be distinguished by picking the first match.

Suggested correction: require a usable resolution before every capture entry point. Reserve `None` for an explicit valid system default choice. All unavailable, missing, invalid and ambiguous states must block warmup and recording with a visible recovery action. Cross API fallback also needs an unambiguous identity, not merely the first preferred name match.

Acceptance: test resolver to real recorder integration for each status, mocking only the stream boundary. Assert zero stream attempts for unusable selections in normal dictation, scratchpad commands and setup microphone preview.

### 2. High: persistent microphone identity is not authoritative throughout the UI and configuration lifecycle

Locations: `engine/orchestrator.py:59`, `:674`, `:692`; `ui/setup_wizard.py:265`; `ui/settings_dialog.py:171`.

Four reproductions show the remaining integration problems:

1. An explicit `{"mode":"default"}` with a stale legacy index 4 creates a recorder for device 4. The new choice must take precedence over legacy keys.
2. `update_config({"audio_device_index":12})` updates the in memory identity to Mic B, but the saved JSON retains `{"mode":"default"}`. The derived identity is assigned after `save_config`.
3. Opening Setup with a missing saved headset selects system default automatically. This bypasses the otherwise correct sentinel handling before the resolver runs.
4. Two endpoints with the same name and API but different channel counts cause Settings to select the first, one channel endpoint when the stored identity requests two channels. Both pickers match name/API and omit the disambiguator.

Suggested correction: normalize the complete selection before saving once, preserve explicit default mode, use the same resolution contract in both pickers, and show a disconnected or ambiguous placeholder without substituting a working microphone. Preserve the user's saved identity until they deliberately choose another one.

The simple legacy migration now produces the correct identity in memory. The handoff nevertheless incorrectly says `load_config` passes raw JSON to migration: current code still passes the merged `config`. The local probe also logged a Windows access denied error while migration attempted to replace the config file from inside its open read context. Close the read handle before saving and add a reload from disk assertion to the migration test.

### 3. High: observer can verify delivery that did not happen, or conceal duplicates

Locations: `benchmarks/delivery_observer.py:71`, `:143`, `:160`.

Confirmed using a deterministic clock and synthetic document strings:

| Input situation | Current result | Required result |
| --- | --- | --- |
| Baseline reader returns `None`, next read contains an existing phrase | `VERIFIED_FIRST_DELIVERY` | Missing baseline evidence, no verified latency |
| Expected `phrase`, document receives `phrase phrase` | `VERIFIED_FIRST_DELIVERY` | Duplicate classification |
| Baseline is `hello phrase end`, later buffer is `hello OTHER phrase end`, expected insertion is `phrase` | `VERIFIED_FIRST_DELIVERY` | Existing token must not count as newly delivered text |

The substring guard is insufficient when the fallback delta is the entire document. A smaller document is not necessarily a deletion failure either: replacing a selected passage can legitimately shorten a document.

Suggested correction: require a readable baseline captured before dispatch, calculate the actual document change including the relevant selection, correlate that change with the dispatched payload, and classify duplicates and partial insertions explicitly. Keep speech accuracy scoring separate from delivery verification. Do not identify a wrong window solely because its text differs; target identity and focus evidence are separate inputs.

### 4. High: observer timing and aggregation can report invented zero latency

Locations: `benchmarks/delivery_observer.py:105`, `:125`, `:208`.

1. A singleton verified sample with first appearance 80 ms and settled appearance 120 ms produces p50 and p95 of **0 ms** for both. The percentile interpolation needs an equal index case or a validated shared implementation.
2. Text appears at 0 ms, disappears at 30 ms, then reappears at 200 ms. The observer confirms it immediately on reappearance and reports settled time 0 ms. Returning to baseline must reset the settlement candidate.
3. A reader taking 60 ms per call overruns a requested 10 ms observation budget, returning after approximately 132 ms in the probe. `initial_probe` is outside the deadline and the callback is synchronous. A blocked UIA call can block indefinitely.

Suggested correction: use one monotonic deadline covering all reads, a bounded reader mechanism with bounded concurrency and shutdown, and reset stability on every content transition. A timeout must not become a zero measurement. Add singleton, baseline restoration, stalled reader and repeated timeout tests.

The observer is not yet wired into an actual paired application benchmark. Searches found its callers in its unit tests, not a physical target adapter or the WAV benchmark. Feature 29 remains in progress.

### 5. High: comparative and privacy claims exceed the attached measurements

Locations: `docs/testing/FINAL_COMPETITIVE_AND_VISIBILITY_VALIDATION_REPORT.md`, `docs/handoffs/CODEX_FINAL_VERIFICATION_AND_AUDIT_HANDOFF.md`, and the local script `scratch/run_vbcable_paired_benchmark.py`.

The script records only FlowPilot transcription and formatting trials. Wispr contributes a process snapshot, not matching per fixture transcription or observed insertion results. Comparing FlowPilot p50 to an unrelated Wispr history mean does not establish "27% faster". An unmeasured competitor result cannot establish an advantage for facts, identifiers or p95.

The script samples every process whose name contains `python` before initializing its STT engine. Its JSON says `process_count: 4`, contradicting the report's one process claim. This is not a measured packaged FlowPilot memory comparison.

The same script writes the literal `"network_egress": "Zero bytes (offline)"`; it does not measure bytes. The real voice report explicitly says `network_verification: not instrumented by this runner`. Preserve the offline architecture claim, but describe socket instrumentation only where it actually ran and keep whole process byte measurement unmeasured.

The 120 clip report does contain the reported DE/ES/FR values as `avg_wer`. Label these per clip averages, model `base`, and this corpus only. Do not extend them to English, Hindi, Tamil or Malayalam acoustic quality. "RTL/script handling 100% verified" is not evidence of recognition quality for those languages.

Suggested correction: rewrite the two new reports with these boundaries, link tracked sanitized evidence, and keep unknown competitor values unknown. Do not use the current reports to promote the release or mark competitive validation complete.

### 6. Medium: a purported unit test can open a real microphone and leave it warm

Location: `tests/test_audio_devices.py`, `test_deferred_switch_during_active_recording`.

This test wraps the real `set_device` but does not mock `sd.InputStream`. `stop_recording` applies the deferred switch, and that path starts warmup even though the test passed `keep_stream_alive=False`. The surrounding mock in this review recorded one attempted hardware stream creation. The test does not close the recorder afterward.

Suggested correction: mock only the physical stream, exercise the actual lifecycle methods, and close the recorder in `finally` or registered cleanup. Verify stream closure and frame retention. A regression suite must not open an arbitrary real device index 12.

### 7. Resolved during review: wheel movement switched tabs without a click

Locations: `ui/flowpilot_dashboard.py`, `ui/workspace_style.py`, and new cases in `tests/test_workspace_refresh.py`.

The initial filters protected closed combo boxes but did not protect `QTabBar`. A downward wheel event changed Meetings from index 1 to 2, Studio from 0 to 1, and Settings from 0 to 1. This changes the page contents and looks like a scroll jump. The compact bottom boundary tests did not reproduce a separate bounce. Gemini subsequently added tab protection; the regressions now pass.

Remaining policy and coverage checklist for Gemini, who currently owns these files:

1. Use one application owned wheel policy for the dashboard and standalone Settings, Studio and Setup. Avoid installing separate competing filters on every child.
2. A closed combo must forward wheel movement to the nearest scroll viewport without changing its value, including when focused. Preserve an open popup's normal behavior.
3. Consume wheel events on tab headers without changing the selected section. Keep mouse clicks and keyboard navigation working.
4. Preserve the wheel event's pixel delta, angle delta, phase and coordinates when forwarding. Accept the handled original event so it cannot be applied twice.
5. Keep bottom boundaries stable. Do not resize the dashboard, reset scroll positions, or change unrelated layout padding as a scrolling fix.

Reproduction command, in an isolated profile with `QT_QPA_PLATFORM=offscreen`:

```powershell
python -X utf8 -m pytest tests/test_workspace_refresh.py -q -k "wheel_over_tabs or repeated_wheel or inner_scroll_boundary"
```

The new regression tests were not relaxed to report success. They turned green after the production behavior changed. Click and keyboard preservation tests, standalone dialog coverage, and physical mouse/touchpad checks remain useful before marking whole app usability complete.

## Next verification order

1. Gemini finishes the UI changes and addresses findings 1 through 6. Keep microphone safety and observer fixes separately reviewable.
2. Reproduce each failing case against a stable source snapshot. Recheck the supplied tests with physical hardware boundaries mocked.
3. Run the full source gate with honest skips, then the required physical desktop gate on an idle desktop. Record the exact source revision and failures, not just counts.
4. Run the remaining visibility, real speaker and matched competitor trials required by the scope. A settings correction from `always` to `smart` is not a substitute for every live gate row.
5. Only then build and verify a fresh candidate. The RC3 binary and its historical hashes do not validate this uncommitted source.

No release tag, commit, push, packaged binary or user profile was changed by this review.
