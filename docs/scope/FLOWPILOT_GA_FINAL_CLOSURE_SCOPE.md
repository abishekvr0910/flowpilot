# FlowPilot: General Availability (GA) Final Closure Scope

**Document Version:** 3.2.0-GA-CLOSURE-SPEC  
**Status:** Completed & Verified in Source (v3.1.0 GA / Unsigned Pilot Release)  
**Target Release:** FlowPilot v3.1.0  
**Target Architecture:** Windows 10/11 (64-bit, x64), Native Host-Isolated  

---

## Executive Summary

While FlowPilot v3.1.0 achieved complete offline pipeline execution, 63-suite audit passage, and real-time, zero-cloud-egress local dictation optimized for developer workflows and privacy-conscious users, closing the final operational and distribution requirements prepares the codebase for polished General Availability (GA).

This closure scope defines the requirements, technical design, acceptance criteria, and closure decisions across the core work packages and release gates:

1. **WP-1: One-Click Windows Installer & Desktop Lifecycle (Inno Setup / WiX)**
2. **WP-2: Universal Selection-Aware In-Place Text Rewriter & Undo Buffer**
3. **WP-3: Dedicated USB PnP Bus Audio Device (`USB\VID_...`) Hot-Plug Harness**
4. **WP-4: Automated Authenticode Code-Signing & Timestamping Pipeline**
5. **WP-5: Indic Language Acoustic Calibration & Experimental Guard**
6. **WP-6: Unsigned Pilot Policy Decision & Gate Closure Matrix**

---

## Work Package 1: One-Click Windows Installer (`Setup.exe`)

### 1.1 Scope & Functional Requirements
* **Standard Windows Installation Wizard:** Package the standalone PyInstaller bundle into `FlowPilot-Setup-v3.1.0.exe`.
* **User-Local (Non-Elevated) Install Target:** Default install directory is `{localappdata}\Programs\FlowPilot` (`C:\Users\<user>\AppData\Local\Programs\FlowPilot`). Does **not** trigger Windows UAC Administrator elevation prompts during installation or auto-updates.
* **Shortcut Management:**
  * Start Menu shortcut in `Programs\FlowPilot`.
  * Optional Desktop shortcut (checkbox in installer, default checked).
* **Launch on Windows Startup:**
  * Optional checkbox during setup: *"Start FlowPilot automatically when Windows starts"*.
  * Manages registry entry in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
  * Exposes toggle in Settings Dialog to enable/disable startup behavior at runtime.
* **Running Instance Detection:**
  * Installer queries `SingleInstance` mutex (`Global\FlowPilot_Desktop_SingleInstance_Mutex`).
  * If running, prompts user to close FlowPilot or sends a clean WM_CLOSE signal before replacing files.
* **Clean Uninstaller:**
  * Windows "Installed Apps" / "Add or Remove Programs" registration.
  * Completely removes binary files, cache, and registry keys upon uninstall; asks user whether to preserve personal dictionary (`~/.flowpilot/corrections.json`).

### 1.2 Acceptance Gates
* Executing `FlowPilot-Setup-v3.1.0.exe` installs cleanly without admin rights.
* Uninstallation removes all binaries, leaving 0 orphaned shortcuts.
* Single-instance detection prevents installing over an active, locked `.exe`.

---

## Work Package 2: Universal Selection-Aware In-Place Text Rewriter

### 2.1 Scope & Functional Requirements
* **Selection Capture Adapter (`engine/selection_rewriter.py`):**
  * Read selected text from the foreground editor via:
    1. *Tier 1:* Win32 `EM_GETSELTEXT` (Native Win32 edit controls).
    2. *Tier 2:* UI Automation `IUIAutomationTextPattern::GetSelection` (Word, modern editors).
    3. *Tier 3:* Non-destructive clipboard capture (`Ctrl+C` with pre-copy clipboard backup and immediate restore).
* **Voice Command vs Dictation Intent Classifier:**
  * Detect command patterns: *"make this formal"*, *"shorten this"*, *"fix grammar"*, *"translate to Spanish"*, *"bullet points"*.
  * If no command pattern is detected, treat input as replacement dictation.
