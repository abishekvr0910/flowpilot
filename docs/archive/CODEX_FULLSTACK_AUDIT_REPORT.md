# FlowPilot Full-Stack Audit and GitHub Reconciliation

> **Historical snapshot - superseded.** Retained for provenance only. Do not use this document as current instructions, test status, performance proof, legal/compliance advice, or up-to-date competitor information. See the [archive index](README.md) for current sources.

**Audit date:** 2026-10-15  
**Workspace:** `S:\APPs\New folder`  
**Audited branch:** `feature/developer-reliability-upgrade`; started at `b638c8d94cf33337bac29ff74cc17cf6adc0d9e5` and advanced during the audit to `cbdaa78a467699a3893f97e16b63b2a734b0af0b`  
**Rollback tag:** `v3.0.2-release` at `b9bd76396b2883fa2e87e8b131d231dc39c34515`  
**Audit mode:** Read-only product and repository audit. No merge, tag mutation, push, or release publication was performed.

## Executive verdict

FlowPilot has a credible Windows dictation engine and is suitable for a controlled pilot. It is not ready for an unqualified production release.

The main blocker is the **truth boundary between “input was sent” and “text is present in the intended application.”** The 18-scenario suite failed exactly at physical text confirmation: `TextInjector.inject()` returned success after dispatching paste keystrokes, but the expected text was absent from the Notepad buffer read by the test. The release documents describe confirmed injection, while the orchestration path does not invoke `verify_text_injected()` before marking the session successful.

The same pattern exists at repository level: documentation and release claims are ahead of the current gates. The host regression suite finished at 23/24, the physical specification suite stopped at Scenario 4, the remote repository has no workflows or branch protection, and the web API exposes sensitive configuration without a local authentication boundary.

**Release recommendation:** keep `v3.0.2-release` as the rollback baseline; treat `v3.1.0-pilot` as an internal pilot artifact; do not promote it until the P0 gates in this report pass.

## 1. Git and GitHub reconciliation

### Repository state

| Item | Observed state | Verdict |
|---|---|---|
| Public repository | `https://github.com/abishekvr0910/flowpilot` | Confirmed |
| Remote default branch | `master` at `ba5c93e1183edf1d89db7688fe1e8041ba228a13` | Confirmed |
| Local `master` | Same `ba5c93e` commit | Aligned |
| Rollback tag | `v3.0.2-release` at `b9bd763` | Preserved |
| Feature branch | Current `cbdaa78`, five commits ahead of current `master` | Local only; not present on remote |
| Master versus rollback tag | `master` is one documentation commit ahead of `v3.0.2-release` | Task specification wording was stale, tag itself is intact |
| Open issues / pull requests | 0 / 0 | Empty project history, not evidence of defect-free operation |
| Remote workflows | 0 | No CI or release automation on GitHub |
| Branch protection | Disabled | High governance risk |
| Latest `master` signature | Unsigned | Supply-chain hardening gap |

The audit began with the task files untracked at `b638c8d`. During execution, the branch advanced to local commit `cbdaa78` containing the npm orchestration, Node integration test, CI workflow, and task files. This audit did not create that commit. The tests and full-stack findings below describe the resulting `cbdaa78` workspace state.

The feature branch contains a proposed `.github/workflows/ci.yml`, but it has not been pushed. Its current design is not suitable for `windows-latest`: it runs microphone, CoreAudio, Notepad, and interactive desktop tests that require a real logged-in Windows session. The runner also contains `ensure_desktop_accessible()`, which attempts to kill `LockApp.exe`; a test harness must not manipulate workstation security processes.

### Tag reconciliation

All local tag objects match the remote refs:

| Tag | Remote/local tag ref | Dereferenced release commit |
|---|---|---|
| `v2.0.0-release` | `83744efe48d8e8815744c10f0caebb69876adb21` | `02c1241aa9b8810eb008f3df298ce1760930236d` |
| `v2.1.0-release` | `8c770abca00d9e2656984f0a78d995a92e60e10f` | `c0c7411d4a75a6ff50187344e0b2775e9fcb6f4b` |
| `v3.0.0-release` | `ce136e20945c20895be6da6930ddf21711b54fb4` | `ec118d2371fe3315d03e1cf381a860dab06ac1c4` |
| `v3.0.1-release` | `93cff43eb874432f301f724f69a325abc459ee73` | `5fd8e2fb640079ac66e6993554e4d21a18f3af03` |
| `v3.0.2-release` | `b9bd76396b2883fa2e87e8b131d231dc39c34515` | Lightweight tag; same commit |

