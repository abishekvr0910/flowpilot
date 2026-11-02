# FlowPilot v3.1.0-RC13 — Independent Review Dossier

**Prepared for:** Gemini (adversarial second opinion)
**Prepared by:** Claude / OpenCode
**Date:** 2026-10-31
**Repository:** `https://github.com/abishekvr0910/flowpilot`
**Reviewed commit:** `2afd94b` (`feat(ux): add subtle musical earcons, 150ms post-roll audio overhang, HUD fallback toast, and idle update checker`)
**Reviewed tag:** `v3.1.0-RC13` (confirmed via `git ls-remote`; local tag list was stale)
**Artifacts inspected:** `FlowPilot-Setup-v3.1.0.exe` (692,934,347 bytes), `FlowPilot-v3.1.0-RC13-windows-x64.zip` (772,606,872 bytes)
**Code changes made during review:** none
**Second opinion:** Gemini, received 2026-10-31 — verdict, answers, and reconciliation in §10

---

## 0. Reviewer brief

You are reviewing this as an independent engineer and product critic. Do not accept the severity labels below at face value.

Return a structured review that answers:

1. **Per finding:** agree, disagree, or “insufficient evidence,” with a one-line reason.
2. **Methodology:** which measurements are weak, which conclusions overreach, and what would make them defensible.
3. **Missed risks:** what this review failed to examine that could change the verdict.
4. **Plan sequence:** is the proposed order correct, or would you reorder it?
5. **Claims to delete or soften:** quote the exact sentence.
6. **Decision:** would you ship RC13 as-is, ship a reduced GA, or hold?

Do not rewrite the product. Do not propose new features. The question is whether the diagnosis and remediation plan are sound.

---

## 1. Executive verdict

FlowPilot is technically ambitious and better tested than most two-week solo projects. The blocker is not code volume or feature breadth. The blocker is that the release cannot reliably reach or convince a user:

- The public installer is **unsigned**, **660.8 MB**, and has **no version/company metadata**.
- GitHub’s “Latest” release is **v3.0.2**, while all recent work is hidden under **pre-release RC13**.
- The in-app updater cannot discover RC13, and its version model cannot distinguish RC11 from RC13.
- Real-speech accuracy is **14.3% WER English**, **23.2% French** on the bundled 10-clip samples — not commercial parity.
- Idle runtime costs about **11% of one CPU core** and **272 MB RSS** while doing nothing.

**Recommendation:** freeze features. Ship one signed, base-model-only, correctly-versioned GA; fix the update channel; measure real-user correction time before adding anything else.

**Status after second opinion (2026-10-31):** Gemini concurred with all nine findings and recommended **HOLD** on promoting RC13 to "Latest." Reduced-GA conditions: signed binaries (F-01), working updater (F-02), base-only default bundle (F-04), idle fix baked into the binary (F-05), and privacy disclosure (F-06). Full response and reconciliation in §10.

---

## 2. Scope and method

### 2.1 What was reviewed

- GitHub repository metadata, releases, assets, CI runs, traffic, branch protection, runners, and community profile.
- Source at `2afd94b` / `v3.1.0-RC13`.
- Full local test suite and Node/FastAPI tests.
- ASR accuracy and latency on the bundled real-voice manifests.
- Startup time, idle CPU/RSS, self-test duration, installer/zip size, Authenticode status, and embedded version metadata.
- Release, scope, privacy, and packaging documentation for consistency.

### 2.2 Environment

| Item | Value |
|---|---|
| OS | Windows (win32) |
| CPU | 12th Gen Intel Core i5-12500H |
| RAM | 15.7 GB |
| Python | 3.11.15 (CI uses 3.12) |
| STT threads | 8 |
| Compute | CPU INT8, beam size 1, VAD disabled |
| Installer tooling | Inno Setup definitions in `installer/flowpilot_setup.iss`; PyInstaller in `flowpilot.spec` |

### 2.3 Commands run

```powershell
python -X utf8 tests/run_all_tests.py
npm test
python desktop_app.py --self-test
git rev-parse --short HEAD
git ls-remote --tags origin
Get-AuthenticodeSignature "dist\FlowPilot\FlowPilot.exe"
Get-ChildItem dist\FlowPilot -Recurse | Measure-Object Length -Sum
gh api repos/abishekvr0910/flowpilot/releases
gh api repos/abishekvr0910/flowpilot/actions/runners
```

