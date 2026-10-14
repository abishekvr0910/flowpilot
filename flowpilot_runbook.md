# FlowPilot Operational Runbook (v2.0 Native Desktop)

**Version:** 2.0.0-verified  
**Author:** FlowPilot Engineering  
**Working Directory:** `S:\APPs\New folder`

---

## 1. Quick Start

### How to Launch FlowPilot Desktop
FlowPilot runs as a native Windows desktop application with a floating microphone HUD (Flow Pill) and system tray presence:

1. **Option A (Desktop Batch File — Recommended):**
   * Double-click [`start_desktop.bat`](file:///S:/APPs/New%20folder/start_desktop.bat) in `S:\APPs\New folder`.
   * The floating microphone pill will appear at the bottom center of your screen, and the FlowPilot icon will appear in the Windows System Tray (notification area).

2. **Option B (PowerShell / Command Prompt):**
   ```powershell
   cd "S:\APPs\New folder"
   python desktop_app.py
   ```

3. **Option C (Standalone Executable from `dist/`):**
   * Run `dist\FlowPilot\FlowPilot.exe`.

---

## 2. How to Dictate (Daily Usage)

### Method 1: The Native Floating Flow Pill
1. Open any application (Notepad, VS Code, Word, Chrome, Slack, Discord).
2. Click the circular **Microphone Button** on the floating Flow Pill:
   * **Crucial Feature:** Because the Flow Pill uses Win32 `WS_EX_NOACTIVATE`, clicking the pill **never steals focus** from your editor!
   * Any background audio (YouTube/Spotify) will immediately silence.
   * The live blue waveform bar will animate as you speak.
3. Speak your sentence naturally.
4. Click the **Microphone Button** again (or press the hotkey):
   * Background audio restores immediately.
   * Local Faster-Whisper transcribes your voice on CPU.
   * The formatted text pastes directly into your active cursor position.
   * The pill turns green and displays "Pasted!" for 1.2s before returning to idle.

### Method 2: Global Win32 Keyboard Shortcuts
With FlowPilot running anywhere in the background:
* **Primary Toggle Shortcut:** Press **`Ctrl + Shift + Space`** once to start recording, and press it again to finish and paste.
* **Secondary Toggle Shortcut:** Press **`Ctrl + Alt + Space`**.
* **Single-Key Toggle:** Press **`F9`** (great for rapid single-key dictation).

*(Note: Wispr Flow's shortcut `Ctrl + Win` is intentionally not used to prevent conflicts).*

---

## 3. System Tray & Settings

### System Tray Actions (Bottom-Right Taskbar):
* **Left Click:** Toggles dictation immediately.
* **Right Click:**
  * **Dictate:** Start/Stop dictation.
  * **Show/Hide Floating Mic:** Toggles pill visibility.
  * **Silence Background Audio:** Checkbox to toggle audio ducking on/off.
  * **Settings & History:** Opens the Settings Dialog.
  * **Exit FlowPilot:** Cleanly unregisters hotkeys and shuts down.

### Settings Dialog Features:
1. **Model Selection:**
   * `base`: Default ultra-fast local model (140MB, ~1s latency on CPU).
   * `small`: Higher accuracy for complex sentences (460MB).
   * `medium`: Maximum accuracy for technical prose (1.4GB).
2. **Tone Selection:**
   * `default`: Natural dictation with punctuation.
   * `developer`: Code-aware formatting with snake_case and camelCase.
   * `casual`: Relaxed everyday speech.
   * `professional`: Formal email and document tone.
3. **Dictation History:**
   * Displays the last 50 dictations with timestamps, durations, and target application names.
   * "Copy Selected Text" button to re-copy previous dictations.

---

## 4. Troubleshooting & Automated Diagnostics

### Run the Complete 9-Subsystem Audit Suite
If you want to verify that every hardware and software component is operating properly:

```powershell
cd "S:\APPs\New folder"
python tests/run_all_tests.py
```

This validates all 9 subsystems in under 26 seconds:
1. Microphone enumeration & 16kHz PCM capture
2. Faster-Whisper local model loading & inference
3. Text injection & clipboard preservation
4. Windows CoreAudio ducking & error recovery
5. REST API & WebSocket streaming protocol
6. Global hotkey normalization
7. Win32 `RegisterHotKey` kernel message loop
8. PySide6 Floating HUD & Tray lifecycle
9. 5 consecutive end-to-end Notepad injection cycles

---

## 5. Clean Process Termination

To cleanly exit FlowPilot:
* Right-click the Flow Pill -> Click **Exit FlowPilot**, or
* Right-click the FlowPilot tray icon -> Click **Exit FlowPilot**, or
* Via PowerShell:
  ```powershell
  Get-Process -Name python*, FlowPilot* -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*FlowPilot*" } | Stop-Process -Force
  ```
