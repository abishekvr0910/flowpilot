# FlowPilot Build & Release Guide

This document describes how to build, test, package, and distribute FlowPilot as a standalone Windows application and installer.

---

## 1. Prerequisites & Environment Setup

* **Operating System:** Windows 10 / Windows 11 (64-bit)
* **Python Runtime:** Python 3.10 or 3.11 (64-bit)
* **Audio Hardware:** Any functioning microphone (integrated array or USB headset)

### Setup Instructions
```powershell
# 1. Clone repository
git clone <repo-url> "S:\APPs\New folder"
cd "S:\APPs\New folder"

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
pip install PySide6 pyinstaller
```

---

## 2. Running Automated Verification

Before building the production package, verify that all 9 subsystems pass the forensic audit suite:

```powershell
python tests\run_all_tests.py
```
Expected output:
```
[PASS] Microphone & Audio Capture                    (2.64s)
[PASS] Local Whisper Speech-to-Text Model            (4.27s)
[PASS] Text Injection & Clipboard Safety             (2.31s)
[PASS] Windows Audio Ducking & Error Recovery        (1.05s)
[PASS] UI REST API & WebSocket Protocol              (3.38s)
[PASS] Global Hotkey Resolution & Normalization      (2.03s)
[PASS] Win32 RegisterHotKey & Message Loop           (0.55s)
[PASS] Native PySide6 Desktop HUD & Tray Lifecycle   (2.61s)
[PASS] End-to-End 5-Cycle Notepad Dictation          (6.54s)
----------------------------------------------------------------------
Total Test Time: ~25s | Overall Verdict: ALL TESTS PASSED
```

---

## 3. Building Standalone Executable with PyInstaller

FlowPilot includes a tailored `flowpilot.spec` bundling the PySide6 desktop shell, CTranslate2/faster-whisper inference engine, and native Win32 libraries.

### Build Command:
```powershell
pyinstaller flowpilot.spec --noconfirm
```

### Resulting Distribution Directory:
The built application resides in:
```
dist/
└── FlowPilot/
    ├── FlowPilot.exe        # Main standalone executable
    ├── python311.dll        # Embedded runtime
    ├── PySide6/             # Qt GUI libraries & plugins
    ├── engine/              # Engine package
    └── ui/                  # UI components
```

---

## 4. Installer Generation (Inno Setup Script)

To produce a single-file setup installer (`FlowPilot_Setup_v2.0.exe`), use the following Inno Setup script (`installer.iss`):

```pascal
[Setup]
AppName=FlowPilot
AppVersion=2.0.0
AppPublisher=FlowPilot Team
DefaultDirName={autopf}\FlowPilot
DefaultGroupName=FlowPilot
UninstallDisplayIcon={app}\FlowPilot.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=dist\installer
OutputBaseFilename=FlowPilot_Setup_v2.0
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start FlowPilot automatically when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "dist\FlowPilot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FlowPilot"; Filename: "{app}\FlowPilot.exe"
Name: "{group}\Uninstall FlowPilot"; Filename: "{uninstallexe}"
Name: "{autodesktop}\FlowPilot"; Filename: "{app}\FlowPilot.exe"; Tasks: desktopicon
Name: "{userstartup}\FlowPilot"; Filename: "{app}\FlowPilot.exe"; Tasks: startupicon

[Run]
Filename: "{app}\FlowPilot.exe"; Description: "{cm:LaunchProgram,FlowPilot}"; Flags: nowait postinstall skipifsilent
```

---

## 5. Model Distribution Strategy

FlowPilot offers two deployment strategies for local speech recognition weights:

1. **Dynamic On-Demand Download (Default):**
   - First run downloads `faster-whisper-base` (~145MB) from Hugging Face Hub to `~/.cache/huggingface/hub/`.
   - Requires internet connection only on first launch.
2. **Air-Gapped / Pre-Bundled Offline Package:**
   - Pre-download the model weights using:
     ```python
     from faster_whisper import WhisperModel
     WhisperModel("base", download_root="dist/FlowPilot/models/base")
     ```
   - In production, set environment variable `HF_HUB_OFFLINE=1` and point `STTEngine` to the local models folder.

---

## 6. Windows Code Signing & Security Notes

To prevent Windows SmartScreen warnings on clean installations:
1. Obtain an EV (Extended Validation) code signing certificate.
2. Sign the binary using `signtool.exe`:
   ```cmd
   signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a "dist\FlowPilot\FlowPilot.exe"
   ```
3. Register the global hotkeys cleanly; Windows Defender will not flag `RegisterHotKey` because it is a standard Win32 API (unlike keyboard hook injections).
