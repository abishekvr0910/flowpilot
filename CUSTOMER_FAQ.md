# FlowPilot Customer & Enterprise Frequently Asked Questions (FAQ)

**Product:** FlowPilot Desktop  
**Version:** 2.1.0  
**Classification:** Customer Support & Sales Enablement  

---

## 1. Privacy, Security & Offline Operation

### Q: Is FlowPilot truly 100% offline? How can I independently verify this?
**A:** Yes. FlowPilot runs CTranslate2 quantized Whisper speech recognition directly on your computer's local CPU. Once installed, it opens **zero outbound network connections**. You can independently verify this at any time by:
1. Running FlowPilot while your laptop is in **Windows Airplane Mode** (Wi-Fi disconnected).
2. Using Windows Task Manager > Performance > Resource Monitor > Network tab.
3. Running FlowPilot's automated socket audit script: [`python tests/test_network_egress.py`](file:///S:/APPs/New%20folder/tests/test_network_egress.py).

### Q: What happens to my spoken audio? Does FlowPilot store audio recordings on disk?
**A:** No. Microphone audio is streamed into temporary volatile memory (RAM) strictly for the duration of your utterance. As soon as transcription completes, the memory buffer is cleared and garbage-collected. Spoken audio is never written to your hard drive or transmitted to the cloud.

### Q: Is FlowPilot compliant with HIPAA and GDPR?
**A:** FlowPilot provides a **HIPAA-Eligible Architecture** and aligns with **GDPR Privacy-by-Design** principles. Because voice data never leaves your local workstation, deploying FlowPilot eliminates third-party cloud data transmission, cross-border data transfer liabilities, and the requirement for complex cloud Business Associate Agreements (BAAs). Your organization maintains complete physical custody of all spoken voice data.

---

## 2. Hardware Requirements & Performance

### Q: Do I need an expensive dedicated NVIDIA GPU to run FlowPilot?
**A:** No. FlowPilot is optimized with CTranslate2 INT8 quantization to run fast and smooth on standard Intel and AMD x86_64 CPUs (Intel Core 4th Gen+ or AMD Ryzen). A 5-second dictation processes in under ~950 ms on standard laptop processors.

### Q: How much system memory (RAM) does FlowPilot consume?
**A:** FlowPilot consumes approximately **~127 MB to ~290 MB of RAM** while running in the background. Unlike Electron-based alternatives that consume 600MB–1,000MB and spin laptop fans, FlowPilot is built natively with PySide6/Win32 for negligible background resource impact.

---

## 3. Daily Workflow & Dictation Controls

### Q: What keyboard shortcuts does FlowPilot use?
**A:** 
- **`Ctrl + Shift + Space` (Default):** Toggle dictation on/off. Press once to start speaking; press again to paste formatted writing.
- **`F9` (Push-to-Talk):** Hold `F9` while speaking; release to paste.
- **`Ctrl + Alt + Space`:** Secondary toggle shortcut if your system has a shortcut conflict.
- **`Esc`:** Emergency cancel (discards recording and restores background volume).

### Q: Can I run FlowPilot and Wispr Flow on the same computer?
**A:** Yes. Wispr Flow binds `Ctrl + Win`, while FlowPilot uses `Ctrl + Shift + Space` and `F9`. Both applications can be active simultaneously without shortcut collisions or audio device starvation.

### Q: Will dictating with FlowPilot overwrite what I already copied to my clipboard?
**A:** No. FlowPilot saves your pre-existing clipboard contents before pasting, injects the new text in ~300ms, and automatically restores your original clipboard data within 1.5 seconds.

### Q: What if a window closes and my text doesn't paste?
**A:** FlowPilot maintains an in-memory recovery buffer. Simply right-click the FlowPilot tray icon and select **"Copy Last Dictation"**, then press `Ctrl + V` into any document.

---

## 4. Writing Intelligence & Custom Terminology

### Q: How does spoken self-correction work?
**A:** If you make a mistake or change your mind mid-sentence (*"Schedule the meeting for Monday -- actually, Tuesday at 3 PM"*), FlowPilot automatically detects the retraction phrase, removes the superseded information ("Monday"), and pastes the corrected statement (*"Schedule the meeting for Tuesday at 3:00 PM."*).

### Q: What is FactGuard™?
**A:** FactGuard is FlowPilot's deterministic safety layer that inspects the raw speech transcript against the polished output. It mathematically guarantees that numbers, currency amounts, dates, and critical negations (`not`, `never`, `cannot`, `without`) are never deleted or hallucinated by AI rewriting.

### Q: Can our team share a customized dictionary of company terms and acronyms?
**A:** Yes! FlowPilot stores custom vocabulary in a standard JSON file (`%USERPROFILE%\.flowpilot\personalization.json`). IT administrators can distribute a pre-configured dictionary file via Microsoft Intune or corporate group policy to standardize company nomenclature across hundreds of employee laptops.

---

## 5. Licensing, Purchasing & Support

### Q: How is FlowPilot priced?
**A:** We offer:
- **Individual Pro:** $49.00 one-time perpetual license with 1 year of updates (or $4.99/mo).
- **Team / Practice:** $12.00 / seat / month (billed annually) with team dictionary sync and commercial rights.
- **Enterprise Air-Gapped:** $36.00 – $48.00 / seat / year for volume fleet deployments.

### Q: What is your refund policy?
**A:** We offer a **14-day risk-free money-back guarantee**. If FlowPilot does not improve your daily writing speed and workflow, simply contact support@flowpilot.local for an immediate 100% refund.
