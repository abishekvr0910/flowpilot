# Windows Dictation Head-to-Head: FlowPilot vs Wispr Flow

**Status (2026-10-19):** Protocol ready; no comparable live results or decrypted Wispr capture have been collected. The local Wispr installation inspected for version identity is 1.6.1174. Record the FlowPilot commit, Wispr version, Windows build, CPU, microphone route, and model size with every run. The repeated-Notepad failure mechanism and patch are documented in [the insertion RCA](NOTEPAD_INSERTION_RCA.md). A local interactive-desktop regression run passed **38/38 suites** in 102.21 seconds; that is not a Wispr head-to-head result or a release-artifact check.

**Host setup snapshot (2026-10-18):** An isolated mitmproxy 11.0.2 install under ignored `scratch/benchmark-tools` passed a command-scoped HTTPS interception test on `127.0.0.1:8899`. Persistent current-user CA trust was rejected as too broad, so Wispr TLS was not decrypted and no system/global proxy settings were changed. The signed official VB-Cable Pack45 driver was installed: its WASAPI `CABLE Input` playback and `CABLE Output` recording endpoints passed a one-second 48 kHz synthetic-tone loopback test (captured RMS 0.11177, peak 0.28185). We did not intentionally change default audio devices, but a post-install check found Windows/PortAudio's default speaker output pointed at `CABLE Input`; the prior output route was not recorded, so it must be selected explicitly rather than guessed. The default microphone then remained `Microphone Array (Intel Smart Sound)`. The vendor required a reboot to finalize driver installation; reboot status was not reverified for this record. One idle `netstat` snapshot showed three established TLS connections owned by Wispr processes; it did not expose hostnames, request bodies, codec, or dictation traffic.

## After-restart readiness checklist

1. Confirm the VB-Cable driver survived the reboot and that both `CABLE Input` (playback) and `CABLE Output` (recording) appear in Windows Sound settings. If ordinary speakers are silent, restore your preferred physical/Bluetooth device as the **default output**; do not leave VB-Cable as the system default just to run the benchmark.
2. For each controlled trial, route the WAV player to `CABLE Input` and select `CABLE Output` as the microphone inside **each** dictation app. Device numeric indices can change after reboot, so select by name. Leave the normal system microphone and speaker defaults alone.
3. The ignored `scratch/benchmark-tools` binaries and local proxy configuration persist, but the listener does not auto-start after reboot. No Wispr traffic capture, system proxy routing, or certificate trust is configured. Revisit proxy consent and a disposable test account before trying to decrypt traffic; do not use real credentials, conversations, clipboard text, or private files.
4. Re-run the cable tone test, then the paired WAV benchmark. Keep the network protocol table below as **not measured** until attributed evidence is actually captured. Record the exact source commit and installed artifact for each run.

This is a behavior and performance comparison, not a copy of proprietary code or a security certification. Use a disposable Windows test account and synthetic, non-sensitive text. Do not commit raw traffic captures, auth tokens, audio containing real conversations, or personal clipboard contents.

## Phase 1 — Observed Wispr network protocol

1. Install and start one standard local capture tool (Fiddler, Charles, or equivalent) on the test machine. Trust its local CA for that test account only. Verify that the Wispr process actually routes through the proxy; do not assume Windows proxy settings cover every transport. Do not disable certificate validation or bypass application pinning. If TLS decryption fails, record only visible DNS/IP/SNI, timing, and byte counts; mark payload fields unknown.
2. With all unrelated apps closed, make one test dictation using a generated canary phrase. Repeat with two rapid utterances. Record process ID, app version, connection IDs, request/response timestamps, endpoint host and path, method, content type, message framing, compressed and uncompressed byte lengths, and status/error frames. Store only sanitized field names/types and length summaries in this repository.
3. Probe context separately: put distinct synthetic canaries in a foreground test window title, focused edit field before/after the cursor, and clipboard. Dictate another unrelated phrase. Search only the decrypted, attributed Wispr requests for those canaries. A missing canary is evidence only for that captured path and configuration—not proof of global absence. Never inspect real user content.
4. Record payload codec and sample rate only when headers or decoded frame/container metadata establish them. Packet size alone cannot distinguish PCM, Opus, or resampling. Distinguish capture start, last audio send, first response byte, completed response, and visible insertion. Request duration is **not** pure server computation time.

