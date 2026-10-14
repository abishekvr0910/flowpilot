# FlowPilot Pilot Tester Quick-Start Guide

Welcome to the FlowPilot Pilot Evaluation Program. FlowPilot is a Windows-first, AI-powered speech-to-text writing assistant designed to operate 100% locally with zero cloud data egress.

---

## 1. 3-Minute Fast Setup

1. **Extract or Locate FlowPilot:**
   - Standalone Portable: Unzip `FlowPilot-v2.0.0-win64.zip` into any directory (e.g. `C:\Tools\FlowPilot\`).
   - Development Run: Double-click [`start_desktop.bat`](file:///S:/APPs/New%20folder/start_desktop.bat).
2. **Launch FlowPilot:**
   - Double-click [`FlowPilot.exe`](file:///S:/APPs/New%20folder/dist/FlowPilot/FlowPilot.exe).
   - Within 1.5 seconds, the floating **Microphone Pill** appears at the top center of your screen, and the FlowPilot icon appears in your **Windows System Tray** (notification area).
3. **Verify Microphone Access:**
   - Ensure your microphone is plugged in and enabled in Windows:  
     *Settings > Privacy & Security > Microphone > "Let desktop apps access your microphone" = ON*.

---

## 2. Keyboard Shortcuts & Controls

| Shortcut | Action | Behavior |
|:---|:---|:---|
| **`Ctrl + Shift + Space`** | **Toggle Dictation** | Press once to start speaking; press again when done to transcribe and insert text. |
| **`F9`** | **Push-to-Talk** | Hold `F9` down while speaking, release `F9` when finished. |
| **`Ctrl + Alt + Space`** | **Secondary Toggle** | Alternative shortcut if another app binds `Ctrl + Shift + Space`. |
| **`Esc` (or HUD Click)** | **Emergency Cancel** | Immediately discards the recording, restores background audio, and cancels insertion. |

### Audio Feedback Tones
- **Ascending Tone (880 Hz $\rightarrow$ 1320 Hz):** Microphone opened; start speaking.
- **Descending Tone (1320 Hz $\rightarrow$ 880 Hz):** Recording stopped; transcribing and inserting text.
- **Low Cancel Tone (440 Hz $\rightarrow$ 330 Hz):** Dictation cancelled; nothing inserted.

---

## 3. Your First Dictation (Step-by-Step)

1. Open **Windows Notepad**, Microsoft Word, Slack, or your preferred code editor.
2. Click inside the document so your text cursor is blinking.
3. Press **`Ctrl + Shift + Space`**.
   - Notice the ascending chime and the floating HUD glowing red (*"Recording..."*).
   - Notice background music or video automatically quiets down (Audio Ducking).
4. Speak naturally:
   > *"Hello team, please find the quarterly performance update attached for review."*
5. Press **`Ctrl + Shift + Space`** again.
   - Within ~300ms, the transcribed and formatted text is automatically pasted at your cursor.
   - Background audio immediately returns to its original volume.
   - Your original clipboard contents remain safe and are restored automatically.

---

## 4. Key Writing Intelligence Features to Test

### A. Spoken Self-Correction
Say: *"Schedule the meeting for Thursday — actually, Friday morning at 10 AM."*  
**Result:** *"Schedule the meeting for Friday morning at 10 AM."*  
The mistaken word ("Thursday") is automatically removed, and the correct date and time format are preserved.

### B. Developer / Code Formatting
Say: *"create camel case user profile and snake case get account balance"*  
**Result:** `userProfile` and `get_account_balance`.

### C. Voice Snippets
Say: *"Please book time via insert my calendly"*  
**Result:** Injects your pre-configured Calendly link.

### D. Emergency Text Recovery
If text fails to insert because a window was closed or elevated:
1. Right-click the **FlowPilot tray icon**.
2. Click **"Copy Last Dictation"**.
3. Press `Ctrl + V` anywhere to retrieve your text from the internal memory buffer.

---

## 5. Troubleshooting & Bug Reporting

- **Microphone records silence?**
  Run [`collect_diagnostics.bat`](file:///S:/APPs/New%20folder/collect_diagnostics.bat) to verify your audio endpoints.
- **Text doesn't paste into Administrator Command Prompt or PowerShell?**
  Windows User Interface Privilege Isolation (UIPI) blocks standard user apps from typing into elevated windows. Right-click [`FlowPilot.exe`](file:///S:/APPs/New%20folder/dist/FlowPilot/FlowPilot.exe) and select **"Run as Administrator"**.
- **Found a bug?**
  Run [`collect_diagnostics.bat`](file:///S:/APPs/New%20folder/collect_diagnostics.bat) and send the generated `flowpilot_diagnostic_report.txt` along with [`PILOT_BUG_REPORT_TEMPLATE.md`](file:///S:/APPs/New%20folder/PILOT_BUG_REPORT_TEMPLATE.md) to your pilot coordinator.