Benchmarks used the bundled manifests under `docs/evaluation/` and an ephemeral harness in the user temp directory. The harness is not committed; all parameters needed to repeat the run are listed below.

### 2.4 Limitations

- WER is based on **10 clips per language**. It is indicative, not statistically conclusive.
- WER is **raw ASR output**, before FlowPilot’s `ContextProcessor` / `WritingIntelligence` post-processing. Product-level WER is therefore lower than the numbers here.
- Timings are from one machine and one power state.
- The installer was inspected, not installed on a clean Windows VM.
- GitHub metrics are point-in-time (2026-10-31).
- The 40-clip English manifest is incomplete locally: 30/40 audio paths are absent because `private/` is gitignored. Only the 30-item `EN_HI_TA_ML_REAL_VOICE_MANIFEST.json` maps fully to present clips.
- `hardware-tests.yml` could not be evaluated: no self-hosted runner is registered and the workflow has zero runs.

---

## 3. Repository and release health

| Signal | Finding | Confidence |
|---|---|---|
| Visibility | Public, MIT | High |
| Age | Created 2026-10-14; 215 commits by 2026-10-31 | High |
| Attention | 5 stars, 1 fork, 1 watcher, 0 open issues | High |
| Positioning | No repository topics; discussions disabled; wiki enabled | High |
| Latest stable | `v3.0.2-release` (2026-10-15), 5 asset downloads | High |
| Newest build | `v3.1.0-RC13` (2026-10-29), pre-release, 1–2 asset downloads | High |
| Release cadence | Seven visible RC releases in roughly two weeks | High |
| CI | 14/15 recent runs green, ~5–6 minutes each | High |
| Branch protection | 1 review required; **required status checks not enabled**; admins exempt | High |
| Hardware workflow | Requires self-hosted runner; **0 runners, 0 runs** | High |
| Community profile | 71%; no code of conduct, no PR template | High |
| Commit identity | 211/215 commits authored as `FlowPilot Engineering <engineering@flowpilot.local>` | High |
| Traffic (14 days) | 18 views / 10 uniques; 1,543 clones / 352 uniques | High |

The clone count is inconsistent with the view and star counts. Treat it as automated traffic until proven otherwise.

---

## 4. Measured performance

### 4.1 ASR accuracy

Model: faster-whisper `base`, INT8, beam 1, VAD off. Corpus: 10 real clips per language from the bundled manifests. Metric: normalized WER against `formatted_reference`.

**All WER figures in this section are indicative (N=10; ±5–8% margin), not a product accuracy claim — see Gate F in §6.**

| Language | n | WER | CER | Exact match | p50 decode | RTF |
|---|---:|---:|---:|---:|---:|---:|
| English | 10 | **14.3%** | 7.3% | 3/10 | 0.629 s | 0.101 |
| German | 10 | **14.7%** | — | 3/10 | 0.64 s | 0.113 |
| Spanish | 10 | **19.9%** | — | 2/10 | 0.65 s | 0.131 |
| French | 10 | **23.2%** | — | 1/10 | 0.63 s | 0.113 |

Observed English errors were concentrated in proper nouns and domain terms:

- “Kempton” -> “Campton”
- “Beitar Illit” -> “Byter Elite”
- “fair chance farms” -> “FairChan's”

`small` model, English only:

| Model | WER | Exact | p50 | Load | Marginal RSS |
|---|---:|---:|---:|---:|---:|
| base | 14.3% | 3/10 | 0.63 s | 0.4 s | baseline 192 MB |
| small | **12.4%** | 3/10 | **2.02 s** | 1.16 s | **+~210 MB** |

Interpretation: `small` buys ~1.9 WER points for **3.2x latency** and a much larger install. That is a poor default trade for dictation.

### 4.2 Startup and self-test

| Probe | Result |
|---|---|
| Import time | 0.97 s |
| App construction | 0.91 s |
| Time to ACTIVE (headless source) | ~1.9 s |
| `--self-test` wall time | 4.2 s |
| First self-test transcription | 2.17 s for a 143,764-byte SAPI buffer |

The self-test is much faster than the 33.6 s figure in older release notes. The difference is likely hardware and warm caches; it should not be quoted as a stable benchmark without context.

### 4.3 Idle runtime

Measured on the installed `dist\FlowPilot\FlowPilot.exe` (PID 11072) and on a headless source instance.

