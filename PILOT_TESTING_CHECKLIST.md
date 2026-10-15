# FlowPilot Repeatable Pilot Testing Checklist

**Tester Name:** _______________________  
**Date of Test:** _______________________  
**Host Hardware / Laptop Model:** _______________________  
**Windows Version / Build:** _______________________  
**FlowPilot Version:** v3.1.0-pilot Standalone (SHA-256: 4FD81150A5E404AB64C52B0C03BACB454D59DF6911BF0E23D3EABC363ED1B6FE)  

Please perform each step below in order and record your empirical observations.

---

## Evaluation Scenarios

| Step # | Scenario | Test Instructions | Expected Result | Pass / Fail | Notes & Observations |
|:---:|:---|:---|:---|:---:|:---|
| **1** | **Clean Spawn & HUD** | Launch `FlowPilot.exe`. Observe time to appearance. | HUD appears at top-center within 1.5s. Tray icon visible. | [ ] PASS<br>[ ] FAIL | |
| **2** | **Single Instance Lock** | Double-click `FlowPilot.exe` a second time while it is already running. | Second process cleanly terminates without opening duplicate HUD or crashing. | [ ] PASS<br>[ ] FAIL | |
| **3** | **Notepad Basic Dictation** | Open Notepad. Press `Ctrl+Shift+Space`. Speak: *"This is a pilot test of the FlowPilot voice system."* Press shortcut to stop. | Audio cues sound. Injected accurately into Notepad within ~300ms. Cursor advances. | [ ] PASS<br>[ ] FAIL | |
| **4** | **Focus Protection** | Click the floating microphone pill with your mouse. | Floating HUD does not steal focus from Notepad (`WS_EX_NOACTIVATE`). | [ ] PASS<br>[ ] FAIL | |
| **5** | **Audio Ducking Recovery** | Play background media (YouTube/Spotify). Start recording. Stop recording. | Background media volume lowers during speech and instantly restores to exact volume upon stop. | [ ] PASS<br>[ ] FAIL | |
| **6** | **Spoken Self-Correction** | Dictate: *"Meeting is scheduled for Monday — actually, Tuesday at three PM."* | Injected text reads: *"Meeting is scheduled for Tuesday at 3:00 PM."* Monday is cleanly omitted. | [ ] PASS<br>[ ] FAIL | |
| **7** | **Technical Identifier Casing** | Dictate: *"create snake case user auth token and camel case parse json"* | Injected text renders: `user_auth_token` and `parseJson`. | [ ] PASS<br>[ ] FAIL | |
| **8** | **Non-Destructive Clipboard** | Copy *"SENSITIVE_SECRET_ABC"* to clipboard. Run a dictation cycle. Wait 2 seconds. Press `Ctrl+V`. | *"SENSITIVE_SECRET_ABC"* pastes, confirming pre-dictation clipboard was safely restored. | [ ] PASS<br>[ ] FAIL | |
| **9** | **Emergency Cancellation** | Start dictation, speak 2 words, press `Esc` (or click Cancel). | Audio cue sounds. Recording is discarded. Nothing injected into document. Audio unducks. | [ ] PASS<br>[ ] FAIL | |
| **10**| **Recovery Buffer Retrieval** | Close target document immediately after dictation. Right-click tray icon > "Copy Last Dictation". Paste into a new document. | The last dictated text is retrieved from memory and pasted successfully. | [ ] PASS<br>[ ] FAIL | |

---

## Overall Pilot Outcome & Satisfaction

- **Total Scenarios Passed:** _____ / 10
- **Perceived Speed (1 to 5 stars):** [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5
- **Accuracy & Meaning Quality (1 to 5 stars):** [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5
- **General Usability & Reliability (1 to 5 stars):** [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5
- **Would you recommend FlowPilot to colleagues in your team?** [ ] Yes  [ ] No  [ ] Undecided

**Tester Signature:** _______________________  