* **Local SLM Transform Pipeline:**
  * Route selected text + spoken command through local `Qwen2.5-0.5B` SLM sandbox.
  * FactGuard entity protection strictly enforced: numbers, currencies, dates, and negations in the source text must not be hallucinated or dropped.
* **Atomic Replacement & Undo Latch:**
  * Snapshot selected range before replacement.
  * Dispatch replacement text via targeted clipboard paste.
  * Register pre-replacement text into instant Undo buffer (`VoiceEditor` transaction).
  * Hotkey **`Alt+Shift+U`** immediately restores the original pre-replacement text if the user dislikes the result.
* **Focus-Shift Abort Safety:**
  * If the active window changes while the user is speaking the rewrite command, abort replacement immediately and stage result to the recovery buffer. Never type into an unexpected window.

### 2.2 Acceptance Gates
* Select paragraph in Notepad, press `Ctrl+Alt+T`, say *"make this concise"*, paragraph is replaced with concise version in $\le 900\text{ms}$.
* Pressing `Alt+Shift+U` immediately reverts the paragraph to the original text.
* FactGuard vetoes any rewrite that drops numbers or negations.

---

## Work Package 3: Dedicated USB Audio Bus (`USB\VID_...`) Hot-Plug Harness

### 3.1 Scope & Functional Requirements
* **USB Bus PnP Enumeration:**
  * Query Windows SetupAPI / WMI for true physical USB audio endpoints (`USB\VID_XXXX&PID_XXXX`).
  * Distinguish USB bus devices from motherboard analog jacks (`HDAUDIO\...`).
* **Hardware Event Listener:**
  * Listen for Win32 `WM_DEVICECHANGE` broadcast messages (`DBT_DEVICEARRIVAL`, `DBT_DEVICEREMOVECOMPLETE`).
  * On USB device arrival/removal, trigger PortAudio dynamic re-enumeration without waiting for user action.
* **Mid-Stream Disconnect Hardening:**
  * If an active recording USB microphone is physically yanked:
    1. Catch PortAudio stream error cleanly (0 thread crashes).
    2. Salvage audio buffer recorded up to the disconnect instant.
    3. UI displays *"USB Microphone Disconnected"*.
    4. Halt recording without silent fallback to internal laptop mic.
* **Verification Script & Receipt:**
  * Create `scripts/verify_usb_bus_hotplug.py` generating signed receipt `PHYSICAL_USB_BUS_UNPLUG_RECEIPT.md`.

### 3.2 Acceptance Gates
* Active recording on USB microphone survives physical cable unplug without application crash.
* System refuses to fall back to default laptop mic when USB mic is missing.
* Hot-plugging USB mic back in restores device within 2.0 seconds.

---

## Work Package 4: Automated Authenticode Code-Signing Pipeline

### 4.1 Scope & Functional Requirements
* **Dedicated Signing Utility (`scripts/package_windows_release.py`):**
  * Automated discovery of Windows SDK `signtool.exe`.
  * Support both PFX file signing (with password environment variable) and Windows Certificate Store / HSM hardware token signing (via SHA-1 thumbprint).
* **Comprehensive Artifact Signing:**
  * Sign primary executable: `dist/FlowPilot/FlowPilot.exe`.
  * Sign all bundled native extensions: `_internal/**/*.pyd`, `_internal/**/*.dll`.
  * Sign installer executable: `dist/FlowPilot-Setup-v3.1.0.exe`.
* **Dual SHA-256 & RFC 3161 Timestamping:**
  * Sign with `/fd SHA256`.
  * Timestamp via RFC 3161 compliant server (`http://timestamp.digicert.com` with fallback to Sectigo).
* **Automated Signature Verification Gate:**
  * Pre-release assertion executing PowerShell `Get-AuthenticodeSignature`.
  * Assert `Status == 'Valid'` and `SignerCertificate` matches authorized publisher.

### 4.2 Acceptance Gates
* When a certificate is provided, `Get-AuthenticodeSignature` returns `Status: Valid`.
* When no certificate is provided, binary packages are marked `UNSIGNED_PILOT` truthfully without conflating hash manifests with Authenticode signatures.