Only `v3.0.2-release` is a published GitHub Release. The earlier four names are Git tags without published GitHub Release assets.

### Artifact integrity

| Local artifact | Bytes | SHA-256 | Remote comparison |
|---|---:|---|---|
| `FlowPilot-v2.0.0-win64.zip` | 248,773,290 | `C0CE8C5E39279C4C2598CCC29A321195C21046E9F0351994E0FCCE5504BD4734` | No published release asset |
| `FlowPilot-v2.1.0-win64.zip` | 248,774,062 | `F1F283945D122C213D416144BEC878F252D93C207FB204D5FF69D1CADF0292D3` | No published release asset |
| `FlowPilot-v3.0.0-win64.zip` | 252,221,573 | `DDA6FFB0CB8EA1821B2139D4F49FADAA07A03BCC9DF491163B3DC6682752814C` | No published release asset |
| `FlowPilot-v3.0.1-win64.zip` | 252,234,246 | `986C9CEEF4DE6F36A2198C90DB1EEAA39C907E907A24EBD0F2EE90CDDB7FC703` | No published release asset |
| `FlowPilot-v3.0.2-win64.zip` | 252,311,634 | `985E031C7AF2617E4C03138D1A00472607FF9F9E1D2CFF636827F26077F63F74` | Exact size and digest match to GitHub asset |
| `FlowPilot-v3.1.0-pilot-win64.zip` | 251,173,567 | `4FD81150A5E404AB64C52B0C03BACB454D59DF6911BF0E23D3EABC363ED1B6FE` | Matches task specification; not published |

The current unpacked `dist/FlowPilot` directory is 607,094,341 bytes (578.97 MiB). `FlowPilot.exe` itself is about 31.23 MiB, so documentation must distinguish executable size from complete installed footprint.

## 2. Documentation and claims audit

### Claims that are supported

- Default transcription mode is local Faster-Whisper.
- The core local dictation test opened no external sockets during the observed test window.
- `Ctrl+Shift+Space`, `Ctrl+Alt+Space`, and `F9` are registered through Win32 `RegisterHotKey`.
- The base model performed well on the current six-case synthetic SAPI benchmark.
- The published v3.0.2 asset size and SHA-256 are correct.

### Claims that need correction or tighter scope

1. **“Sub-second latency (~1.2s p50)” is self-contradictory.** A 1.2 second median is not sub-second. Current synthetic model inference was 744.9–933.1 ms for the base model, but that excludes capture finalization and application injection.
2. **Language coverage is inconsistent.** The UI claims “100+,” the release report says Whisper supports 99 languages, and FlowPilot's own registry provides explicit metadata for 18 core languages. State these as three separate scopes.
3. **F9 behavior depends on global mode.** With the default `hotkey_mode="toggle"`, F9 is also registered as a toggle. README and settings text describe F9 as push-to-talk without explaining that dependency.
4. **Zero-egress needs a precise boundary.** Local cached-model dictation passed the socket test. First-run model acquisition can access Hugging Face, cloud mode uploads audio, the companion page loads Google Fonts, and the web API returns cloud API keys to clients.
5. **“Transcripts immediately cleared/wiped” is not proven.** Python string and buffer dereferencing is not deterministic memory wiping.
6. **“Confirmed injection” is not enforced by the orchestration path.** The helper exists, but `inject()` returns true when keystrokes are dispatched and the orchestrator accepts that result without a physical buffer confirmation.
7. **The current release report is stale against the feature branch.** It states 20/20 and 18/18 with no defects; the current branch defines 24 regression modules and the fresh results are 23/24 plus an E2E failure at Scenario 4.

## 3. Runtime and test scorecard

### Environment

| Runtime | Task expectation | Observed |
|---|---|---|
| Python | 3.12 | 3.11.15 in Hermes virtual environment |
| Node.js | v24.15.0 | v24.15.0 |
| npm | 11.12.1 | 11.12.1 |

### Executed tests

| Test command | Result | Evidence / limitation |
|---|---|---|
| `python tests/run_all_tests.py` | **FAIL** before summary | CP1252 console crashed while printing U+FFFD from device name |
| `python -X utf8 tests/run_all_tests.py` in sandbox | 15/24 | Expected sandbox restrictions blocked mic, GUI, profile, and temp writes |
| Same command with physical host access | **23/24** in 66.88s | Only Silero duplicate asset path failed |
| `python -X utf8 tests/test_final_specification_e2e.py` | **FAIL** | Scenarios 1–3 passed; Scenario 4 failed physical Notepad buffer assertion; 5–18 did not run |
| `python -X utf8 tests/test_standalone_binary_smoke.py` | **PASS** | Launch, 318.27 MiB resident RAM, mutex, assets, termination |
| `python -X utf8 -m pytest tests/test_api_and_websocket.py -v` | **PASS** | 1 test; five dependency deprecation warnings |
| `python -X utf8 tests/test_network_egress.py` | **PASS** | Zero external sockets observed; captured clip produced empty transcript |
| `npm test` | **PASS** | Static assets, config API, and WebSocket handshake tested; stop stage accepted an `audio_level` event as success |
| `npm pack --dry-run --json` | **PASS, package shape rejected** | 116 files, 1.30 MB tarball, entire Python app and ONNX models included |

