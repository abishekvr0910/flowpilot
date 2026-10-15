# CODEX TASK: FULL-STACK DEVELOPER RESEARCH, REPO AUDIT, GITHUB RECONCILIATION & LOCAL NPM/WEB EVALUATION

## Mission Directive

Execute a comprehensive full-stack research, repository audit, GitHub reconciliation, and local npm/web stack evaluation for **FlowPilot**. Apply modern full-stack engineering standards across frontend, backend, desktop IPC, local web/WebSocket protocols, GitHub repository health, and npm integration opportunities.

> [!IMPORTANT]
> **Operational Boundary Mandate**:
> 1. Stable baseline `v3.0.2-release` at `b9bd763` on `master` must remain unchanged as the official rollback baseline.
> 2. Do not merge into `master`, move tags, or push to remote GitHub without explicit authorization.
> 3. Zero-cloud-egress privacy must be preserved: FlowPilot operates 100% locally with zero external network telemetry.

---

## 1. Project Context & Environment Baseline

- **Repository**: `https://github.com/abishekvr0910/flowpilot`
- **Active Working Branch**: `feature/developer-reliability-upgrade`
- **Current Rollback Baseline**: `refs/tags/v3.0.2-release` at commit `b9bd763`
- **Pilot Artifact**: `dist/FlowPilot-v3.1.0-pilot-win64.zip` (SHA-256: `4FD81150A5E404AB64C52B0C03BACB454D59DF6911BF0E23D3EABC363ED1B6FE`)
- **Host Runtime Stack**:
  - Python: 3.12 (Virtualenv: `hermes-agent`)
  - Node.js: `v24.15.0`
  - npm: `11.12.1`
  - Desktop GUI: PySide6 (Qt 6)
  - Core STT: Faster-Whisper (CTranslate2 + Silero VAD ONNX)
  - Web & IPC: FastAPI, Uvicorn, WebSockets

---

## 2. Phase 1 — GitHub Remote & Repository Audit

Investigate the remote GitHub repository and local Git workspace:

1. **Remote Repository Health & State**:
   - Inspect remote repository URL: `https://github.com/abishekvr0910/flowpilot.git`.
   - Verify commit divergence between `master` and `feature/developer-reliability-upgrade`.
   - Reconcile published GitHub release tags (`v2.0.0-release`, `v2.1.0-release`, `v3.0.0-release`, `v3.0.1-release`, `v3.0.2-release`) with local git refs.
   - Confirm checksums and artifact sizes of published GitHub releases against local `dist/` archives.
2. **Repository Governance & Documentation Audit**:
   - Audit `README.md`, `FLOWPILOT_V302_RELEASE_REPORT.md`, `SECURITY.md`, `PRIVACY.md`, `LICENSE`, and `pyproject.toml`.
   - Verify consistency of reported latency claims (p50 ~1.2s), supported languages, hotkeys (`Ctrl+Shift+Space`, `F9`), and privacy guarantees.
   - Inspect repository workflow files (`.github/workflows/`) for CI/CD, release automation, or linting definitions. Identify gaps where automated GitHub Actions could build, test, and release binaries.

---

## 3. Phase 2 — Local npm, Node.js & Web Architecture Research

Leverage full-stack developer skills to evaluate the web, WebSocket, and potential Node/npm client layers:

1. **Local Node.js & npm Diagnostic**:
   - Verify local Node.js (`v24.x`) and npm (`11.x`) environment and global/local packages.
   - Evaluate opportunities for an npm package (e.g. `@flowpilot/sdk`, `@flowpilot/client`, or web companion frontend).
2. **Backend Web & WebSocket Service Audit**:
   - Inspect `pyproject.toml` `[project.optional-dependencies] web`: `fastapi`, `uvicorn`, `websockets`, `requests`, `openai`.
   - Inspect existing REST endpoints and WebSocket protocols in `tests/test_api_and_websocket.py`.
   - Validate API behavior:
     - Health check endpoints (`/health` or `/status`).
     - Real-time transcription streaming via WebSockets.
     - Localhost security bindings (`127.0.0.1` only, CORS restrictions, zero public internet exposure).
3. **Full-Stack Companion UI Feasibility**:
   - Research blueprint for a lightweight modern web companion dashboard (Vite / React / Tailwind or lightweight Vanilla JS) served locally.
   - Evaluate capabilities: real-time audio visualizer, snippet editor, custom dictionary management, profile configuration, and latency telemetry graphs.

---

## 4. Phase 3 — Full-Stack Verification & Test Execution

Independently execute and verify the application across the complete test pyramid:

1. **Automated Regression Suite (Python)**:
   ```powershell
   python tests/run_all_tests.py
   ```
   - Verify all 24 test modules pass cleanly (Audio capture, Faster-Whisper, TextInjector, AudioDucker, API & WebSockets, Win32 Hotkeys, Desktop App, FactGuard v2, Session State Machine, and Zero Network Egress).
2. **End-to-End Specification Suite**:
   ```powershell
   python tests/test_final_specification_e2e.py
   ```
   - Verify all 18 end-to-end scenarios pass with physical text verification in target applications.
3. **Packaged Binary Smoke Test**:
   ```powershell
   python tests/test_standalone_binary_smoke.py
   ```
   - Verify packaged `dist/FlowPilot/FlowPilot.exe` launches without DLL missing errors, respects Win32 Single-Instance Mutex, resolves Silero VAD assets, and terminates cleanly.
4. **API & WebSocket Standalone Verification**:
   ```powershell
   python -m pytest tests/test_api_and_websocket.py -v
   ```
   - Confirm WebSocket framing, state broadcast, and error handling.
5. **Zero-Egress Security & Privacy Audit**:
   ```powershell
   python tests/test_network_egress.py
   ```
   - Confirm socket hooks detect zero outbound traffic to external IP addresses.

---

## 5. Phase 4 — Synthesis & Full-Stack Recommendation Report

Synthesize all findings into a structured report covering:
1. **GitHub Status & Alignment**: Remote vs local state, release artifact integrity, and CI/CD recommendations.
2. **Web & npm Opportunities**: Concrete blueprint for npm package / web companion interface, API contract specification, and local developer tooling.
3. **Test & Performance Scorecard**: Quantitative test results, memory footprint, cold-start latency, and transcription latency.
4. **Full-Stack Roadmap**: Prioritized next steps across desktop, web API, npm ecosystem, and packaging automation.

---

## Execution Command
To begin execution, trigger the audit against the workspace and report findings step-by-step.