| Metric | Result |
|---|---|
| Idle CPU, installed build | 9.1–13.4% of one core across 10 s samples |
| Idle CPU, headless source | ~10.9–11.4% of one core |
| Idle RSS, headless source | 272 MB |
| Threads, installed build | 44 |
| Microphone | Pre-roll stream open and monitoring while idle |
| Reduced-motion run | **11.41–11.56% CPU — no reduction** |

**Important correction:** the 30 FPS HUD timer was initially suspected as the dominant cause. The reduced-motion experiment did not lower CPU, so that attribution is **not proven**. Profile before changing timers.

### 4.4 Packaging

| Artifact | Size |
|---|---:|
| `FlowPilot-Setup-v3.1.0.exe` | 692,934,347 B (660.8 MB) |
| `FlowPilot-v3.1.0-RC13-windows-x64.zip` | 772,606,872 B (736.8 MB) |
| Unpacked `dist\FlowPilot\_internal` | 1,032.1 MB |
| `models/faster-whisper-base` | ~141 MB |
| `models/faster-whisper-small` | ~464 MB |
| `FlowPilot.exe` | 25.4 MB |

The two models are ~605 MB of the payload. `small` alone is roughly 60% of the download for a 1.9-point English WER gain.

`FlowPilot.exe` Authenticode status: **NotSigned**. Embedded ProductVersion/CompanyName: absent.

### 4.5 Test suite

| Run | Result |
|---|---|
| Full Python suite | **59/60 suites passed**, 0 skipped, 186.6 s |
| Failed suite | `tests/test_text_injector.py` |
| Failure text | `Notepad did not expose an editable document for flowpilot-audit-ftdx6a3a.txt; observed=[], launcher_exit=None.` |
| Standalone reruns | 5/5 passed |
| `npm test` | Passed |
| `--self-test` | Passed |

The failure is consistent with a race in Notepad control discovery under full-suite load, not a reproducible injection defect. It still means the suite is not deterministic.

---

## 5. Findings

### F-01 — P0 — Unsigned installer with no version metadata

**Evidence**

- `Get-AuthenticodeSignature` on the built executable: `NotSigned`.
- The release asset is the same build (SHA-256 matches the published manifest).
- No `ProductVersion`, `CompanyName`, or `FileDescription` on `FlowPilot.exe`.

**Impact**

Windows SmartScreen will warn on first launch. For a privacy/security-positioned dictation tool, an unsigned 660 MB binary is the single largest conversion killer. Users cannot distinguish RC11 from RC13 in file properties.

**Proposed fix**

Use the existing signing path in `scripts/package_windows_release.py` (it already supports `--cert`, `--thumbprint`, `--subject`, timestamping, and fail-closed verification) with an Azure Trusted Signing or OV certificate. Add Inno `VersionInfo*` directives and a PyInstaller version resource.

**Acceptance**

`Get-AuthenticodeSignature` returns `Valid` for the executable and installer; Properties shows product/version/company; filename includes the RC suffix.

**Confidence:** High.

---

### F-02 — P0 — The release and update channel cannot surface RC13

**Evidence**

`engine/update_checker.py:15-17`:

```python
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "3.1.0"
```

`engine/update_checker.py:32-36` (nested inside `compare_versions`):

```python
def normalize(v: str):
    v = v.lstrip("v").strip()
    nums = [int(x) for x in re.findall(r"\d+", v)]
    is_rc = "-rc" in v.lower() or "rc" in v.lower()
    return (nums, 0 if is_rc else 1)
```

Three distinct failures:

1. **Discovery:** `/releases/latest` excludes pre-releases. GitHub returns v3.0.2, so RC13 is never fetched.
2. **Identity:** `CURRENT_VERSION` is `"3.1.0"`, omitting the RC suffix. The running app cannot tell RC11 from RC13.
3. **Ordering:** tuple comparison uses the numeric list first. `3.1.0-rc13` normalizes to `([3,1,0,13], 0)`, while `3.1.0` normalizes to `([3,1,0], 1)`. Because the RC list is longer, `3.1.0-rc13 > 3.1.0` — a pre-release sorts above its own stable release. The `is_rc` flag only breaks ties when the numeric lists are equal, which they rarely are.

**Impact**

No user can be notified of RC13. An RC13 user will never be told that a future 3.1.0 stable exists. If pre-releases are enabled naively, stable users will be pushed onto release candidates.

**Proposed fix**

