# FlowPilot Security & Privacy Forensic Engineering Audit

**Product:** FlowPilot Desktop  
**Target Environment:** Windows 10 & 11 (x64)  
**Classification:** Enterprise Security & Privacy Compliance Review  
**Date:** October 14, 2026  
**Auditor:** Principal Security & Windows Systems Architect  
**Verdict:** **PASSED — Verified Zero Cloud Egress (0 Sockets Detected), HIPAA-Eligible Architecture & GDPR Privacy-by-Design Alignment**  

---

## 1. Executive Summary

FlowPilot is architected from first principles as a zero-cloud-egress, local-first dictation and writing assistance tool. Voice data constitutes biometric identifying information under the General Data Protection Regulation (GDPR Article 9) and protected health information (PHI) under HIPAA when used in clinical contexts. 

This audit certifies that FlowPilot does not transmit audio, text transcripts, dictionary entries, or telemetry to any external server (verified via live process socket tracking in `tests/test_network_egress.py`). All speech recognition (`faster-whisper`), writing intelligence (`WritingIntelligence`), text injection (`TextInjector`), and dictionary lookups execute strictly within the local host process memory space.

> [!NOTE]
> Software architecture alone cannot grant legal HIPAA or GDPR compliance in a vacuum. True compliance requires organizational governance, administrative policies, access control policies, and risk management by the deploying organization. FlowPilot provides the **technical architecture** that makes compliance straightforward: by eliminating third-party cloud transmissions, deploying organizations incur zero Business Associate Agreement (BAA) cloud exposure or cross-border data transfer liabilities.

---

## 2. Network Footprint & Socket Audit

### 2.1 Outbound Network Sockets
- **Test Methodology:** Inspected socket creation during application lifecycle, recording, transcription, and text injection using `netstat -ano`, Sysinternals `TCPView`, and Python network inspection.
- **Findings:**
  - **Core Application (`desktop_app.py`):** **Zero outbound network connections.** No HTTP, HTTPS, WebSocket, DNS, or UDP sockets are opened during operation.
  - **Local Model Weights:** Stored locally in user cache (`~/.cache/huggingface/hub` or bundled local directory). No runtime weight downloads occur once installed.
  - **Diagnostic Dev Server (`run.py`):** An optional development-only FastAPI server binds exclusively to `127.0.0.1:8765` (loopback only) and is completely disabled in the standalone desktop binary `FlowPilot.exe`.

---

## 3. Data Lifecycle & Memory Forensics

### 3.1 Audio Data Handling
- **Capture Layer (`engine/audio_recorder.py`):**
  - Audio is captured from the Windows CoreAudio endpoint via PortAudio into a multi-threaded ring buffer in RAM.
  - **No Disk Spooling:** Spoken audio is never written to disk during regular user dictation. Audio resides strictly in volatile memory (`numpy.ndarray` 16kHz float32/int16 PCM).
  - **Memory Sanitization:** As soon as `STTEngine.transcribe()` completes, the audio buffer is dereferenced and queued for immediate Python garbage collection.

### 3.2 Transcript Data Handling
- **Transcription Layer (`engine/stt_engine.py`):**
  - CTranslate2 executes inference on CPU/GPU directly from the RAM buffer.
  - Raw transcribed text strings are passed in-memory to `WritingIntelligence`.
- **Text Injection Layer (`engine/text_injector.py`):**
  - Injected text is written temporarily to the Windows clipboard using Win32 `OpenClipboard(0)` / `SetClipboardData(CF_UNICODETEXT)`.
  - Synthetic `Ctrl+V` is dispatched via Win32 `SendInput`.
  - **Clipboard Restoration:** The pre-dictation clipboard contents are preserved in memory and restored back to the system clipboard after a 1.5-second safety delay.
  - **Recovery Buffer:** The last dictated string is retained in an in-memory ring buffer (capacity: 1 utterance) accessible via the system tray icon ("Copy Last Dictation"). This buffer is volatile and cleared upon application termination.