| Protocol evidence field | Required observation | Result |
| --- | --- | --- |
| Endpoint/method/path | Decrypted attributed request or official public API documentation | Not measured |
| REST vs WebSocket/gRPC | Observed HTTP upgrade/content type/framing | Not measured |
| Audio codec/sample rate/chunk interval | Decoded payload metadata and consecutive frame timestamps | Not measured |
| Audio and context payload schema | Sanitized field names/types from attributed requests | Not measured |
| Clipboard/window-title canaries | Exact synthetic canary match in complete attributed capture | Not measured |
| Network request duration/payload overhead | Capture timestamps and encoded byte lengths | Not measured |
| Back-to-back buffering | Two tagged utterances and their request/insertion order | Not measured |

Wispr's current public documentation says desktop dictation uses cloud processing, and Context Awareness can include text from the active app; it says screenshots are not taken. These are vendor disclosures, not observations of this particular session. See its [privacy overview](https://docs.wisprflow.ai/articles/3467817258-security-and-compliance-faq) and [Context Awareness guide](https://docs.wisprflow.ai/articles/4678293671-Context-Awareness).

## Phase 2 — Same-audio live benchmark

Create a private fixture manifest with `id,condition,wav_sha256,spoken_reference,expected_identifiers,source,consent`. Use 16-bit PCM WAVs with consistent level and explicit sample rate. Play each file into the same verified virtual microphone input for both applications; confirm both select that input. Do **not** use speakers-to-physical-microphone playback as a fair substitute. Randomize tool order across runs, reset the target field between trials, and keep model, language, style, and dictionary settings recorded rather than silently changing them.

| Condition | Minimum fixture design | Output target |
| --- | --- | --- |
| Quiet speech | Human whisper and low-volume speech, separately labeled | Notepad and IDE |
| Noise | Same clean utterance mixed with documented fan/typing recordings at two SNRs | Notepad |
| Developer text | Exact `camelCase`, `snake_case`, CLI flags, paths, and fenced-code dictation | VS Code/Cursor and terminal |
| Back-to-back | Pairs at 0, 250, and 750 ms inter-utterance gaps | Notepad |
| Paste stress | Slow-rendering editor, deliberately unfocused target, and clipboard change during injection | Target-specific |

For each trial record: tool/version, fixture SHA-256, start/stop monotonic timestamps, visible-text timestamp from the **same external observation method**, output text, target, injection outcome, recovery action, process-tree peak RAM and CPU, disk paths/sizes created, and whether the output was verified. Use 100 paired trials for a meaningful primary p95 latency estimate; smaller category samples are exploratory. Report per-condition sample size and failure count. Blind-review text output before revealing which tool produced it.

Metrics: WER = `(substitutions + deletions + insertions) / reference words`; identifier-token error = incorrect protected identifiers / reference identifiers; factual-token error = incorrect numbers, negations, dates, amounts, or CLI flags / reference protected tokens. Compute stop-to-visible-text p50/p95 from successful and failed trials separately; never drop failures silently. For insertion success, distinguish confirmed, sent-but-unverified, and failed. Report process-tree RAM/CPU and the observation window. Disk residue means files remaining after the app exits and its documented cleanup window has elapsed.

The existing `tests/benchmark_corpus.py` evaluates FlowPilot's local STT/polish stages with SAPI-synthesized audio. It is not a live Wispr comparison or a full stop-to-visible-text benchmark.

### Empirical Trial Results (2026-10-19 VB-Cable Loopback Run)

Controlled loopback execution routed 15 synthetic speech WAV fixtures through WASAPI `CABLE Input` (14) at 48 kHz and captured them via `CABLE Output` (18). The figures below describe **FlowPilot-only exploratory processing**, not paired visible-text results. Wispr was observed as a running host process tree in these trials.

| Metric | FlowPilot observation | Important boundary |
| --- | --- | --- |
| Acoustic routing | CABLE Input to CABLE Output at 48 kHz | Loopback was verified; device indices can change. |
| Transcription + formatting time | p50 **561.1 ms**, p95 **999.0 ms** | Starts when the WAV buffer is delivered; excludes capture, UI insertion, and visibility verification. |
| Word error rate | Raw **21.26%**; cleaned **12.18%** | Raw and cleaned outputs use **different** spoken versus formatted references, so this is not proof that formatting halved acoustic errors. |
| Developer identifiers | **15/16** matched (93.8%) | Small synthetic SAPI corpus; not general developer-speech accuracy. |
| Factual tokens | **34/40** matched (85.0%) | Negation behavior was checked only on the listed samples. |
| Memory snapshot | **75.8 MB** (2 processes observed) FlowPilot baseline | Sampled before model load; reaches ~280 MB after Faster-Whisper base INT8 load. A separate Wispr snapshot showed 1,286.2 MB across 12 processes. |
| Headless insertion outcome | `FAILED_RECOVERY_AVAILABLE` safe abort | When running in a background/headless environment without an active window (HWND=0), TextInjector safely aborted Ctrl+V paste and preserved text in the recovery buffer. |
| Network test | Selected dictation paths attempted no non-loopback sockets under test instrumentation | Not an all-runtime byte-count certification. Wispr protocol/payload was not measured. |

