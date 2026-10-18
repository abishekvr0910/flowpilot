# FlowPilot Pilot Testing Checklist

**Date:** __________  **Source commit or release tag:** __________  **Windows version:** __________  **Microphone:** __________

Use non-sensitive test content. Record observed behavior and timings; expected outcomes below are goals, not claims that every machine has passed.

| Scenario | Expected behavior | Result / notes |
|---|---|---|
| Launch and exit | One companion and tray icon; clean exit | |
| Duplicate launch | No competing microphone listener | |
| Notepad dictation | Text inserted at the cursor; record stop-to-text time | |
| Focus integrity | Companion interaction does not steal editor focus | |
| Appearance selection | Right-click or Studio changes style; double-click does not cycle | |
| Push-to-talk | `F9` starts and ends capture as configured | |
| Clipboard preservation | Existing clipboard content remains recoverable after paste | |
| Cancel and recovery | Cancel inserts nothing; Copy Last Dictation works when available | |
| Audio ducking | Background audio restores after recording, if supported on host | |
| Local data disclosure | History Vault contains expected WAV/text after dictation; deletion behavior is understood | |

**Issues:** Link to a [bug report](PILOT_BUG_REPORT_TEMPLATE.md) or GitHub issue: __________

Do not count a skipped hardware scenario as a pass. Redact any diagnostics or screenshots before sharing.