### Current synthetic benchmark

Fresh SAPI benchmark, CPU INT8, 8 threads:

| Model | Process RAM after load | STT latency range | Result summary |
|---|---:|---:|---|
| tiny | 179.98 MiB | 382.8–452.9 ms | 30.8% WER on developer jargon; unsuitable default |
| base | 272.61 MiB | 743.6–931.1 ms | 0% WER/CER on all six current synthetic cases |

These six deterministic voices are regression fixtures, not field accuracy. They do not validate diverse human accents, rooms, microphones, or conversational cadence.

### Test quality findings

- The 24-module suite is valuable as a host acceptance suite, but mixes deterministic unit tests with physical hardware and GUI tests.
- `test_silero_vad_resolution.py` requires assets in three locations. The production binary smoke test passes with `_internal/faster_whisper/assets`, so either the build is missing the promised duplicate or the regression contract is obsolete. Resolve the contract rather than skipping it.
- The E2E suite is fail-fast and lacks guaranteed Notepad cleanup after assertion failure.
- `read_window_buffer()` uses global Ctrl+A/Ctrl+C and changes the user's selection/cursor. It also targets a top-level HWND and is unreliable with modern Notepad child controls.
- `run_all_tests.py` can kill `LockApp.exe`. Remove this behavior.
- The Node test calls the WebSocket lifecycle verified after receiving any message following stop; in this run that message was `audio_level`, so finalization was not actually verified.
- The API test verifies happy-path framing but not malformed messages, unauthorized origins, disconnect cleanup, concurrent clients, schema rejection, or secret redaction.

## 4. Web and WebSocket architecture audit

### Current protocol

REST endpoints:

- `GET /api/config`
- `POST /api/config`
- `POST /api/toggle`
- `GET /api/history`
- `DELETE /api/history`

WebSocket endpoint:

- `/ws` accepts `toggle`, `start`, and `stop` actions.
- It broadcasts state and RMS audio-level events.
- It does **not** implement partial or real-time transcription streaming.

### Critical web gaps

1. There is no `/health`, `/status`, or versioned `/api/v1` contract.
2. Requests and WebSocket commands use unvalidated dictionaries rather than strict Pydantic message schemas.
3. `GET /api/config`, POST responses, and the initial WebSocket frame expose the full config, including Groq/OpenAI keys.
4. CORS uses wildcard origins, methods, and headers with credentials enabled. FastAPI's documentation explicitly requires concrete values when credentials are enabled and recommends explicit origins.
5. WebSocket connections have no token, origin validation, permission scope, rate limit, message size limit, or command acknowledgement.
6. The service prints a localhost URL, and supplied launch/test commands bind to `127.0.0.1`, but the ASGI application itself does not enforce loopback deployment.
7. The UI loads fonts from Google and therefore is not a zero-egress web companion.
8. Several UI fields use `innerHTML` with user-controlled vocabulary or metadata, creating a local stored DOM-injection surface.
9. FastAPI startup uses deprecated `@app.on_event("startup")`; use lifespan handling.
10. The browser can overwrite the entire config object. Use allow-listed PATCH models and write-only secret endpoints.

FastAPI documents explicit origin lists for credentialed CORS and supports dependencies/security on WebSocket endpoints:

- <https://fastapi.tiangolo.com/tutorial/cors/>
- <https://fastapi.tiangolo.com/advanced/websockets/>

## 5. npm assessment

The existing `package.json` is a task runner, not a usable SDK package.

- `main` points at `ui/app.js`, which accesses `document` at import time. A Node import fails with `ReferenceError: document is not defined`.
- There is no exported `FlowPilotClient`, no TypeScript declarations, no `exports` map, and no runtime schema.
- No `files` allow-list or `.npmignore` exists. npm therefore packed 116 repository files, including Python source, audits, tests, and ONNX assets.
- There is no local dependency graph or lockfile for a frontend build.
- The unscoped package name `flowpilot` is already owned on npm by an unrelated Jira/GitLab tool (`1.2.0`). `@flowpilot/sdk` is also occupied. `@flowpilot/client` was not publicly found, but the `@flowpilot` scope appears to belong to another project.