Per-trial metadata, short SHA-256 prefixes, RMS levels, and raw versus cleaned outputs are recorded in [`vbcable_benchmark_results.json`](vbcable_benchmark_results.json). Full fixture hashes and WAV files were not preserved in this public record, so the 15-trial numbers cannot be independently reproduced from this repository alone.

## Phase 3 — Scoped FlowPilot implementation units

### A. Never-store dictation history (implemented in this sprint)

`save_history_text: false` gates vault, legacy history, insights, and pilot metrics writes for new dictations. The in-memory last-dictation recovery buffer remains. The vault opens without creating an empty history file or directory. Existing saved history and meeting notes are not erased by switching modes. Acceptance: no vault or WAV creation in a fresh profile, no config history append, and opt-in persistence still works. See `tests/test_transforms_and_history.py`.

### B. Recovery without accidental duplicate insertion (implementation spec)

Keep a single in-memory recovery record keyed by `session_id`: final text, target HWND/process, original injection status, and optionally the final audio bytes with a short expiry. Expose a **Paste Last** action separately from **Copy Last**. An automatic retry is allowed only after `FAILED_RECOVERY_AVAILABLE` or a provably absent insertion. Never auto-retry `SENT_UNVERIFIED`; an opaque editor might already contain the text. A manual paste may intentionally repeat text and must show the destination and prior status. Before insertion, verify the current HWND and focused field; if focus moved, do not force it back. Make retry idempotent by session token while a prior attempt is in flight. Re-transcription uses retained in-memory audio in never-store mode or the existing opt-in vault; never create a retry WAV. Clear the buffer on expiry, shutdown, or explicit forget.

Acceptance: confirmed insertion is not auto-duplicated; opaque targets require manual confirmation; focus change aborts safely; rapid clicks produce at most one in-flight paste; clipboard sequence guard preserves newer user copies; no-store retry leaves no audio file.

### C. Local focused-field context (implementation spec)

Create a Windows-only UI Automation reader behind a `FocusedContextReader` interface. Its single COM worker thread owns UIA objects; the dictation pipeline waits at most **500 ms** for an immutable result, then continues with current process-name profiles. Drop stale results by session ID and never accumulate more than one queued request. First check `IsPassword`, sensitive control types, process denylist, and focused HWND; fail closed before reading value/text patterns. Read at most 128 characters around the caret and at most 50 local IDE workspace filenames, only when the user opts in. Do not capture screenshots, enumerate clipboard data, persist context, or send it to a remote service. Preserve FactGuard's numeric/negation/identifier checks after context-assisted formatting.

Acceptance: password fields yield no content; UIA hang cannot delay injection beyond 500 ms; context never changes numbers or negations; zero outbound sockets; focus remains in the editor; disabled mode performs no UIA reads.

### D. Slow-app adaptive injection and recovery shortcuts (Wispr Flow alignment)

Wispr Flow's official paste guidance identifies that heavy web/Electron applications (Slack, Notion, Discord, Teams, Word, Outlook, WhatsApp) and virtual desktop environments (RDP/VMs) require:
1. **Adaptive Clipboard Hold Buffer:** Rather than restoring original clipboard contents after a fixed 1.5s, FlowPilot now adaptively extends the clipboard hold buffer to **3.5 seconds** for heavy/Electron apps and **5.0 seconds** for remote desktops (`mstsc.exe`, `vncviewer.exe`). This prevents slow applications from reading the restored pre-dictation clipboard before they have finished processing the paste.
2. **Keystroke Dwell Pacing:** Keystroke event duration (`time.sleep`) between `VK_CONTROL` and `V` is adaptively increased from 20ms to 40ms (50ms on remote desktops) to avoid key event drops under heavy main-thread UI load.
3. **Dedicated Instant Recovery Shortcuts:**
   - **Paste Last Dictation:** `Shift + Alt + Z` (and `Alt + Shift + Z`)
   - **Copy Last Dictation:** `Shift + Alt + X` (and `Alt + Shift + X`)
   If target application focus changes or an opaque application drops a paste, users can press `Shift + Alt + Z` directly in their target window to paste the recovery buffer, or `Shift + Alt + X` to copy it.
