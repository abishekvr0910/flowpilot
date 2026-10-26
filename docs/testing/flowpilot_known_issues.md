# FlowPilot Known Issues, Operating Boundaries & Mitigations

**Product:** FlowPilot Desktop  
**Target Platform:** Windows 10 & Windows 11 (x64)  
**Reviewed:** October 18, 2026; source behavior can differ from published builds.
**Document Classification:** Technical Architecture & Field Support  

---

## 1. Windows UIPI & Elevation Isolation (User Interface Privilege Isolation)

- **Root Cause:** Windows security enforces User Interface Privilege Isolation (UIPI). A medium-integrity process (standard user mode) is strictly forbidden by the NT kernel from injecting synthetic keystrokes (`SendInput`, `AttachThreadInput`, `WM_PASTE`) into high-integrity (elevated / Administrator) windows.
- **Symptom:** Audio records and transcribes normally, HUD indicates success, but text does not appear in elevated windows (such as an Administrator PowerShell console, elevated Command Prompt, or Regedit).
- **Mitigation & Handling:**
  1. **Manual recovery:** First check whether text arrived. If absent, use the tray's **Copy Last Dictation**, focus the intended field, and paste manually. Current focus-abort handling retains text in memory without necessarily putting it on the clipboard.
  2. **Privilege boundary:** Keep normal dictation at standard user privilege. Running FlowPilot elevated broadens its privileges and is not the default remedy. Test any elevated workflow separately.

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
- **Verification boundary:** Check the configured shortcuts and selected audio devices on the actual host. Different default chords do not prove that both applications can capture concurrently without conflicts.

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
  - FlowPilot types into verified Windows Terminal and legacy console windows using Unicode `SendInput`, because this workstation's Windows Terminal ignored `Shift + Insert`. It reports the delivery as unverified unless the document can be read. Newlines are refused so dictation cannot submit a command.
  - Other terminal emulators still use their configured paste shortcut. If delivery is unconfirmed, check the target before retrying to avoid duplicate text.
  - The latest dictation is retrievable from **"Copy Last Dictation"** while it remains in the process's recovery buffer. It is replaced by later dictations and does not survive app exit.

---

## 6. Multi-Monitor Display DPI Scaling

- **Root Cause:** When moving windows across monitors with mixed DPI scaling (e.g. 150% scaling on a 4K laptop display and 100% on an external 1080p monitor), Windows Win32 coordinate calculations can occasionally report stale screen geometries.
- **Mitigation:**
  - FlowPilot's floating HUD (`ui/floating_hud.py`) listens to Qt `screenChanged` signals and dynamically recalculates its top-center position based on the geometry of the currently focused display screen.

---

## 7. Air-Gapped Model Weight Provisioning

- **Current behavior:** Runtime model loading uses `local_files_only=True`; a missing model fails with a provisioning message rather than downloading automatically.
- **Provisioning:** Follow [the source setup guide](../../QUICKSTART.md#running-current-source) to explicitly download weights during connected setup, or transfer a complete model directory/cache for disconnected use. Creating an empty cache folder is insufficient. Verify the chosen build and model with local-only loading; evaluate optional integrations separately.

---

## 8. Windows Workstation Lock Screen (`LockApp.exe`)

- **Root Cause:** When Windows locks (e.g., `Win + L` or screen saver timeout), the OS switches the active desktop from `Default` to `Winlogon` / `LockApp.exe`. Under the Windows NT security architecture, non-elevated user processes cannot open or manipulate the clipboard on an inactive desktop session (`ERROR_ACCESS_DENIED (5)`).
- **Mitigation & Handling:**
  - FlowPilot's `TextInjector` catches `ERROR_ACCESS_DENIED` without crashing.
  - The transcribed, polished dictation is automatically safeguarded in the internal recovery buffer (`get_last_injected_text()`).
  - Upon unlocking the workstation, the user can right-click the FlowPilot tray icon and select **"Copy Last Dictation"** to retrieve their text.


