# Contributing to FlowPilot

Thank you for your interest in improving FlowPilot! We welcome contributions from developers, designers, and voice interface enthusiasts.

---

## 🛠️ Development Setup

### Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.10, 3.11, or 3.12
- Git
- Working microphone

### Setting up the Environment
```powershell
# 1. Clone repository
git clone https://github.com/abishekvr0910/flowpilot.git
cd flowpilot

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies in editable mode
pip install -r requirements.txt
pip install -e .[dev]
```

---

## 🧪 Running the Test Suites

FlowPilot features comprehensive regression, specification, and safety test suites:

### 1. Complete Automated Audit Suite (20 Tests)
Runs microphone checks, Whisper model inference, FactGuard rules, Win32 hotkey loop, network egress verification, and 5-cycle Notepad dictation:
```powershell
python tests/run_all_tests.py
```

### 2. Full 18-Scenario Specification Verification
Validates end-to-end system behaviors including single-instance mutex, foreground targeting, spoken self-correction, audio ducking, and emergency cancellation:
```powershell
python tests/test_final_specification_e2e.py
```

### 3. Packaged Standalone Binary Smoke Test
Verifies binary packaging, dynamic DLL resolution, and single-instance mutex handling:
```powershell
python tests/test_standalone_binary_smoke.py
```

---

## 📐 Coding Standards & Guidelines

- **Zero Network Egress:** Core dictation components must never make network calls unless the user explicitly configured cloud mode.
- **Privacy Preservation:** Never log user audio, transcripts, or personal data to stdout, disk files, or diagnostic dumps.
- **FactGuard Preservation:** Any changes to `ContextProcessor` or `WritingIntelligence` must strictly preserve negations, numbers, dates, and technical symbols without hallucination.
- **Thread Safety:** Audio capture, hotkey listeners, and UI components run on distinct threads; always protect shared resources using locks (`threading.Lock()`).
- **Win32 Window Focus:** The floating HUD must always retain the `WS_EX_NOACTIVATE` window style so it never steals focus from the user's active window.

---

## 📦 Building the Standalone Executable

To compile FlowPilot into a standalone Windows binary:
```powershell
pyinstaller --noconfirm flowpilot.spec
```
The compiled output is located in `dist/FlowPilot/FlowPilot.exe`.

---

## 🤝 Submitting Changes

1. Fork the repository and create your feature branch (`git checkout -b feature/amazing-feature`).
2. Verify all test suites pass locally (`python tests/run_all_tests.py`).
3. Commit your changes with clear, descriptive messages.
4. Push to your branch and open a Pull Request.
