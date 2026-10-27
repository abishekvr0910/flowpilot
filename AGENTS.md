# FlowPilot

## Stack

- **Language / Runtime**: Python 3.10 or newer, targeted at 3.12 (64-bit), Windows-first
- **Framework**: PySide6 (Qt6) desktop app, optional FastAPI web companion on 127.0.0.1
- **Key dependencies**: faster-whisper (CTranslate2 int8, CPU), sounddevice plus soundfile for capture, pywin32 plus pycaw for Windows audio, onnxruntime for Silero VAD
- **Package manager**: pip (`requirements.txt`; `pyproject.toml` holds metadata and a console script)

## Build approach

Journey, as recorded in `docs/scope/index.md`: complete and verify the Windows dictation, text injection, and recovery path before adding breadth.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run desktop application
python desktop_app.py

# Offline self-test (Windows only, synthesizes speech through SAPI and decodes on CPU)
python desktop_app.py --self-test

# Full audit suite, 60 suites; release promotion also requires --require-all
python -X utf8 tests/run_all_tests.py

# Run single suite
python -X utf8 tests/test_writing_intelligence.py

# Build the desktop binary
python -m PyInstaller flowpilot.spec --noconfirm

# Package release archive with Authenticode signing and checksum manifests
python scripts/package_windows_release.py --version v3.1.0-RC8
```

## Specifications

Stored in `docs/specs/` as `NNNN-title.md`:
- `0001-context-aware-companion-visibility.md`: Context-aware companion display policy.
- `0002-persistent-audio-input-identity.md`: Persistent audio device selection and USB hot-plug guard.
- `0003-visible-delivery-benchmark-observer.md`: High-precision visible text delivery observation.
- `0004-local-text-repair-sandbox.md`: Local SLM text repair, slot-locking, and FactGuard veto protocol.

## Core Invariants

- **Zero cloud egress during dictation:** Audio, tensors, and transcripts strictly stay on the host device. The optional integration API uses loopback `127.0.0.1`. Model provisioning is an explicit, user-initiated HTTPS setup action and must never trigger implicitly during dictation.
- **Truthful status reporting:** Never report a paste as `CONFIRMED` unless the target window buffer was verified via Win32 `WM_GETTEXT` or UI Automation `IUIAutomationValuePattern`; `InjectionStatus` wording drives the UI.
- **External transform safety:** External Replace and Revert are unavailable until a real revision and selection adapter exists; caller-supplied labels do not authorize input. Scratchpad edits use `VoiceEditor` transactions.
- **Windows first, cross-platform adapters second:** Native Win32 code first, followed by pactl, osascript, or xdotool fallbacks behind guarded imports.
- **Target window focus safety:** Floating HUD windows must strictly maintain `WS_EX_NOACTIVATE (0x08000000)` and `Qt.WindowDoesNotAcceptFocus` so they never steal keyboard focus. Terminal injections must use dual-mode (`KEYEVENTF_UNICODE` typing or `Shift+Insert` paste).
- **Environment isolation:** Stage environment variables before importing engine modules; `engine/config.py` captures the config path at import time. Test isolation uses `FLOWPILOT_CONFIG_FILE`, `FLOWPILOT_CONFIG_DIR`, `FLOWPILOT_MUTEX_NAME`, and `FLOWPILOT_HEADLESS`.
- **UTF-8 child processes:** Every subprocess call passes `encoding="utf-8", errors="replace"` and children run with `-X utf8`.
- **Deterministic FactGuard:** `ContextProcessor` and `WritingIntelligence` must strictly preserve numbers, currency, dates, technical tokens, and negations (`not`, `never`) without hallucination.
- **Logging convention:** Use `logging.getLogger("FlowPilot.<Module>")` in new and touched modules; legacy code prints to stdout.

## Context Files

- [engine/AGENTS.md](engine/AGENTS.md): Pipeline invariants, module responsibilities, import-time hazards, and cross-platform tiers.
- [ui/AGENTS.md](ui/AGENTS.md): Qt window hierarchy, HUD non-activating behavior, companion stack, and web shell.
- [tests/AGENTS.md](tests/AGENTS.md): 60-suite runner rules, environment staging, and testing conventions.
