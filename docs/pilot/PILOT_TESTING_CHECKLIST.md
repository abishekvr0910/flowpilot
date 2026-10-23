# FlowPilot Pilot Testing Checklist

**Date:** __________  **Candidate artifact SHA-256 / commit:** __________  **Windows version:** __________  **Microphone:** __________

Use non-sensitive test content. Record observed behavior and timings; expected outcomes below are goals, not claims that every machine has passed.

| Scenario | Expected behavior | Result / notes |
|---|---|---|
| Launch and exit | Exactly one companion HUD and system tray icon; clean exit without orphan processes | |
| Duplicate launch | Second process exits immediately with code 0; primary process holds mutex | |
| Notepad dictation | Text inserted at the cursor; record stop-to-visible-text time | |
| Focus integrity | Companion HUD interaction does not steal editor focus (`WS_EX_NOACTIVATE`) | |
| Appearance selection | Passive HUD keeps editor focus; intentionally opened Studio accepts input and returns safely to the workflow | |
| Push-to-talk | `F9` (or configured key) starts and ends capture cleanly in hold or toggle mode | |
| Clipboard preservation | Existing clipboard text or a newer user copy remains intact; record rich format limits separately | |
| Cancel and recovery | Cancel using the supported control inserts nothing; Copy Last Dictation works when a recovery buffer exists | |
| Audio ducking | Background audio attenuates during speech and restores cleanly after finalization | |
| **Delivery outcomes: Verified paste** | Target buffer read back matches inserted transcript | |
| **Delivery outcomes: Unverified dispatch** | App reports unverified dispatch when it cannot confirm the document; record the human observation separately | |
| **Delivery outcomes: Safe refusal** | Focus switched away during speech; no typing dispatched to wrong window; text preserved in memory | |
| **Delivery outcomes: Duplicate insertion** | No double-typing or duplicate characters observed | |
| **Privacy: History disabled (default)** | With `save_history_text: false`, `~/.flowpilot/history/` writes zero WAV or transcript files | |
| **Privacy: History enabled (opt-in)** | When enabled in Settings, Vault writes local WAV/JSON; individual/all delete works cleanly | |
| **Privacy: Existing stored data** | Upgrading from older profile preserves previous history without automatic deletion | |
| **External transform repair** | Replace and Revert remain unavailable; preview and explicit Copy Output work without automatic external typing | |
| **Upgrade settings** | Existing privacy choices, dictionary, snippets, and companion settings survive a tested upgrade | |
| **Artifact identity** | Recorded ZIP and executable hashes match the reviewed candidate; source repairs are not attributed to an older binary | |
| **Multilingual dictation** | Test Hindi / Tamil / Malayalam accuracy against real speaker speech; note dialect/accent | |

**Issues:** Link to a [bug report](PILOT_BUG_REPORT_TEMPLATE.md) or GitHub issue: __________

Do not count a skipped hardware scenario as a pass. Redact any diagnostics or screenshots before sharing.
