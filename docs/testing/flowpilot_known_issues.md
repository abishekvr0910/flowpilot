# FlowPilot Known Issues, Operating Boundaries & Mitigations

**Product:** FlowPilot Desktop  
**Target Platform:** Windows 10 & Windows 11 (x64)  
**Date:** October 14, 2026  
**Document Classification:** Technical Architecture & Field Support  

---

## 1. Windows UIPI & Elevation Isolation (User Interface Privilege Isolation)

- **Root Cause:** Windows security enforces User Interface Privilege Isolation (UIPI). A medium-integrity process (standard user mode) is strictly forbidden by the NT kernel from injecting synthetic keystrokes (`SendInput`, `AttachThreadInput`, `WM_PASTE`) into high-integrity (elevated / Administrator) windows.
- **Symptom:** Audio records and transcribes normally, HUD indicates success, but text does not appear in elevated windows (such as an Administrator PowerShell console, elevated Command Prompt, or Regedit).
- **Mitigation & Handling:**
  1. **Standard Mode:** FlowPilot copies the transcribed text to the system clipboard and displays a visual indicator. Users can press `Ctrl + V` manually into the elevated application.
  2. **Elevated Execution:** If your primary workflow requires dictating into administrative terminals or IDEs, launch FlowPilot using **"Run as Administrator"** or configure its shortcut property to always run elevated.

---

## 2. Laptop Multimedia Function Lock (Fn Keys)

- **Root Cause:** Many modern enterprise laptops (Dell XPS/Latitude, Lenovo ThinkPad, HP EliteBook, Asus ROG) ship with Function Lock disabled by default. In this mode, physical `F1–F12` keys emit ACPI multimedia hardware events (e.g. brightness, volume, mute) rather than standard virtual keycodes (`VK_F1`–`VK_F12`).
- **Symptom:** Pressing `F9` alters display brightness or audio volume instead of activating FlowPilot push-to-talk.
- **Mitigation:**
  1. Toggle Function Lock by pressing `Fn + Esc` on the laptop keyboard.
  2. Use FlowPilot's multi-key chords: **`Ctrl + Shift + Space`** (default) or **`Ctrl + Alt + Space`**.
  3. Click the microphone icon directly on the floating HUD pill.

---

## 3. Coexistence with Competitor Software (Wispr Flow)

- **Root Cause:** Wispr Flow Windows client registers the global hotkey `Ctrl + Win`. Attempting to register the exact same key combination from FlowPilot would cause Windows API `RegisterHotKey` to fail with Win32 Error 1409 (`ERROR_HOTKEY_ALREADY_REGISTERED`).
- **Design Resolution:** FlowPilot deliberately configures and registers:
  - Primary: `Ctrl + Shift + Space`
  - Secondary: `Ctrl + Alt + Space`
  - Tertiary: `F9`
- **Verification:** Both applications can run simultaneously on the same host without hotkey collisions or audio device starvation.

---

## 4. Hardware Sample-Rate Fallback & Audio Drivers

- **Root Cause:** Certain specialized audio hardware (e.g., Intel Smart Sound Technology Digital Arrays, USB studio interfaces, or Bluetooth Low Energy hands-free profiles) reject PortAudio requests for 16,000 Hz capture with error code `-9997 (Invalid sample rate)`.
- **Mitigation:**
  - FlowPilot's `AudioRecorder` detects sample-rate rejection automatically.
  - It queries the default device for its native hardware rate (typically 44,100 Hz or 48,000 Hz), captures at the hardware's native rate, and dynamically resamples the audio stream to 16,000 Hz mono PCM using linear interpolation (`np.interp`) before delivering it to the Whisper model.

---

## 5. Terminal & Legacy Console Paste Emulation

- **Root Cause:** Legacy terminal emulators (vintage `cmd.exe` without QuickEdit mode, PuTTY, Mintty, or terminal applications running inside `tmux`/`vim`) interpret synthetic `Ctrl + V` keystrokes as ASCII control code `0x16` (`^V`) rather than a clipboard paste command.
- **Mitigation:**
  - In Windows Terminal, `Ctrl + Shift + V` or `Ctrl + V` works out of the box.
  - In vintage terminals, FlowPilot preserves the transcribed text on the system clipboard. The user can press `Shift + Insert` (standard Unix terminal paste) or right-click to paste.
  - The latest dictation is always retrievable from the System Tray menu via **"Copy Last Dictation"**.

---

## 6. Multi-Monitor Display DPI Scaling

- **Root Cause:** When moving windows across monitors with mixed DPI scaling (e.g. 150% scaling on a 4K laptop display and 100% on an external 1080p monitor), Windows Win32 coordinate calculations can occasionally report stale screen geometries.
- **Mitigation:**
  - FlowPilot's floating HUD (`ui/floating_hud.py`) listens to Qt `screenChanged` signals and dynamically recalculates its top-center position based on the geometry of the currently focused display screen.

---

## 7. Air-Gapped Model Weight Provisioning

- **Root Cause:** To keep repository clone sizes lightweight, faster-whisper model weights are downloaded from Hugging Face Hub during first run on machines with active internet access.
- **Air-Gapped Deployment:** For secure, offline-only, or classified environments with zero internet access, administrators can pre-provision the model weights by placing the model directory in:
  `C:\Users\<Username>\.cache\huggingface\hub\models--Systran--faster-whisper-base\`
  Once provisioned, FlowPilot functions 100% offline with zero external network connectivity.

---

## 8. Windows Workstation Lock Screen (`LockApp.exe`)

- **Root Cause:** When Windows locks (e.g., `Win + L` or screen saver timeout), the OS switches the active desktop from `Default` to `Winlogon` / `LockApp.exe`. Under the Windows NT security architecture, non-elevated user processes cannot open or manipulate the clipboard on an inactive desktop session (`ERROR_ACCESS_DENIED (5)`).
- **Mitigation & Handling:**
  - FlowPilot's `TextInjector` catches `ERROR_ACCESS_DENIED` without crashing.
  - The transcribed, polished dictation is automatically safeguarded in the internal recovery buffer (`get_last_injected_text()`).
  - Upon unlocking the workstation, the user can right-click the FlowPilot tray icon and select **"Copy Last Dictation"** to retrieve their text.


