# FlowPilot Changelog

This page distinguishes published releases from work on `master`. Check [GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases) for downloadable artifacts and [GitHub Actions](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) for current verification status.

## Unreleased source changes (GA Final Closure)

- **Inno Setup 1-Click Zero-Admin Windows Installer (WP-1):** Production Inno Setup script (`installer/flowpilot_setup.iss`) and packaging pipeline (`scripts/package_installer.py`) targeting `{localappdata}\Programs\FlowPilot` without admin UAC elevation prompts, managing single-instance mutex detection, desktop/start shortcuts, and clean uninstallation.
- **Universal Selection Rewriter & Instant Undo Latch (WP-2):** In-place selection replacement engine (`engine/selection_rewriter.py`) with instant rollback via **`Alt+Shift+U`**. Enforces FactGuard entity preservation, focus shift detection, terminal window protection, and credential window safety.
- **Dedicated USB Audio Bus Hot-Plug Harness (WP-3):** Hardware-level PnP USB audio verification harness (`scripts/verify_usb_bus_hotplug.py`) validating hardware ID persistence and strict `DEVICE_MISSING_SENTINEL = -9999` refusal without silent microphone fallback.
- **Authenticode Code Signing Pipeline (WP-4):** Automated Authenticode signing pipeline (`scripts/sign_authenticode.py`) with Windows SDK `signtool.exe` discovery, SHA-256 digests, dual RFC 3161 timestamping (DigiCert / Sectigo fallbacks), and signature verification.
- **Universal Repetition Loop Suppression (WP-5):** Regex token loop suppression (`(?u)(?:^|\s)(\S+)(?:\s+\1){2,}(?=\s|$)`) eliminating acoustic repetition loops across Indic (Hindi, Tamil) and English speech.
- **Reserved Shortcut Collision Protection:** Registered `Alt+Shift+U` in `RESERVED_FLOWPILOT_SHORTCUTS` alongside `Alt+Shift+Z` and `Alt+Shift+X`, ensuring dictation key reassignments cannot collide with recovery shortcuts.

- Removed obsolete cloud controls from the optional web companion. Unsupported cloud settings are rejected by the API, and old unused cloud keys are removed from the active local config on load.
- Moved superseded verification and agent status reports into the dated archive, removed tracked scratch probes, and replaced workstation-specific public links.

## v3.1.0-RC11 — October 28, 2026

- **Caret-Aware Context Formatting:** Real-time Win32 `EM_GETSEL` and UIA `IUIAutomationTextPattern` surrounding text inspection; suppresses mid-sentence capitalization, duplicate punctuation, and trailing periods before following lowercase text.
- **Automatic Correction Learning & Persistence:** Automatic detection of user buffer replacements post-injection with occurrence thresholding, atomic disk persistence (`~/.flowpilot/corrections.json`), and UI suggestion cards in `DictionaryView`.
- **Background Idle Model Memory Unloader:** Background orchestrator idle timer releasing 1.0–2.0 GB RAM from local Faster-Whisper and SLM workers during periods of inactivity with transparent, zero-cost reacquisition on subsequent dictation calls.
- **Two-Track Meeting Audio Separation:** WASAPI loopback system audio capture with acoustic energy bleed suppression, ensuring loud remote speaker turns do not leak into local mic turns.
- **Synthetic Modifier Safety:** Hardened modifier release gate ensuring physical keys are unpressed before paste dispatches, tagging synthetic events with `'FPLT'` (`0x46504C54`).

## v3.1.0 — October 20, 2026

- **Multilingual Offline Dictation:** Added tested acoustic support for German, French, Spanish, Japanese, Chinese, and Hindi using bundled Faster-Whisper base weights with zero network calls.
- **Microphone Device Switching:** Input audio device selection in Settings Dialog and First-Run Wizard binds dynamically to the recorder stream without requiring application restart.
- **Immediate Personalization:** Custom dictionary biasing and voice snippet expansions apply immediately to live dictation upon save without reloading the application.
- **Safe "Paste Last" Injection:** Prevents blind keystrokes into FlowPilot's own windows (HUD, Dashboard, Tray), automatically restores focus to the previously active external editor, or safely stages to the clipboard.
- **Slow-App Paste Resilience:** Introduced window-class adaptive timing profiles (dwell, hold, post-paste) for Outlook, Word, WhatsApp, remote desktop, and JetBrains IDEs.
- **Text Injector Hardening:** Eliminated copy-failure UnboundLocalError; added focus-loss pre-dispatch abort with clipboard preservation and sequence guard against clipboard overwrite during hold.
- **Truthful Status Reporting:** Distinguishes `CONFIRMED_INSERTED`, `SENT_UNVERIFIED`, and `FAILED_RECOVERY_AVAILABLE` in the HUD and tray, with dedicated instant recovery hotkeys (`Shift+Alt+Z` to paste last dictation, `Shift+Alt+X` to copy last dictation).
- **First-Run Onboarding & Key Customization:** Added 5-step local Setup Wizard supporting single-key push-to-talk (e.g. `F9`) and conflict exemption protecting assigned recovery shortcuts (`Alt+Shift+Z`, `Alt+Shift+X`, `Ctrl+Alt+T`) from collision.
- **Companion Studio & Dictation Vault:** Pixel companions, meeting notes, productivity insights, and local dictation History Vault with never-store mode support.

## v3.0.2 — published October 15, 2026

- Windows portable release: [`FlowPilot-v3.0.2-win64.zip`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release).
- The dated [release evaluation](docs/release/FLOWPILOT_V302_RELEASE_REPORT.md) records the hardware and corpus used for its measurements. Those results apply to that release, not automatically to later source.

Earlier engineering notes are retained as [historical snapshots](docs/archive/README.md); they are not a live feature list or current test report.