- Use `/releases?per_page=20`, filter drafts, and select the highest eligible version for the configured channel (`stable` default, `prerelease` opt-in).
- Parse strict semver including `-rc.N`; order `rc.2 < rc.10 < 3.1.0 < 3.2.0`.
- Keep a separate Windows numeric file version (for example `3.1.0.13`) because Inno’s `VersionInfoVersion` requires a dotted numeric quad.
- Add unit tests covering RC ordering, channel filtering, legacy `3.1.0`, and malformed tags.

**Acceptance**

On `3.1.0-rc11` with channel `prerelease`, RC13 is offered. On `3.1.0-rc13`, RC13 is not offered. On stable `3.1.0`, RC13 is not offered. On stable `3.0.2`, the latest stable is offered.

**Confidence:** High.

---

### F-03 — P0 — Accuracy does not support “commercial parity”

**Evidence**

- English base WER: 14.3% (3/10 exact).
- German: 14.7%; Spanish: 19.9%; French: 23.2%.
- `small` improves English only to 12.4% at 3.2x latency.
- The project’s own v3.0.2 report records 15.66% raw WER / 12.01% strict cleaned WER, and 55.38% raw WER on the “Numbers & Dates” slice.
- `docs/scope/FLOWPILOT_GA_FINAL_CLOSURE_SCOPE.md` still frames the goal as parity with commercial dictation tools.

**Impact**

For dictation, 14% WER means roughly one error every seven words before post-processing. Proper nouns fail first, which is exactly where users notice. The privacy and zero-egress advantages are real, but they do not compensate for a visibly worse transcript.

**Proposed fix**

Do not swap models in this release. First measure correction time with 10 real users (errors per 100 words, seconds to fix). Then choose between:

- ship base-only and position as private/local;
- default to `small` and accept ~2 s latency;
- adopt a stronger CPU model for English while keeping Whisper for multilingual.

**Acceptance**

A written accuracy position with corpus, sample size, date, and product-level (post-processed) WER; no unqualified parity claim.

**Confidence:** High on the numbers; Medium on the best model path.

**Second-opinion qualification (Gemini, Q1):** treat the WER figures as *indicative* (N=10, ±5–8% margin). The proper-noun failure pattern is the reproducible core. Any accuracy claim requires post-processed WER through `WritingIntelligence.polish()` plus correction edit distance and time-to-accepted-delivery (Gate F, §6; §10.2).

---

### F-04 — P1 — Installer size is dominated by an optional model

**Evidence**

- Installer: 660.8 MB; zip: 736.8 MB; unpacked: 1,032 MB.
- Base model: ~141 MB; small model: ~464 MB.
- `flowpilot.spec:26-27` includes the entire `models/` directory.
- `installer/flowpilot_setup.iss:43` packages the whole bundle.

**Impact**

Download abandonment, slow updates, and a poor first impression. Most users will not benefit from `small` enough to justify 464 MB.

**Proposed fix**

Default build includes `models/faster-whisper-base` only. Offer `small` as an optional pack or an explicit, user-initiated, hash-verified download. Keep the zero-egress guarantee by making provisioning an explicit setup action.

**Acceptance**

Default installer <= 300 MB; clean install + `--self-test` passes with base only; selecting `small` without it installed produces a clear prompt, not a crash.

**Confidence:** High.

---

### F-05 — P1 — Idle CPU and memory are high for a tray utility

**Evidence**

- ~9–13% of one core while idle on the installed build.
- ~11% on a headless source run; 272 MB RSS; 44 threads.
- Microphone pre-roll stream remains open.
- Reduced-motion mode did **not** lower CPU (11.41–11.56%).

**Impact**

Battery drain, fan noise, and heat on a laptop. A dictation tool that costs a tenth of a core at rest contradicts the “lightweight local utility” positioning.

**Proposed fix**

Profile first (`py-spy` or `cProfile`) for 20 s idle. Then target the measured hot path among:

- `ui/floating_hud.py:164` — 30 FPS repaint while visible;
- `ui/companion_visibility_controller.py:36` — 350 ms context/media poll;
- `ui/workspace_home.py:138` — 750 ms dashboard refresh;
- `engine/audio_recorder.py:191` — always-open pre-roll stream.

Do not assume the HUD timer is the cause; the reduced-motion result contradicts that.

**Acceptance**

Idle CPU <= 2% of one core (3 x 10 s samples), RSS <= 300 MB, dictation p50 within +10% of 0.63 s.

**Confidence:** High on the measurement; Low on attribution until profiled.

---

### F-06 — P1 — Update check is not disclosed in the privacy policy

**Evidence**

