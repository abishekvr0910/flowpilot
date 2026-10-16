# ⚡ FlowPilot 60-Second Quickstart

Welcome to **FlowPilot**! FlowPilot is an open-source, low-latency, 100% private voice dictation assistant for **Windows**, **Linux**, and **macOS** with full Wispr Flow feature parity.

---

## 1. How to Launch FlowPilot

### Windows
- **Option A (One-Click Batch Launcher):** Double-click **`start_desktop.bat`** in the repository root.
- **Option B (Pre-built Standalone App):** Double-click **`FlowPilot.exe`** (or `dist\FlowPilot\FlowPilot.exe`).
- **Option C (From Python Source):**
  ```powershell
  python desktop_app.py
  ```

### Linux (Ubuntu, Debian, Fedora, Arch)
```bash
# Install audio & input prerequisites
sudo apt install libportaudio2 xdotool pulseaudio-utils   # Debian/Ubuntu
# or: sudo dnf install portaudio xdotool pulseaudio-utils # Fedora

python3 desktop_app.py
```

### macOS (Apple Silicon / Intel)
```bash
# Install portaudio
brew install portaudio

python3 desktop_app.py
```
*(Grant Accessibility and Microphone permissions in macOS System Settings when prompted).*

---

## 2. Desktop Companion & Visual Styles

When FlowPilot starts, you will see the **Pilot Companion** appear on your screen:
- 🤖 **Mascot Companion ("Pilot"):** A cute, compact animated robot companion with blinking eyes, pupil dilation that reacts to your voice volume, acoustic antennae waves, thinking swirls, and a joyful smile upon pasting.
- 🚫 **Zero Clutter:** No annoying text pills, no focus-stealing window overlays (`WS_EX_NOACTIVATE`).
- 🖐️ **Draggable Anywhere:** Drag Pilot to any pixel on any monitor. Position is automatically remembered across app restarts.
- 📐 **Snap to Any Corner:** Right-click Pilot to immediately snap to *Bottom-Right*, *Bottom-Left*, *Top-Right*, *Top-Left*, *Left Edge (Middle)*, or *Bottom-Center*.
- 📏 **Wispr Flow Docked Edge Line:** Prefer the minimal Wispr Flow style? Right-click Pilot and select **Appearance Style → Wispr Flow Docked Edge Line** (or double-click the companion) to switch to a sleek vertical bar docked against your screen edge!

---

## 3. How to Dictate (Three Flexible Ways)

Place your cursor in any application (VS Code, Notepad, Browser, Slack, Word, Terminal):

| Method | Shortcut | Action |
|:---|:---|:---|
| **Toggle Mode (Default)** | **`Ctrl + Shift + Space`** *(or click Pilot)* | Press once to speak. Speak naturally. Press again or pause for ~0.85s to finalize and paste at your cursor. |
| **Push-to-Talk (Wispr Flow style)** | **`F9`** | Press and hold `F9`. Speak while holding. Release `F9` to paste instantly. |
| **TapLatch™ Hands-Free** | **Rapid double-tap `F9`** | Rapidly tap `F9` twice (<350ms) to lock dictation hands-free. Single tap `F9` to stop and paste. |

---

## 4. Wispr Flow Voice Commands & Spoken Punctuation

FlowPilot automatically resolves voice editing commands, punctuation, and structural formatting on the fly:

### Spoken Punctuation
- Say *"comma"* → `,`
- Say *"period"* or *"full stop"* → `.`
- Say *"question mark"* → `?`
- Say *"exclamation point"* → `!`
- Say *"colon"* → `:`
- Say *"semicolon"* → `;`
- Say *"open quote"* / *"close quote"* → `"`
- Say *"open paren"* / *"close paren"* → `(` / `)`
- Say *"dot dot dot"* or *"ellipsis"* → `...`

### Voice Editing & Formatting
- **Voice Erase:** Say *"scratch that"* or *"delete that"* to erase the preceding sentence/clause.
- **Word Erase:** Say *"scratch last word"* to erase only the previous word.
- **All Caps:** Say *"all caps urgent"* → `URGENT`.
- **Spoken Self-Correction:** Say *"let's meet Tuesday, actually Wednesday"* → *"Let's meet Wednesday"*.

### Structural Commands
- Say *"new line"* → Inserts `\n` and capitalizes the next sentence.
- Say *"new paragraph"* → Inserts `\n\n` for a clean paragraph break.
- Say *"press tab"* or *"tab"* → Inserts `\t`.

### Smart Formatting
- **Emails & URLs:** Say *"contact john dot doe at company dot com"* → `john.doe@company.com`.
- **Code Identifiers (Developer Mode):** Say *"camel case user profile"* → `userProfile`, *"snake case api key"* → `api_key`.
- **Currencies & Percentages:** Say *"twenty five percent discount on twelve thousand dollars"* → `25% discount on $12,000`.

---

## 5. Pro-Tips & Emergency Recovery

- **Instant Re-Paste:** Press **`Alt + Shift + Z`** anywhere in your OS to immediately re-paste your last dictation buffer.
- **Copy Last Dictation:** If an elevated terminal window blocks automated typing, right-click the System Tray icon or Pilot Companion and select **"Copy Last Dictation"** — your dictation is never lost.
- **Audio Ducking:** FlowPilot automatically lowers background music (Spotify, YouTube, Discord) while speaking, then restores volume upon pasting.
- **100% Offline by Default:** Speech recognition runs locally on your CPU via `faster-whisper` INT8. No audio recordings or keystrokes ever leave your device.