npm documents that omission of `files` defaults to including nearly everything and that `exports` defines and encapsulates a package's public entrypoints: <https://docs.npmjs.com/cli/v11/configuring-npm/package-json/>

### Recommended package boundary

Use a scope controlled by this project, for example `@flowpilot-local/client`, only after ownership is secured.

The package should contain:

- `FlowPilotClient` with REST and WebSocket transports;
- generated TypeScript types for settings, commands, state events, metrics, and errors;
- reconnect with exponential backoff and monotonically increasing event sequence handling;
- abort signals and request timeouts;
- no Python binaries, models, UI source, or secret storage;
- `exports` for browser and Node ESM, plus `.d.ts` declarations;
- a strict `files` allow-list and `private: true` until publication is intentional.

## 6. Recommended local companion architecture

Keep the Python desktop process as the single owner of microphone, session state, speech inference, and Win32 injection.

```text
PySide6 desktop / FlowOrchestrator
          |
          | typed internal events
          v
FastAPI loopback gateway (127.0.0.1 only)
          |
          +-- REST /api/v1: health, settings, dictionary, snippets, metrics
          |
          +-- WS /api/v1/events: state, levels, final transcript, timings, errors
          |
          v
@flowpilot-local/client
          |
          v
Vite + React + TypeScript companion UI (all assets bundled locally)
```

### Minimum API contract

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Version, readiness, model loaded, active session; never secrets |
| GET | `/api/v1/settings` | Redacted, allow-listed settings |
| PATCH | `/api/v1/settings` | Validated partial update with field constraints |
| PUT | `/api/v1/secrets/{provider}` | Write-only API-key update; never returned |
| GET/POST/DELETE | `/api/v1/dictionary` | Personal vocabulary management |
| GET/POST/DELETE | `/api/v1/snippets` | Snippet management |
| GET | `/api/v1/metrics/sessions` | Local stage timings and success rates without text |
| POST | `/api/v1/dictation/start` | Start with idempotency/session guard |
| POST | `/api/v1/dictation/stop` | Stop current session |
| POST | `/api/v1/dictation/cancel` | Cancel current session |
| WS | `/api/v1/events` | Versioned event stream |

Use an event envelope such as:

```json
{
  "version": 1,
  "sequence": 42,
  "type": "pipeline.metrics",
  "session_id": "uuid",
  "timestamp": "2026-10-15T01:20:30.000Z",
  "payload": {
    "state": "SUCCESS",
    "stt_ms": 775.7,
    "injection_ms": 31.2,
    "injection_confirmed": true
  }
}
```

### Local security boundary

- Generate a random session token at server start and require it for mutating REST calls and the WebSocket handshake.
- Validate `Host` and WebSocket `Origin`; accept only the bundled companion origin.
- Bind explicitly to `127.0.0.1`, reject proxy forwarding by default, and fail startup if configured for a non-loopback host without an explicit unsafe-development flag.
- Redact secrets in every response and log.
- Set request and frame size limits.
- Use strict Pydantic request and event models with unknown fields rejected.
- Bundle fonts, icons, chart code, and all frontend assets locally.
- Prefer Windows Credential Manager for cloud keys; do not store them in plaintext config JSON.

### UI recommendation

Use Vite + React + TypeScript for the companion because the page now has several synchronized domains: session state, settings, dictionaries, snippets, history policy, and telemetry charts. Vite supports a React TypeScript template and production bundling; it transpiles TypeScript but type checking must remain a separate CI command. See <https://vite.dev/guide/> and <https://vite.dev/guide/features.html>.

Do not add Tailwind initially. The existing CSS can be migrated into local design tokens and CSS modules with less churn. Add a small bundled chart library only when real pilot timing data exists.

Recommended first screens:

1. **Live session:** state, RMS visualizer, target app, confirmed insertion result.
2. **Dictionary and snippets:** validated CRUD with import/export preview.
3. **Profiles:** per-application mode and terminology overrides.
4. **Local performance:** p50/p95 STT and injection timings, failure rate, no raw text by default.
5. **Privacy:** active engine, network mode, history/telemetry state, model availability.

Do not stream microphone audio to the browser for the visualizer. Broadcast normalized RMS/peak samples already computed by the engine.

## 7. Architecture scorecard