- `engine/config.py:57` defaults `check_for_updates` to `True`.
- `engine/update_checker.py` calls `api.github.com`.
- `PRIVACY.md` does not describe this request, its cadence, or its payload.
- The settings checkbox says “on startup,” but the checker is throttled to once per 24 hours.

**Impact**

The product’s core promise is zero cloud egress during dictation. The check is outside dictation and carries only a version/user-agent, but an undisclosed network call in a privacy-first tool is a credibility problem.

**Proposed fix**

Disclose endpoint, cadence, payload, and opt-out in `PRIVACY.md`; correct the settings copy; consider a first-run notice. Keep the default on only if disclosed.

**Acceptance**

Every network call is documented; settings text matches actual behavior; a test asserts that no other egress exists outside the documented path.

**Confidence:** High.

---

### F-07 — P1 — The suite is 59/60 and CI does not gate the product

**Evidence**

- One failure in `tests/test_text_injector.py` under full-suite load; 5/5 standalone passes.
- No required status checks on `master`.
- No lint, typecheck, coverage, dependency lock, or installer smoke test.
- CI runs Python 3.12 only; local validation used 3.11.
- `hardware-tests.yml` is dead: no runner, no runs.

**Impact**

A flaky injection suite erodes trust in the one behavior the product cannot get wrong. Dead workflows create a false sense of coverage.

**Proposed fix**

Replace fixed sleeps with bounded polling in the Notepad test; require CI checks; add a Windows packaging smoke job (build, silent install, `--self-test`, uninstall); add a 3.11/3.12 matrix; pin dependencies; either fund a hardware runner or mark the workflow manual and stop advertising it.

**Acceptance**

Three consecutive full-suite runs green; a broken installer fails CI; the hardware workflow is either running or explicitly retired.

**Confidence:** High.

---

### F-08 — P2 — Documentation drift and a stale packaging command

**Evidence**

- `docs/scope/index.md:7` still says RC11.
- `docs/release/RELEASE_ARTIFACT_MANIFEST.md:5` stops at RC11; no RC12/RC13 entries.
- `ui/settings_dialog.py:327` and `:753` hardcode `v3.1.0`.
- `AGENTS.md` documents `python scripts/package_windows_release.py --version ...`, but the script accepts `--bundle`, `--archive`, and signing options — not `--version`.

**Impact**

Contributors and reviewers cannot tell which build is current. The documented release command fails.

**Proposed fix**

Make the version single-source; regenerate the manifest per release; correct the command block; scope benchmark claims to corpus and hardware.

**Acceptance**

No page calls RC11 current; the documented release command runs as written.

**Confidence:** High.

---

### F-09 — P2 — Repository hygiene and traction

**Evidence**

- No topics, code of conduct, or PR template; issue template not recognized by GitHub.
- 211/215 commits from a synthetic engineering identity.
- 5 stars, 1 fork, 0 issues, 18 views in 14 days; 1,543 clones likely automated.

**Impact**

Low discoverability and no external feedback loop. Two weeks of RC churn without a single user issue is a warning sign, not a compliment.

**Proposed fix**

Add topics, CoC, PR/issue templates; attribute commits to a human maintainer; recruit 5–10 pilot users and instrument correction time.

**Acceptance**

At least five external users complete a dictation session and report errors; issue tracker has real reports.

**Confidence:** High on the metrics; Medium on the causal story.

---

## 6. Proposed remediation plan

| Order | Workstream | Effort | Depends on | Change |
|---|---|---|---|---|
| 1 | Stabilize injector test; require CI checks; packaging smoke | S | — | unchanged |
| 2 | Single-source version; exe/installer metadata | S | — | unchanged |
| 3 | RC-aware update channel; tests | S–M | 2 | unchanged |
| 4 | Profile, then cut idle CPU | M | profiling | **moved up** — fix must be baked into the GA binary |
| 5 | Base-only installer | M | 2 | now follows the idle fix |
| 6 | Privacy disclosure + docs/claims reconciliation | S | 3, 5 | merged; must complete before Gate E |
| 7 | Sign executable and installer | S once cert exists | certificate | unchanged |

Reordered on Gemini's advice (§10.3): the idle fix ships inside the GA binary rather than after it, and privacy/docs sync happens once updater behavior and bundle contents are final.

### Gate criteria

