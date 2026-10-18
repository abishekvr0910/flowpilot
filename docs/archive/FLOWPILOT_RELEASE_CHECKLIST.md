# FlowPilot Production Release & Deployment Verification Checklist

> **Historical snapshot - superseded.** Retained for provenance only. Do not use this document as current instructions, test status, performance proof, legal/compliance advice, or up-to-date competitor information. See the [archive index](README.md) for current sources.

**Product:** FlowPilot Desktop  
**Target Platform:** Windows 10 / Windows 11 (64-bit)  
**Binary Distribution:** Standalone Portable Directory / Installer (`dist/FlowPilot/FlowPilot.exe`)  
**Date:** October 14, 2026  
**Status:** Certified Release Checklist  

---

## 1. Prerequisites and Host Environment

Prior to deployment on a clean target machine, verify the following baseline prerequisites:

- [x] **Operating System:** Windows 10 (Version 1903+) or Windows 11 (64-bit).
- [x] **Processor Architecture:** x86_64 with AVX2 instruction set support (Intel Core 4th Gen+, AMD Zen+).
- [x] **System Memory (RAM):** Minimum 4 GB available (8 GB+ recommended).
- [x] **Microsoft Visual C++ Redistributable:** 2015–2022 x64 runtime (`vc_redist.x64.exe`) installed for CTranslate2 / PortAudio DLL bindings.
- [x] **Microphone Endpoint:** Active, unmuted audio input device recognized by Windows CoreAudio.
- [x] **Microphone Permissions:** Windows Settings > Privacy & Security > Microphone > "Let desktop apps access your microphone" enabled.

---

## 2. Binary Compilation & Packaging Verification

- [x] **PyInstaller Specification:** `flowpilot.spec` includes all required native binaries (`ctranslate2.dll`, `portaudio.dll`, `sndfile.dll`, PySide6 plugins).
- [x] **Standalone Executable Verified:** `dist/FlowPilot/FlowPilot.exe` generated (~32.7 MB).
- [x] **Clean Launch Test:** Launches without external Python interpreter or virtual environment.
- [x] **Startup Latency:** HUD and Tray icon appear in under 1.5 seconds from process spawn.
- [x] **DLL Dependency Audit:** No missing dynamic libraries reported via `dumpbin` or `Dependencies.exe`.

---

## 3. Subsystem Functional Verification (Smoke Test)

Perform the following 9-step smoke test on any new host deployment:

### Step 1: Single Instance Lock
- Launch `FlowPilot.exe`.
- Attempt to launch a second instance of `FlowPilot.exe`.
- **Expected Result:** The second process immediately detects `Global\FlowPilot_Desktop_SingleInstance_Mutex`, displays a notification that FlowPilot is already running, and terminates without error code.

### Step 2: System Tray & Floating HUD
- Look at the Windows notification area (System Tray).
- **Expected Result:** FlowPilot microphone pill icon is present. Floating HUD pill appears top-center of the screen in ready/idle state.
- Click the floating HUD.
- **Expected Result:** HUD does not steal keyboard focus from the active foreground application (`WS_EX_NOACTIVATE`).

### Step 3: Global Hotkey Registration
- Open a text editor (e.g. Windows Notepad).
- Type some initial text. Ensure the cursor remains in Notepad.
- Press `Ctrl + Shift + Space` (or alternate shortcut `Ctrl + Alt + Space` / `F9`).
- **Expected Result:** Audio cue sounds (ascending dual-tone beep 880Hz -> 1320Hz). HUD transitions to pulsing red/amber "Recording..." state.

### Step 4: Microphone Capture & Audio Ducking
- While background music (Spotify, YouTube, Media Player) is playing, activate recording.
- **Expected Result:** Background media audio is immediately muted or attenuated.
- Speak clearly into the microphone: *"This is a test of the FlowPilot local dictation system."*
- Press `Ctrl + Shift + Space` again to stop.
- **Expected Result:** Audio cue sounds (descending dual-tone beep 1320Hz -> 880Hz). Background media audio returns to its exact pre-dictation volume.

### Step 5: Fast Transcription & In-Place Text Injection
- Observe the active Notepad document.
- **Expected Result:** Within ~300ms, the transcribed and formatted text is pasted directly into Notepad at the cursor position. Cursor advances. Original window focus is retained.

### Step 6: Writing Intelligence & Self-Correction
- Press hotkey and speak: *"Please schedule the client review for Thursday — actually, Friday at two PM."*
- Stop dictation.
- **Expected Result:** Text inserted is: *"Please schedule the client review for Friday at 2:00 PM."* The mistaken word "Thursday" is removed, and "Friday at 2:00 PM" is formatted with FactGuard preservation.

### Step 7: Technical Formatting (Developer Mode)
- Switch style to Technical/Developer or speak: *"create camel case user profile and snake case get account balance"*.
- **Expected Result:** Injected text renders as: `userProfile` and `get_account_balance`.

### Step 8: Clipboard Non-Destructive Restoration
- Copy sensitive text to clipboard before dictation: *"CONFIDENTIAL_DATA_123"*.
- Perform a dictation cycle into Notepad.
- Wait 2 seconds. Press `Ctrl + V` manually in Notepad.
- **Expected Result:** *"CONFIDENTIAL_DATA_123"* is pasted, verifying that user clipboard contents were fully restored.

### Step 9: Tray Recovery Buffer ("Copy Last Dictation")
- Open the System Tray menu by right-clicking the FlowPilot icon.
- Click **"Copy Last Dictation"**.
- Press `Ctrl + V` into any document.
- **Expected Result:** The last dictated sentence is pasted from the internal recovery buffer.

---

## 4. Uninstallation and Data Cleanup

To cleanly remove FlowPilot from a target system:
1. Exit FlowPilot via Tray Menu > **"Exit FlowPilot"**.
2. Delete the `FlowPilot` application directory.
3. (Optional) Remove user settings and personal dictionary from:
   `%APPDATA%\FlowPilot\` (or delete `personalization.json`).
4. FlowPilot writes zero keys to `HKEY_LOCAL_MACHINE` and requires no registry scrubbing.
