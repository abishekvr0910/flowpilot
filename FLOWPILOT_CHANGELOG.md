# FlowPilot Changelog

This page distinguishes published releases from work on `master`. Check [GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases) for downloadable artifacts and [GitHub Actions](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) for current verification status.

## Unreleased source changes

- Removed obsolete cloud controls from the optional web companion. Unsupported cloud settings are rejected by the API, and old unused cloud keys are removed from the active local config on load.
- Moved superseded verification and agent status reports into the dated archive, removed tracked scratch probes, and replaced workstation-specific public links.

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
