# Contributing to FlowPilot

Thank you for your interest in improving FlowPilot! We welcome contributions from developers, designers, accessibility advocates, and voice interface enthusiasts.

FlowPilot is an offline-first, local voice workstation for Windows designed for developers and privacy-conscious professionals. Our core architectural commitment is **zero cloud data egress during dictation**: speech capture, recognition, and writing intelligence execute entirely on-device.

---

## 🛠️ Development Setup

### Prerequisites
- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **Runtime:** Python 3.10, 3.11, or 3.12 (64-bit)
- **Version Control:** Git
- **Hardware:** Functional microphone (USB headset or built-in array)

### Setting Up the Environment

```powershell
# 1. Clone the repository
git clone https://github.com/abishekvr0910/flowpilot.git
cd flowpilot

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🧪 Running Test Suites

FlowPilot enforces strict regression, specification, and safety testing. All code changes must pass the full audit suite before merging.

### 1. Master Automated Audit Suite (59 Suites)
Runs all standalone regression suites sequentially as isolated subprocesses, covering VAD, CTranslate2 speech recognition, FactGuard preservation, Win32 hotkeys, network egress, and text injection:
```powershell
python -X utf8 tests/run_all_tests.py
```
> [!NOTE]
> Release promotion requires passing all suites without interactive skips:
> `python -X utf8 tests/run_all_tests.py --require-all`

### 2. Single Suite Execution
You can run any individual test suite directly with Python or pytest:
```powershell
python -X utf8 tests/test_writing_intelligence.py
# or via pytest:
python -X utf8 -m pytest tests/test_writing_intelligence.py -q
```

### 3. Offline Acoustic Self-Test
Synthesizes speech on Windows via SAPI and verifies local Faster-Whisper CPU decoding without internet access:
```powershell
python desktop_app.py --self-test
```

### 4. Zero Cloud Egress Verification
Ensures that all non-loopback network calls are strictly blocked and that audio/transcripts never leave the host:
```powershell
python -X utf8 tests/test_network_egress.py
```

### 5. Packaged Standalone Binary Smoke Test
Verifies PyInstaller packaging, single-instance mutex handling, and bundled asset integrity:
```powershell
python -X utf8 tests/test_standalone_binary_smoke.py
```

---

## 📐 Architecture & Coding Guidelines

Every contribution must honor FlowPilot's architectural invariants:

### 1. Zero Cloud Egress Invariant
- **Rule:** Audio capture, tensor conversion, transcription, and text formatting must execute 100% on-device (`127.0.0.1` loopback only).
- **Rule:** Never introduce third-party analytics, remote crash telemetry, or cloud AI endpoints into the dictation pipeline.
- **Rule:** Model provisioning must be an explicit, user-initiated HTTPS setup action (via `engine/model_downloader.py`) and must never be triggered implicitly from the dictation loop.

### 2. Truthful Status Invariant
- **Rule:** Never report an injection as `CONFIRMED` unless physically verified in the target application buffer via Win32 `WM_GETTEXT` or UI Automation `IUIAutomationValuePattern`.
- **Rule:** The `InjectionStatus` enum drives all UI feedback. If a target is unreadable or elevated, report `UNVERIFIED_DISPATCH` or `SAFE_REFUSAL` honestly.

### 3. Target Window & Clipboard Safety
- **Rule:** Floating HUD windows must strictly maintain `WS_EX_NOACTIVATE (0x08000000)` and `Qt.WindowDoesNotAcceptFocus` so they never steal keyboard focus from the user's active window.
- **Rule:** When injecting into terminals (`cmd.exe`, `powershell.exe`, `WindowsTerminal.exe`), use dual-mode injection (`KEYEVENTF_UNICODE` typing or `Shift+Insert` paste) to avoid shell clipboard collisions.
- **Rule:** Always preserve prior user clipboard contents. In slow applications (Notion, Slack, Obsidian), respect the dynamic paste delay before restoring the user's prior clipboard.

### 4. Deterministic FactGuard Preservation
- **Rule:** Any changes to `ContextProcessor` or `WritingIntelligence` must strictly preserve numbers, currency, dates, technical tokens, and negations (`not`, `never`) without hallucination or truncation.

### 5. Subprocess & Encoding Invariant
- **Rule:** Every `subprocess` call must pass `encoding="utf-8", errors="replace"` and child processes must run with `-X utf8`.
- **Rule:** Use `logging.getLogger("FlowPilot.<Module>")` in new or touched modules.

---

## 📦 Building the Standalone Package

To package FlowPilot into a standalone Windows distribution:

```powershell
# 1. Compile with PyInstaller
python -m PyInstaller flowpilot.spec --noconfirm

# 2. Package into release ZIP with SHA-256 manifest and optional Authenticode signing
python scripts/package_windows_release.py --version v3.1.0-RC8
```
The compiled output is located in `dist/FlowPilot-v3.1.0-RC8-win64.zip`.

---

## 🤝 Submitting Changes

1. **Create an Issue:** Before submitting large architectural changes, open an issue to discuss your proposal against existing [specs](docs/specs/).
2. **Branch Naming:** Use descriptive branch prefixes:
   - `feature/your-feature-name`
   - `fix/issue-description`
   - `docs/documentation-update`
3. **Run the Audit Suite:** Verify that `python -X utf8 tests/run_all_tests.py` passes cleanly with zero failures.
4. **Commit Messages:** Follow the [Conventional Commits](https://www.conventionalcommits.org/) format (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
5. **Open a Pull Request:** Submit your PR against `master`. Hosted CI will verify tests, code compilation, and package smoke before review.