- **Gate A (after 1):** 3 consecutive full-suite runs green; a deliberately broken installer fails CI.
- **Gate B (after 3):** mocked API tests prove stable/prerelease selection and RC ordering; settings shows the runtime version.
- **Gate C (after 4):** idle CPU <= 2% of one core; RSS <= 300 MB; dictation p50 within +10%.
- **Gate D (after 5):** installer <= 300 MB; clean-VM install and self-test pass.
- **Gate E (before publish):** Authenticode `Valid` on both artifacts; SHA-256 manifest; GitHub “Latest” points to the intended stable.
- **Gate F (before any accuracy claim):** post-processed WER through `polish()` on a stated corpus, plus correction edit distance and time-to-accepted-delivery from at least one real user session. Until Gate F passes, every WER figure in docs must be labeled "indicative (N=10)".

---

## 7. Decisions needed

1. **Certificate source.** Azure Trusted Signing, an OV/EV PFX, or a store certificate. The signing code already exists; only the credential is missing.
2. **Update default.** Keep automatic checks on with disclosure, or off by default. Recommendation: on, disclosed, with a first-run notice.
3. **Accuracy strategy.** Base-only plus a user pilot, `small` by default, or a model change. Recommendation: pilot first; do not swap models in this release.
4. **Small-model delivery.** Optional installer pack vs first-run download. Recommendation: optional pack for offline installs.
5. **Hardware CI.** Fund a self-hosted Windows runner, or retire the workflow and document manual hardware verification.

---

## 8. Questions for Gemini

1. Is 10 clips per language enough to support the P0 accuracy finding, or should the claim be softened to “indicative”?
2. Is raw-ASR WER the right metric for a product that post-processes every transcript? What would you measure instead?
3. Do you agree that distribution and trust outrank accuracy for this release, or is 14% WER disqualifying regardless of packaging?
4. Is the proposed semver/RC ordering and channel scheme correct? Identify any edge case that would still misorder releases.
5. Is the base-only installer safe given the multilingual positioning? What breaks when `small` is absent?
6. Is the idle-CPU measurement credible given the reduced-motion null result? What would you profile first?
7. Which finding in this document is weakest, and what evidence would settle it?
8. Would you ship RC13 as-is, ship a reduced GA, or hold? State the one condition that changes your answer.

**Answers and reconciliation:** §10.

---

## 9. Appendix

### A. Release metadata (GitHub API, 2026-10-31)

| Release | Type | Date | Asset downloads |
|---|---|---|---:|
| v3.0.2-release | stable / Latest | 2026-10-15 | 5 |
| v3.1.0-RC13 | pre-release | 2026-10-29 | 1–2 |
| v3.1.0-RC12 | pre-release | 2026-10-29 | — |
| v3.1.0-RC11 | pre-release | 2026-10-28 | — |
| v3.1.0-RC9 | pre-release | 2026-10-28 | — |
| v3.1.0-RC8 | pre-release | 2026-10-28 | — |
| v3.1.0-RC7 | pre-release | 2026-10-28 | — |
| v3.1.0-RC4 | pre-release | 2026-10-26 | — |

### B. Integrity

Published SHA-256 values match the local artifacts:

- Installer: `FA963C8347FAFC2FBC26100E479EFB1A52F864E3DBCE244B22E121C0F366A4E1`
- Zip: `350C971AEB7F288BA94FB5BF539FF3D6BEA8A36297F7F5F537D9D3AE9CC70E37`

### C. Key file references

| Area | File | Lines |
|---|---|---|
| Version | `engine/__init__.py` | 6 |
| Package metadata | `pyproject.toml` | 7 |
| Updater API/version | `engine/update_checker.py` | 15–17, 32–36, 41 |
| Update default | `engine/config.py` | 57 |
| Hardcoded version labels | `ui/settings_dialog.py` | 327, 753 |
| Installer version/output | `installer/flowpilot_setup.iss` | 6, 15, 23 |
| Model bundling | `flowpilot.spec` | 26–27 |
| HUD animation | `ui/floating_hud.py` | 159–166 |
| Visibility polling | `ui/companion_visibility_controller.py` | 35–37 |
| Dashboard refresh | `ui/workspace_home.py` | 137–138 |
| Pre-roll stream | `engine/audio_recorder.py` | 191 |
| Flaky injection test | `tests/test_text_injector.py` | — |
| Scope RC11 drift | `docs/scope/index.md` | 7 |
| Manifest RC11 drift | `docs/release/RELEASE_ARTIFACT_MANIFEST.md` | 5 |
| Stale release command | `AGENTS.md` | Commands section |

### D. Reproduction notes