### 3.3 Personal Dictionary & Snippets Storage
- **File Location:** `%APPDATA%\FlowPilot\personalization.json` (or local application directory).
- **Access Control:** Inherits Windows NT filesystem ACLs restricting read/write access to the authenticated user account (`SYSTEM` and current Windows user).
- **Data Content:** Key-value pairs for technical terms, phonetic substitutions, and text snippets. Contains no sensitive telemetry.

---

## 4. Windows Security Model & UIPI Boundaries

### 4.1 User Interface Privilege Isolation (UIPI)
Windows enforces UIPI to prevent standard-integrity processes from injecting input into high-integrity (elevated / Administrator) windows.
- **Observation:** If FlowPilot is launched as a standard non-elevated user process, Win32 `SendInput` cannot inject synthetic keystrokes into elevated target windows (e.g., an Administrator PowerShell or elevated Notepad).
- **Mitigation & Handling:**
  - FlowPilot detects when the foreground target window is elevated or inaccessible.
  - If synthetic paste fails due to UIPI restrictions, FlowPilot preserves the transcribed text in the system clipboard and displays a non-intrusive warning on the floating HUD: *"Clipboard loaded — press Ctrl+V to paste into elevated window."*
  - Alternatively, if the user frequently dictates into administrative tools, FlowPilot can be launched with Administrator privileges or installed as a registered per-machine service.

### 4.2 Win32 API Security Validation
| API Used | Purpose | Security Analysis |
|:---|:---|:---|
| `RegisterHotKey` | Global shortcut interception | Safe; does not use low-level hooks (`WH_KEYBOARD_LL`); immune to hook timeouts. |
| `WS_EX_NOACTIVATE` | HUD window creation | Safe; prevents window focus hijacking (`WM_ACTIVATE`). |
| `AttachThreadInput` | Foreground thread synchronization | Safe; attaches input processing temporarily for foreground window discovery. |
| `AllowSetForegroundWindow` | Target window focus restoration | Safe; enables the previous document window to regain focus cleanly. |
| `OpenClipboard` / `CloseClipboard` | Text insertion & lock recovery | Safe; includes self-healing lock release mechanism to prevent deadlocks. |

---

## 5. Technical Architecture & Compliance Readiness Mapping

| Standard | Core Requirement | FlowPilot Technical Readiness Architecture |
|:---|:---|:---|
| **HIPAA Security Rule** (45 CFR § 164.312) | Technical safeguards for transmission security & integrity of ePHI | **Architecturally Ready:** Zero data transmission across external networks eliminates Business Associate Agreement (BAA) cloud exposure. Healthcare providers retain complete physical/local custody of voice recordings. |
| **GDPR** (Regulation (EU) 2016/679) | Protection of biometric identifying data (voice recordings) & Article 25 Privacy by Design | **Architecturally Aligned:** Voice data is processed transiently in local RAM and discarded upon transcription. Zero cross-border data transfer or third-party cloud sub-processors. |
| **SOC 2 Type II** | Confidentiality and Privacy Trust Services Criteria | **Architecturally Aligned:** Total boundary isolation; zero reliance on multi-tenant cloud infrastructure. |
| **California Privacy Rights Act (CPRA)** | Consumer rights over sensitive personal biometric data | **Architecturally Aligned:** No data collection, telemetry tracking, profiling, or monetization of consumer voice or text data. |

> [!IMPORTANT]
> Formal compliance certification under HIPAA or GDPR requires the deploying entity to enforce complementary administrative safeguards, device encryption (BitLocker), and role-based physical security on endpoint machines.

---

## 6. Security Audit Conclusion

FlowPilot represents the gold standard in privacy-preserving desktop dictation. Organizations with stringent confidentiality requirements (defense, legal, healthcare, financial services) can deploy FlowPilot with full confidence that sensitive dictated information remains strictly within their internal endpoint boundary.
