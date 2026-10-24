# FlowPilot

## Stack

- **Language / Runtime**: Python 3.10 or newer, targeted at 3.12, Windows first
- **Framework**: PySide6 (Qt6) desktop app, optional FastAPI web companion on 127.0.0.1
- **Key dependencies**: faster-whisper (CTranslate2 int8, CPU), sounddevice plus soundfile for capture, pywin32 plus pycaw for Windows audio, onnxruntime for Silero VAD
- **Package manager**: pip (requirements.txt; pyproject.toml holds metadata and a console script)

## Build approach

Journey, as recorded in `docs/scope/index.md`: complete and verify the Windows dictation and recovery path before adding breadth.

## Commands

```bash
# Install
pip install -r requirements.txt

# Run the app
python desktop_app.py

# Offline self test (Windows only, synthesizes speech through SAPI)
python desktop_app.py --self-test

# Full audit suite, 56 suites; release promotion also requires --require-all
python -X utf8 tests/run_all_tests.py

# One suite
python -X utf8 tests/test_writing_intelligence.py

# Build the desktop binary
python -m PyInstaller flowpilot.spec --noconfirm
```

## Specs

Stored in `docs/specs/` as `NNNN-title.md`. Companion visibility is in progress under spec 0001 and has a recorded RC3 live subset. Persistent microphone identity under spec 0002 and visible delivery observation under spec 0003 remain in progress. Historical RC2 did not include these features.

## Rules

- Zero cloud egress: dictation never leaves the device. Only loopback traffic exists (local LLM ports, the opt in server on 127.0.0.1).
- Truthful status: never report a paste as succeeded unless the target window was really verified; InjectionStatus wording drives the UI.
- External transform Replace and Revert are unavailable until a real revision and selection adapter exists; caller supplied labels do not authorize input. Scratchpad edits use VoiceEditor transactions.
- Windows first, cross platform adapters second: win32 code first, then pactl, osascript, or xdotool fallbacks.
- Stage env vars before importing engine modules; `engine/config.py` captures the config path at import time.
- Every subprocess call passes `encoding="utf-8", errors="replace"` and children run with `-X utf8`.
- Test isolation is env based: `FLOWPILOT_CONFIG_FILE`, `FLOWPILOT_CONFIG_DIR`, `FLOWPILOT_MUTEX_NAME`, `FLOWPILOT_HEADLESS`.
- Each module opens with a feature or PR numbered docstring header.
- Use `logging.getLogger("FlowPilot.<Module>")` in touched files; legacy code prints to stdout.

## Agent skills

- [audit](C:/Users/moham/.agents/skills/audit/): `jsmastery-pro/skills`, builds and keeps the project context current
- [scope](C:/Users/moham/.agents/skills/scope/): `jsmastery-pro/skills`, plans the next slice of work
- [architect](C:/Users/moham/.agents/skills/architect/): `jsmastery-pro/skills`, records load bearing decisions in docs/specs/
- [develop](C:/Users/moham/.agents/skills/develop/): `jsmastery-pro/skills`, builds a feature against its spec
- [check](C:/Users/moham/.agents/skills/check/): `jsmastery-pro/skills`, verify the real app and review code on a fresh model
- [test](C:/Users/moham/.agents/skills/test/): `jsmastery-pro/skills`, writes suites for recent changes
- [document](C:/Users/moham/.agents/skills/document/): `jsmastery-pro/skills`, writes PRs, changelogs, release notes from the real diff
- [sync](C:/Users/moham/.agents/skills/sync/): `jsmastery-pro/skills`, reconciles docs and spec status after changes
- [debug](C:/Users/moham/.agents/skills/debug/): `jsmastery-pro/skills`, finds and fixes root causes of broken behavior

## Context files

- [engine/AGENTS.md](engine/AGENTS.md): pipeline invariants, import time hazards, cross platform tiers
- [ui/AGENTS.md](ui/AGENTS.md): Qt windows, HUD behavior, companion stack, web shell
- [tests/AGENTS.md](tests/AGENTS.md): runner rules, env staging, two suite styles

_Drafted by /audit from the repo, worth a quick human pass. Edit freely: once a line stops matching this draft, later runs treat it as curated and will flag rather than overwrite it._