| Area | Score | Reason |
|---|---:|---|
| Native desktop core | 8/10 | Good separation, state machine, local inference, and Win32 integration |
| Speech and writing pipeline | 8/10 | Strong deterministic synthetic performance; human field evidence still missing |
| Injection reliability | 5/10 | Physical confirmation failed and is not required before success |
| Privacy engineering | 6/10 | Local default is sound; claims and web/cloud boundaries need correction |
| Web/API | 3/10 | Functional prototype with weak schemas, secret exposure, and no local auth |
| Companion UI | 4/10 | Useful prototype, but stale claims, external fonts, and DOM injection risks |
| npm ecosystem | 2/10 | Task runner masquerading as package; name, entrypoint, and contents are wrong |
| Test engineering | 6/10 | Broad physical coverage; mixed tiers, unsafe harness behavior, and red gates |
| CI/CD and release governance | 2/10 | Nothing active remotely; master unprotected; proposed CI is not runner-compatible |
| Documentation truthfulness | 5/10 | Much improved, but still overstates injection, latency, language, and zero-egress scope |

**Overall:** 5.3/10 as a production system; 7/10 as a promising controlled pilot.

## 8. Prioritized roadmap

### P0 — release blockers

1. **Make injection confirmation authoritative.** Return a structured result (`sent`, `confirmed`, `method`, `target`, `error`) and allow `SUCCESS` only when content is confirmed or the target integration provides a reliable acknowledgement. Use UI Automation/TextPattern or application-specific adapters for modern editors; keep manual clipboard recovery as a distinct outcome.
2. **Fix and repeat the physical specification suite.** Guarantee cleanup, create a unique empty document, resolve the actual editor child control, and run all 18 scenarios after Scenario 4 is fixed.
3. **Resolve the Silero packaging contract.** Either restore `dist/FlowPilot/assets` as promised or change the test/spec to require only supported runtime locations. Rebuild and hash the artifact afterward.
4. **Secure or disable the web service.** Redact keys, add strict schemas and local authentication, restrict origins, remove Google Fonts, and add health/version endpoints.
5. **Correct public claims.** Fix “sub-second ~1.2s,” 99 versus 100+ versus 18 languages, F9 mode behavior, memory wiping, installed size, and cached-model/optional-cloud boundaries.

### P1 — reliable engineering system

1. Split tests into deterministic CI, packaged smoke, and self-hosted Windows hardware suites.
2. Remove `LockApp.exe` termination and all user-session destructive behavior from tests.
3. Add GitHub Actions for lint/type/unit tests on hosted runners and a manual/nightly self-hosted workflow for mic, CoreAudio, Notepad, and cross-app injection.
4. Require pull requests, status checks, signed release tags, protected `master`, least-privilege workflow permissions, and immutable release checksums.
5. Add API protocol tests for invalid payloads, origins, auth, disconnects, ordering, concurrent clients, secret redaction, and cancellation.
6. Replace FastAPI startup events and WebSocket legacy APIs before their deprecations become removals.

### P2 — companion and ecosystem

1. Implement the versioned local gateway and generated `@flowpilot-local/client` types.
2. Build the Vite/React/TypeScript companion with fully local assets.
3. Add telemetry charts only for opt-in local metrics and label synthetic versus human measurements.
4. Publish an npm package only after its import contract, ownership, contents, types, tests, and semver policy are stable.
5. Run the planned 10-user pilot and use confirmed insertion rate, correction rate, p50/p95 end-to-end latency, and weekly retention as the promotion gates.

## 9. Reproducible commands

```powershell
git ls-remote --heads --tags origin
git rev-list --left-right --count master...feature/developer-reliability-upgrade
Get-FileHash -Algorithm SHA256 dist\*.zip

python -X utf8 tests/run_all_tests.py
python -X utf8 tests/test_final_specification_e2e.py
python -X utf8 tests/test_standalone_binary_smoke.py
python -X utf8 -m pytest tests/test_api_and_websocket.py -v
python -X utf8 tests/test_network_egress.py
python -X utf8 tests/test_model_benchmarks_extended.py

node --version
npm --version
npm test
npm pack --dry-run --json
```

## Final release gate

FlowPilot should be promoted beyond pilot only when all of the following are true in one traceable build:

- 24/24 deterministic and host acceptance modules pass under their intended runners;
- 18/18 physical specification scenarios pass, including actual target-buffer confirmation;
- Notepad, Chromium input, VS Code, and one Office-style editor pass repeated confirmed injection;
- the packaged artifact passes smoke, is signed, has an SBOM, and its published digest matches the locally tested archive;
- the remote branch is protected and required CI is green;
- web mode cannot disclose secrets or accept commands from an untrusted local origin;
- claims in README, privacy policy, release notes, and UI match the measured evidence.
