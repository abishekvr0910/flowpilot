# FlowPilot Changelog

This page distinguishes published releases from work on `master`. Check [GitHub Releases](https://github.com/abishekvr0910/flowpilot/releases) for downloadable artifacts and [GitHub Actions](https://github.com/abishekvr0910/flowpilot/actions/workflows/ci.yml) for current verification status.

## v3.2.0 — November 4, 2026

- **Adaptive 0.85s Speech-Onset Pre-Roll:** Dynamically retains up to 0.85s of pre-hotkey speech in `AudioRecorder` while maintaining a 0.35s quiet-room floor, dropping casual early speech-onset WER from **22.3% to 13.5%**.
- **95-Tap Windowed-Sinc Anti-Aliasing Resampling:** Replaced linear interpolation in `resample_audio` with a 95-tap Blackman-windowed sinc FIR low-pass filter ($>50\text{ dB}$ stopband attenuation), dropping 48 kHz WASAPI noise-aliased WER from **58.3% to 28.3%** (+14.7% penalty down from +44.7%).
- **Exact CTC Prefix Beam Search & Lexical Biasing:** Upgraded `OnnxASRHarness` with prefix beam search recombining blank/non-blank paths in log space and boosting custom vocabulary tokens. Reduces Mozilla Common Voice Tamil CER from **4.44% to 3.97%**.
- **Pause-Anchored Streaming Prefix Pre-Decoder:** Implemented `get_active_recording_snapshot`, `build_pause_prefix_checkpoint`, and `transcribe_with_checkpoint` in `STTEngine` and `FlowOrchestrator`, pre-decoding completed clauses during mid-utterance pauses to cut post-stop P95 latency by **~300 ms** and multi-clause WER to **12.5%**.
- **Active-Window Context Symbol Harvesting & Multilingual Self-Correction:** Added `WindowInspector.extract_context_vocabulary` (with strict password manager and private browsing exclusions), spoken CamelCase symbol restoration (`onnx asr harness` $\rightarrow$ `OnnxASRHarness`), and full `scratch that` + Polish `nie czekaj`, `czekaj`, `przepraszam` self-corrections with zero FactGuard rollbacks (100% pass rate).
- **Windows Clipboard Privacy & Cloud Sync Exclusion:** Native Win32 `CanIncludeInClipboardHistory` and `CanUploadToCloudStore` zero-flag registration in `TextInjector`, ensuring dictated text is never indexed in Windows Clipboard History (`Win+V`) or synced across devices to the cloud.
- **Hardware Scan Code Terminal Key Mapping:** Mapped `ord('V')`, `VK_CONTROL`, `VK_SHIFT`, and `VK_INSERT` through `win32api.MapVirtualKey(..., 0)` so terminal emulators (VS Code xterm.js, Windows Terminal, mintty) never produce raw `^V` control sequences on non-US or localized keyboard layouts.
- **User-Scriptable Python Transforms Engine:** Native custom transform execution engine in `engine/user_transforms.py` reading user hooks from `~/.flowpilot/transforms.py`, matching and exceeding Hex's config system without external Node.js or QuickJS runtimes.
- **Suite 68 Automated Audit Test:** Added `tests/test_wispr_leapfrog_upgrades.py` validating pre-roll adaptation, filter attenuation, CTC beam search recombination, streaming prefix checkpoints, context symbol harvesting, user transforms, and clipboard privacy flags.

## v3.1.3 — November 4, 2026

- **1-Click UI Model Provisioning for Tamil & Polish:** Added explicit, SHA-256-verified on-demand download actions in both `SettingsDialog` and first-run `SetupWizard` for **AI4Bharat IndicConformer Tamil Specialist (131 MB)** from `models-v1` and **Whisper Small (461 MB)** for Polish (`pl`) and Indic languages, alongside proactive system tray guidance when switching languages via `Ctrl+Alt+L` or the tray menu.
- **Frozen Bundle & User Profile Model Resolution:** Updated `OnnxASRHarness` to resolve `~/.flowpilot/models/indicconformer-{lang}`, `FLOWPILOT_MODEL_DIR`, and PyInstaller frozen `_MEIPASS` / `_internal` directories so installed `FlowPilot.exe` users load downloaded specialist models out of the box without developer workspaces.
- **NeMo-Exact Acoustic Frontend & CTC Boundary Repair:** Upgraded `OnnxASRHarness.extract_features` to NVIDIA NeMo's Slaney mel scale, triangle-area filterbank normalization, `0.97` pre-emphasis, centered `n_fft=512` STFT (`win_len=400`), and CTC subword lateral geminate boundary repair (`ள்ல்` / `ல்ள்`). Reduces Mozilla Common Voice Tamil read-speech WER from **22.0% to 18.5%** (**4.4% CER**, 3.93x faster than Whisper Small on CPU) and casual conversational Tanglish WER from **51.5% to 42.4%**.
- **Pure-NumPy Audio Resampling:** Replaced optional `scipy.signal.resample_poly` usage in `OnnxASRHarness` with FlowPilot's native `engine.audio_recorder.resample_audio`, ensuring 44.1 kHz / 48 kHz inputs resample cleanly inside the minimal ~221 MB frozen runtime without `scipy`.
- **User-Data Safety in Live Notepad Test Harness:** Isolated `tests/notepad_harness.py` via PID and window snapshots (`_OWNED_TEST_HWNDS` / `_OWNED_NEW_PIDS`) so live desktop verification never touches or closes pre-existing user Notepad windows or persisted Windows 11 `TabState` sessions.
- **GitHub Actions CI Green & Node 24 Modernization:** Added a CC0 public-domain Mozilla Common Voice Tamil speech fixture (`tests/fixtures/ta-commonvoice-sample.wav`), provisioned `indicconformer-ta` into `~/.flowpilot/models` post-PyInstaller in CI, upgraded GitHub Actions to `v7` (Node 24), and configured `versioning-strategy: increase-if-necessary` for Dependabot.
- **Authenticode CLI & Installer Sidecar Checksums:** Added CLI argument and environment certificate handling to `scripts/sign_authenticode.py` and automatic `.sha256` sidecar generation plus optional signing in `scripts/package_installer.py`.

## v3.1.2 — November 3, 2026

- **Clean Minimal Runtime Rebuild:** Built exclusively in a clean Python 3.11 virtual environment from `requirements.txt`, eliminating extraneous dependencies (`scipy`, `cryptography`, `aiohttp`, `aioquic`) and restoring the streamlined ~221 MB installer footprint and ~16 MB executable size.
- **Accurate Model Provisioning & Benchmark Metrics:** Clarified that the Tamil specialist ASR model is provisioned on demand from public release assets (`models-v1`) rather than bundled in the base installer. Recorded benchmark figures of 22.0% WER / 3.0% CER on Mozilla Common Voice read speech and 4.3x CPU speedup over Whisper `small`.
- **Regression Test Verification:** Integrated pre-flight URL verification in `tests/test_model_downloader.py`.

## v3.1.1 — November 3, 2026

- **Password Field Dictation & History Safety:** Enforced strict non-retention and blocked dictation in password fields (`ES_PASSWORD`, `UIA_IsPasswordPropertyId`). Text spoken into password fields is discarded immediately and never retained for re-paste or written to the History Vault.
- **Specialist Multilingual ASR (IndicConformer for Tamil):** 100% offline, zero cloud egress ASR harness running AI4Bharat IndicConformer Medium (INT8 Quantized, 137 MB) via ONNX Runtime.
- **Tamil Unicode Boundary Repair:** Deterministic subword token joining repairing doubled consonants at boundaries (`தாவிக்கொண்டு`) and composing disjoined vowels without dropping grammatical letters.
- **Context-Aware Colloquial Tanglish Loanwords:** Dual-mode script toggling (Tamil script vs Tanglish Latin phonetics). Restores 75+ colloquial English loanwords (`time`, `meeting`, `start`, `lunchukku`, `correct-aana`) with context-aware verbal disambiguation for homophones like `கால்` (mapping to English `call` when collocated with verbal auxiliaries like `பண்ணு`, preserving genuine Tamil in `கால் கிலோ` as `kaal kilo` and `ஒரு கோடு போடு` as `oru kodu podu`).
- **Conditional Specialist Preload:** IndicConformer session preloads only when active language is Tamil (`ta`) or `auto`, saving ~168 MB RAM and 1.8s startup overhead during English dictation, with dynamic background preloading on `Ctrl+Alt+L` language quick-switch.
- **Model Provisioning & Integrity Verification:** Integrated `indicconformer-ta` into `engine/model_downloader.py` with SHA-256 hash validation for on-demand setup, preserving the lightweight <250 MB installer footprint.

## v3.1.0 — November 2, 2026

- **Inno Setup 1-Click Zero-Admin Windows Installer:** Production Inno Setup script (`installer/flowpilot_setup.iss`) and packaging pipeline (`scripts/package_installer.py`) targeting `{localappdata}\Programs\FlowPilot` without admin UAC elevation prompts, managing single-instance mutex detection, desktop/start shortcuts, and clean uninstallation.
- **Universal Selection Rewriter & Instant Undo Latch:** In-place selection replacement engine (`engine/selection_rewriter.py`) with instant rollback via **`Alt+Shift+U`**. Enforces FactGuard entity preservation, focus shift detection, terminal window protection, and credential window safety.
- **Dedicated USB Audio Bus Hot-Plug Harness:** Hardware-level PnP USB audio verification harness (`scripts/verify_usb_bus_hotplug.py`) validating hardware ID persistence and strict `DEVICE_MISSING_SENTINEL = -9999` refusal without silent microphone fallback.
- **Authenticode Code Signing Pipeline:** Automated Authenticode signing pipeline (`scripts/package_windows_release.py`, `scripts/sign_authenticode.py`) with Windows SDK `signtool.exe` discovery, SHA-256 digests, and RFC 3161 timestamping.
- **Universal Repetition Loop Suppression:** Dual token and multi-word phrase loop suppression eliminating acoustic repetition loops across Indic (Hindi, Tamil) and English speech.
- **Reserved Shortcut Collision Protection & Cloud Key Purge:** Registered `Alt+Shift+U` in `RESERVED_FLOWPILOT_SHORTCUTS` alongside `Alt+Shift+Z` and `Alt+Shift+X`, and removed obsolete cloud controls and unused cloud config keys on load.

## v3.1.0-RC11 — October 28, 2026

- **Caret-Aware Context Formatting:** Real-time Win32 `EM_GETSEL` and UIA `IUIAutomationTextPattern` surrounding text inspection; suppresses mid-sentence capitalization, duplicate punctuation, and trailing periods before following lowercase text.
- **Automatic Correction Learning & Persistence:** Automatic detection of user buffer replacements post-injection with occurrence thresholding, atomic disk persistence (`~/.flowpilot/corrections.json`), and UI suggestion cards in `DictionaryView`.
- **Background Idle Model Memory Unloader:** Background orchestrator idle timer releasing 1.0–2.0 GB RAM from local Faster-Whisper and SLM workers during periods of inactivity with transparent, zero-cost reacquisition on subsequent dictation calls.
- **Two-Track Meeting Audio Separation:** WASAPI loopback system audio capture with acoustic energy bleed suppression, ensuring loud remote speaker turns do not leak into local mic turns.
- **Synthetic Modifier Safety:** Hardened modifier release gate ensuring physical keys are unpressed before paste dispatches, tagging synthetic events with `'FPLT'` (`0x46504C54`).

## v3.1.0-pilot — October 20, 2026

- **Multilingual Offline Dictation:** Added tested acoustic support for German, French, Spanish, Japanese, Chinese, and Hindi using bundled Faster-Whisper base weights with zero network calls.
- **Microphone Device Switching & Immediate Personalization:** Dynamic input audio device binding and immediate custom dictionary / snippet expansion updates without application restart.
- **Safe "Paste Last" Injection & Slow-App Paste Resilience:** Window-class adaptive timing profiles and focus-loss pre-dispatch abort with clipboard preservation.
- **Truthful Status Reporting & First-Run Onboarding:** Distinguishes `CONFIRMED_INSERTED`, `SENT_UNVERIFIED`, and `FAILED_RECOVERY_AVAILABLE` in the HUD and tray, paired with a 5-step local Setup Wizard and Companion Studio.

## v3.0.2 — published October 15, 2026

- Windows portable release: [`FlowPilot-v3.0.2-win64.zip`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release).
- The dated [release evaluation](docs/release/FLOWPILOT_V302_RELEASE_REPORT.md) records the hardware and corpus used for its measurements. Those results apply to that release, not automatically to later source.

Earlier engineering notes are retained as [historical snapshots](docs/archive/README.md); they are not a live feature list or current test report.