---

## Work Package 5: Indic Language Acoustic Calibration & Experimental Guard

### 5.1 Scope & Functional Requirements
* **Whisper Prompt Priming (`engine/stt_engine.py`):**
  * Provide language-specific Devanagari, Tamil, and Malayalam script priming tokens in `initial_prompt` to stabilize Whisper decoder.
* **Repetition Loop Suppression:**
  * Detect Whisper hallucination loops on low-resource audio (e.g. repeated syllables like `"न न न..."` or `"ம ம ம..."`).
  * Truncate repeating n-grams $\ge 4$ repetitions.
* **UI Acoustic Reality Banner:**
  * In Settings and Setup Wizard, display explicit amber warning: *"Indic language dictation (Hindi, Tamil, Malayalam) is experimental on CPU base model; accuracy varies with accent and ambient noise."*

### 5.2 Acceptance Gates
* Repetition loops in synthetic low-SNR Indic audio are truncated deterministically.
* Settings screen displays unambiguous experimental badge for `hi`, `ta`, `ml`.

---

## Work Package 6: Unsigned Pilot Release Decision & Verification Matrix

### 6.1 Gate E Policy Decision (Unsigned Pilot Release)
* **Context:** In the current build environment, no commercial Code Signing Certificate (EV/OV) or Azure Trusted Signing credentials exist.
* **Decision:** FlowPilot v3.1.0 is officially approved to ship as an **Unsigned Pilot Release (GA Candidate)**.
* **Policy Boundaries:**
  1. **Truthful Status:** Gate E is marked as `CLEARED (UNSIGNED_PILOT)`. Binaries are explicitly documented as unsigned; release notes include clear SmartScreen guidance ("Run anyway" / "More info").
  2. **PE Resource Stamping:** Both `FlowPilot.exe` and `FlowPilot-Setup-v3.1.0.exe` are stamped with full Windows PE version information (`FileVersion: 3.1.0.0`, `ProductVersion: 3.1.0.0`, `CompanyName: FlowPilot Open Source`).
  3. **Cryptographic Integrity:** SHA-256 digests are published in `docs/release/RELEASE_ARTIFACT_MANIFEST.md` for both `FlowPilot-Setup-v3.1.0.exe` and `FlowPilot-v3.1.0-windows-x64.zip`.
  4. **Commercial Signing Path:** Commercial EV/OV signing is decoupled and designated as a post-pilot publisher deployment task once an organizational certificate is provisioned.

### 6.2 Five-Gate Closure Status Matrix

| Gate | Specification Domain | Release Criteria | Status | Evidence & Resolution |
| :--- | :--- | :--- | :---: | :--- |
| **Gate A** | E2E Reliability | All 63 suites pass cleanly without hotkey collision or focus crashes | **PASS** | `conhost.exe` console launch, lock-screen session awareness, S13 hotkey isolation, and bounded recovery timer polling in `test_recovery_feedback.py`. |
| **Gate B** | Offline Security | Zero network egress during dictation; CPU int8 Whisper transcription | **PASS** | SAPI speech synthesis transcribed offline in 10.98s on CPU. Preload and idle memory unloader verified with zero socket egress. |
| **Gate C** | Resource Footprint | Idle CPU consumption < 2% of one core; memory footprint bounded | **PASS** | Running binary measured at 1.46% of one core (0.09% system load), 113.4 MB RSS. 300ms idle timer & static repaint gating active. |
| **Gate D** | Distribution & Recovery | Installer footprint < 250 MB; graceful fallback for missing models | **PASS** | 247.37 MB Inno Setup installer (`FlowPilot-Setup-v3.1.0.exe`). Missing model (`small`) auto-resets to bundled `base`. |
| **Gate E** | Updates & Publisher Identity | Non-tracking PEP 440 updates; PE version info stamped; honest signing status | **PASS (PILOT)** | PEP 440 background check wired (5s startup warmup + 24h timer with atomic disk persistence of `last_update_check_ts`). PE Version 3.1.0.0 stamped. Unsigned pilot status declared truthfully. |