1. Install dependencies from `requirements.txt`.
2. Run the suite: `python -X utf8 tests/run_all_tests.py`.
3. Run the self-test: `python desktop_app.py --self-test`.
4. Real-voice manifests:
   - `docs/evaluation/EN_HI_TA_ML_REAL_VOICE_MANIFEST.json` (30 items)
   - `docs/evaluation/DE_ES_FR_REAL_VOICE_MANIFEST.json`
   - `docs/evaluation/EN_REAL_VOICE_40_MANIFEST.json` (30/40 audio missing locally)
5. Benchmark parameters: model `base`, INT8, beam 1, VAD off, 8 CPU threads, 16 kHz audio.
6. WER is computed against `formatted_reference` with the repository’s normalization rules; hypotheses are raw ASR, not post-processed.

### E. Evidence gaps to close before the next review

- Post-processed WER (through `WritingIntelligence`) on the same clips.
- A clean-VM install/run/uninstall test of the signed installer.
- A profile trace that attributes idle CPU to a specific timer or callback.
- At least one real external user session with correction-time data.
- A 3.11 and 3.12 CI matrix result.

---

## 10. Second opinion (Gemini) and reconciliation — 2026-10-31

Gemini received the dossier above and returned the response below. Content is reproduced faithfully; line wrapping and ASCII tables were reformatted, and the bracketed note in Q5 is mine. The reconciliation in §10.2 records which of its claims were verified against the repository.

### 10.1 Gemini's response

**Overall:** the review is "remarkably incisive, rigorous, and grounded in real forensic measurements"; the diagnosis, methodology, and remediation plan are "sound, fair, and actionable."

**Per-finding assessment** — all nine findings upheld:

| Finding | Severity | Verdict | Rationale |
|---|---|---|---|
| F-01 Unsigned installer | P0 | Agree | An unsigned 660 MB executable triggers Windows SmartScreen blockades, destroying organic trial and adoption. |
| F-02 Release/update channel broken | P0 | Agree | Hardcoded v3.1.0 plus `/releases/latest` (skips pre-releases) plus buggy numeric-list comparison completely breaks in-app updates. |
| F-03 Accuracy vs parity claim | P0 | Agree with qualification | ~14.3% WER is expected for open-source base models; marketing it as commercial parity without qualifying it as private/offline is misleading. |
| F-04 Installer size | P1 | Agree | Bundling both models inflates the download by >3x for a 1.9-point English WER gain; `small` should be optional. |
| F-05 Idle CPU/memory | P1 | Agree | 11% continuous draw drains battery; the review correctly debunked the 30 FPS HUD timer as the sole culprit. |
| F-06 Undisclosed update check | P1 | Agree | Any outbound call violates the local-privacy expectation unless disclosed in `PRIVACY.md`. |
| F-07 Flaky test / ungated CI | P1 | Agree | Unbounded sleeps damage deployment confidence; `hardware-tests.yml` with 0 runners provides phantom safety. |
| F-08 Docs drift / stale command | P2 | Agree | `AGENTS.md` documents `--version` flags that do not exist in `package_windows_release.py`, causing manual release failures. |
| F-09 Synthetic maintainer identity | P2 | Agree | 211/215 commits from a synthetic bot email prevents human credibility. |

**Answers to the eight questions:**

