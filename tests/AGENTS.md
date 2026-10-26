# Tests

## Overview

Fifty nine standalone suites, listed in `tests/run_all_tests.py`, run sequentially as child processes; the runner judges return codes plus skip markers. Suites double as offline audit scripts, so each file can also run on its own without pytest. Release verification uses `--require-all` and rejects skipped suites.

## Key files

| File | Owns |
|---|---|
| run_all_tests.py | The ordered runner, current suite list, verdict logic |
| test_network_egress.py | Refuses every non loopback socket call; the zero egress invariant |
| test_notepad_dictation_e2e.py, notepad_harness.py | Real Notepad injection with ctypes GUITHREADINFO plumbing |
| test_standalone_binary_smoke.py | Packaged binary smoke test through `FLOWPILOT_TEST_EXE` |
| test_orchestrator_state_machine.py | Nine state loop coverage and robustness |
| test_writing_intelligence.py, test_factguard_*.py | FactGuard polishing and adversarial guardrails |
| test_api_and_websocket.py | Local API and WebSocket protocol with its own env staging |
| test_final_specification_e2e.py | The broad 18 scenario end to end specification |

## Commands

```bash
# Full suite, about 7 minutes
python -X utf8 tests/run_all_tests.py

# One suite, pytest not needed
python -X utf8 tests/test_orchestrator_state_machine.py

# pytest alternative, honors pyproject testpaths
pytest tests/test_factguard_v2.py -q
```

## Conventions

- Each suite bootstraps its own `sys.path.insert` of the project root at the top; keep that line when adding files.
- Two accepted styles coexist: pytest suites with fixtures and monkeypatch, and older audit scripts that print and `return False`. Prefer pytest for new suites.
- Stage test env before importing engine modules: `FLOWPILOT_CONFIG_FILE`, `FLOWPILOT_CONFIG_DIR`, `FLOWPILOT_MUTEX_NAME`, `FLOWPILOT_HEADLESS`, `FLOWPILOT_NO_POPUP`.
- Suites that spin the whole app use a unique mutex name per PID, see `test_standalone_binary_smoke.py`.
- The packaged smoke test uses an isolated config by default. Only `FLOWPILOT_SMOKE_USE_CALLER_PROFILE=1` lets a profile migration test select its own temporary profile.
- Transform unit tests mock clipboard and physical input boundaries. They must not overwrite the user's actual clipboard to test an aborted operation.

## Gotchas

- Notepad and SAPI suites launch real Windows processes and need desktop access; they skip silently when the desktop test cannot be held, never schedule them in parallel.
- The physical state machine suite skips honestly when no default microphone exists. The API protocol suite uses a declared virtual input and sends a known frame through the recorder callback.
- The Node integration test launches `tests/virtual_api_server.py` with virtual microphone and hotkey boundaries. This exercises REST and WebSocket transitions on CI without weakening production missing-device refusal.
- `test_network_egress.py` monkeypatches socket `sendto`, `connect`, and `getaddrinfo`; any new network call in engine code shows up as a failure here. Keep it green.
- `test_silero_vad_resolution.py` falls back to a `C:\Temp` path; it assumes a writable temp directory.
- Never import `engine.server` in a suite without staging env first; it instantiates a full orchestrator at import.
- pytest ignores `DeprecationWarning` globally through pyproject, so quieter future breakage surfaces late by design.

## Related specs

Audio identity tests follow [spec 0002](../docs/specs/0002-persistent-audio-input-identity.md). The delivery observer tests follow [spec 0003](../docs/specs/0003-visible-delivery-benchmark-observer.md).