- **Q1 (sample size):** Soften to "indicative." N=10 has ±5–8% margin of error; declaring a P0 blocker on 10 clips overreaches. The proper-noun failure pattern ("Kempton", "Beitar Illit") is 100% reproducible on base-sized models.
- **Q2 (metric):** Raw-ASR WER is the wrong metric — FlowPilot post-processes every transcript. Measure instead: (1) end-to-end post-processed normalized WER after `WritingIntelligence.polish()`; (2) correction edit distance between injected text and the final document text; (3) time-to-accepted-delivery (hotkey release to user's next keystroke).
- **Q3 (priority):** Distribution and trust completely outrank accuracy for this release. "A signed, 180MB, fast installer that delivers an 86% accurate transcript privately in 600ms is a viable product. An unsigned 660 MB installer flagged by SmartScreen that doesn't update and burns 11% CPU will never be tested by users."
- **Q4 (semver):** Proposed scheme correct; edge case is tag variants (`v3.1.0-RC13`, `v3.1.0-rc.13`, `-preview`). Remedy: use `packaging.version.Version` or SemVer 2.0 parsing where pre-releases have lower precedence than release versions.
- **Q5 (base-only):** Safe — "nothing breaks." Base is fully multilingual; claims `stt_engine` gracefully falls back to base when `small` is missing; installer drops 660 MB → ~220 MB. *(Fallback claim rejected — see §10.2.)*
- **Q6 (idle CPU):** Measurement credible; the reduced-motion null result is "extremely revealing" — rendering is not the primary culprit. Profile first: (1) the pre-roll PortAudio stream at 16 kHz waking every ~20 ms (estimated 5–10% of a core); (2) a Win32 hotkey hook or poll loop spinning.
- **Q7 (weakest finding):** F-05 attribution and F-03's N=10. Settle F-05 with a 20-second `py-spy` flamegraph while FlowPilot idles in the tray.
- **Q8 (ship decision):** **HOLD RC13 from promotion to "Latest."** Ship a reduced GA (v3.1.0) only after fixing F-01 (signed binaries/metadata), F-02 (update checker), and stripping `small` from the default installer. Promoting RC13 now would distribute an unsigned 660 MB binary with broken update mechanics that locks users out of future fixes.

**Plan validation:** sequence "largely correct, with one critical adjustment" — move Workstream 5 (idle CPU; #4 in the revised table) up so the fix is baked into the final binary; merge privacy/docs sync after repackaging; signing last.

**Claims to soften (as stated by Gemini):**

- In `FLOWPILOT_GA_FINAL_CLOSURE_SCOPE.md`: change "Full parity with commercial dictation platforms (Wispr Flow / Nuance)" → "Real-time, zero-cloud-egress local dictation optimized for developer workflows and privacy-conscious users." *(The quoted sentence does not exist as written — see §10.2.)*
- In `PRIVACY.md`: add explicit disclosure of the periodic, anonymous GitHub release query and the Settings opt-out.

### 10.2 Verification of Gemini's code-dependent claims

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | Docs say "Full parity with commercial dictation platforms (Wispr Flow / Nuance)" | **Rejected — quote not found** | Actual sentence is `docs/scope/FLOWPILOT_GA_FINAL_CLOSURE_SCOPE.md:12`: "…core parity with commercial dictation tools…". Softening still applies, but the real sentence is the one to edit. |
| 2 | Missing `small` gracefully falls back to base | **Rejected** | `engine/stt_engine.py:119` — `resolve_model_path` "Strictly matches the requested size to avoid returning base weights as small." Default config is `base`, so a base-only bundle is safe for default users; selecting an absent `small` requires a prompt/fallback we must *add* (F-04 acceptance criterion stands). |
| 3 | `WritingIntelligence.polish()` exists | **Confirmed** | `engine/writing_intelligence.py:296` |
| 4 | `packaging.version.Version` orders `v3.1.0-RC13` correctly | **Confirmed** | PEP 440 normalizes `-RC13` → `rc13` and orders pre-release < final; preferred over hand-rolled integer tuples in the F-02 fix. |

Base-only size arithmetic: 660.8 MB installer − ~464 MB `small` ≈ **~200 MB**, consistent with Gemini's ~220 MB estimate; Gate D's ≤300 MB acceptance still applies.

### 10.3 Adopted from the second opinion

- F-03 WER figures relabeled **indicative (N=10, ±5–8%)**; proper-noun failures retained as the reproducible qualitative finding (§5, F-03 qualification).
- Accuracy evidence bar recorded as **Gate F**: post-processed WER via `polish()`, correction edit distance, time-to-accepted-delivery (§6).
- Plan reordered: idle profiling/fix moved before installer repackaging so the fix ships in the GA binary; privacy/docs merged into step 6, gated by final updater behavior and bundle contents (§6 table).
- Ship condition: **HOLD** RC13 as "Latest"; reduced GA only after F-01 + F-02 + base-only bundle + idle fix + disclosure (§1).
- Version parsing remedy: prefer `packaging.version.Version` (or strict semver) over integer-tuple comparison (F-02 fix).

### 10.4 Rejected from the second opinion

- The base→small fallback claim — contradicted by `engine/stt_engine.py:119`; the fallback must be implemented, not assumed (§10.2, row 2).
- The unsupported parity quote — the real sentence is at `FLOWPILOT_GA_FINAL_CLOSURE_SCOPE.md:12` and is the one the docs workstream must soften (§10.2, row 1).

### 10.5 Current status

Second opinion complete and reconciled. The §6 plan (as reordered) and Gates A–F are authoritative. No code changes have been made; execution has not started.
