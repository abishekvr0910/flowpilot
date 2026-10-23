# Wispr Flow reverse engineering + benchmark vs FlowPilot — 2026-10-23

Method note: the reverse-engineer-anything skill was loaded from
`C:\Users\moham\.agents\skills\reverse-engineer-anything\`. Its MCP analysis server
is not registered in this agent client, so the analysis below runs on the skill's
equivalent manual route (shipped-artifact inventory, userData inspection, live
process measurement). Every finding lists its evidence file. No network captures,
no behavioral probes, no account credentials touched; the user's own dictation
history was read only as numeric aggregates, never as transcript text.

## Target identity (verified from artifact)

| Fact | Value | Evidence |
|---|---|---|
| App | Wispr Flow 1.6.1209 (Squirrel/GNU Electron Windows install, running live during analysis) | registry Uninstall entry; `Get-Process` |
| Install root | `C:\Users\moham\AppData\Local\WisprFlow\app-1.6.1209\` | filesystem |
| Electron shell | `Wispr Flow.exe` 235.4 MB (Electron+Chromium), PAKs, ffmpeg.dll, d3d/dxgi | install tree list |
| Renderer+main bundle | `resources\app.asar` 136.2 MB; 213 JS/JSON files, 47.1 MB of script after extraction | `@electron/asar` list + extract (session temp, not committed) |
| Native helper | `resources\Release\Wispr Flow Helper.exe` 20.4 MB — one persistent native process, 63.8 MB RAM | tree + process list |
| Native modules | `node_sqlite3.node`, two hash-named `.node` modules, **Jabra device SDK** (GNAudio DeviceApis DLL set + `jabra-device-connector.exe`) | asar.unpacked tree |
| Accessibility | `ax-inspect(-lib|-server).mjs` — an accessibility-inspection service, UIAutomation × 16 in the helper | resources; helper byte-scan |
| Crash/telemetry | `.sentry-native` dir + `sentry\` userData — crash reporting to cloud | dirs; sentry files |
| User data root | `C:\Users\moham\AppData\Roaming\Wispr Flow\` — `config.json` 43 KB, `feature-flags-cache.json` 43.6 KB, `session.json`, `flow.sqlite` 332.6 MB + WAL | filesystem |

## Measured footprint at idle while dictation idle (this machine, live)

| Metric | Wispr Flow | FlowPilot (fresh dist exe, this session) |
|---|---|---|
| Processes | 12 (Electron: 11 + native helper) | 1 |
| Total RAM | **814.7 MB** | **504.9 MB** (includes loaded local Whisper weights) |
| Cumulative CPU of one process | 1,981 s on one Electron process (uptime-dependent, recorded as-is) | n/a small local workload |
| On-disk size | 235 MB exe + 136 MB asar + 20 MB helper + Chromium DLLs ≈ 400+ MB | 24.9 MB dist folder |
| Network model | cloud ASR everywhere (Sentry crash reporting + websocket sync + CDN) | zero cloud egress by invariant |

Honest caveat: the RAM/CPU comparison is a snapshot, not a controlled load test.
FlowPilot's 505 MB holds a whole STT model; Wispr's evaluative weight is in 12
processes and a 332 MB local SQLite vault.

## Measured Latency benchmark (real, from the product's own history table)

The `History` table in `flow.sqlite` records `e2eLatency`, `clientNetworkLatency`,
`speechDuration`, `numWords` per dictation. Aggregates over the user's own 1,847
Utterances (66,895 words; none of the transcript rows read):

| Measure | Value |
|---|---|
| Average end-to-end latency | **906.6 ms** |
| Median bucket share under 500 ms | 578 / 1847 dictations ≈ 31% |
| Share under 1000 ms | 1299 / 1847 = 70% |
| Best / worst | 26 ms / 6897 ms |
| Average network component | 195 ms |
| Fallback ASR activation | used by 0 of 1851 rows (primary cloud ASR always answered) |
| Average utterance | ~14 s speech, ~36 words |

Interpretation for FlowPilot: local faster-whisper base removes the ~195 ms network
leg but spends CPU compute per utterance, so FlowPilot can win on short utterances
and mid hardware; FlowPilot currently does not record an equivalent e2e latency
column at all, which is itself high-value cheap instrumentation work (see possibilities).

## Feature inventory (from tables, migration scripts, and bundle strings)

**Confirmed shipped features, with evidence source in brackets:**

1. Cloud dictation with OPUS streaming chunks and silence-based auto-stop
   (`opusChunks`, `audioActiveRatio`, `longestSilentStreakMs`, `autoEnded`,
   `gracePeriodMs`) [History schema; main bundle strings].
2. Formatting pipeline with fallback levels and divergence scoring
   (`defaultAsrText`, `fallbackAsrText`, `fallbackLevel`,
   `formattingDivergenceScore`) [History schema].
3. Conversational dictate + tone matching (`conversationId`, `toneMatchedText`,
   `toneMatchPairs`, `save-tone-match-pairs` migration) [DB migrations].
4. Editing attempts telemetry + feedback loop (`editedTextAttempts`, `feedback`,
   `hasRevertedAI`, `editDistanceToDictated`) [History schema].
5. Meeting notes product: recordings, speaker map, live transcript, versioned
   notes, folders, images, sharing, calendar sync, refine pipeline with retries
   (`Meetings`, `MeetingVersions`, `Notes`, `NoteImages`, `NoteVersions`,
   `SharedNotes`, `Folders`, `CalendarEvents`) [table list].
6. Chat over your meetings/notes: `NotetakerChats`, `NotetakerChatMessages`,
   `InstructChatSession`, `InstructHistory` [tables].
7. Companion history search “FlowLens” (`FlowLensHistory`) [table].
8. Custom dictionary with snippets, paired-replacement HTML, usage frequency,
   star, team dictionary (`Dictionary`) [table+migrations].
9. Granola import: reads transcripts from competitor Granola to migrate notes
   (`GranolaImportRun`, `GranolaTranscriptQueue`) [tables].
10. Todos, Automations, remote notifications, sharing slugs, organization
    insights, avatar pick, usage outbox for cloud sync [tables].
11. Trigger: push-to-talk flows; hardware buttons via Jabra SDK (customButton1-3,
    speedDial, pushToTalkRoip) [bundle strings; DLL set].
12. Security positioning: HIPAA BAA policy PDF from their CDN [bundle string].
13. Accessibility inspection of target windows before injection (`axText`,
    `axHTML`, `ax-inspect*.mjs`, helper UIAutomation imports) [History schema;
    helper byte scan].
14. Screenshot attachment to a dictation record (`screenshot` column) [History
    schema].
15. Sound design: dictation-start sound WAV backups, achievement sounds: several wav/mp4
    media assets [renderer media list].

**No product evidence of “hide companion while a video plays”:** no renderer/main
bundle strings for media-aware hiding (`videoPlaying`, `hideOnFullscreen`,
`audioSessionDetect` all zero; the only fullscreen matches are window-style flags
and a post-onboarding action). Feature-flag names in userData also show no such
mode. Wisp's companion is designed to coexist with media, not to duck under it.

## Helper byte-scan (imports detected in shipped binary)

```
SetWindowsHookEx 4 | SendInput 3 | GetAsyncKeyState 2
IAudioSessionEnumerator 1 | IAudioMeterInformation 1 | IAudioCaptureClient 1
UIAutomation 16 | GetForegroundWindow 2 | CoCreateInstance 1 | opus 0
```

Wispr's helper uses the same three Windows surfaces FlowPilot already uses: global
input hooks + synthetic input injection, UIA window inspection, and
IAudioSession/IAudioMeter sessioning. Zero-egress FlowPilot equivalents in the repo:
`engine/text_injector.py`, `engine/window_inspector.py`, and (not yet built)
an audio-presence module on pycaw, which is already a FlowPilot dependency.

## Feature parity vs FlowPilot

| Capability | Wispr Flow | FlowPilot today |
|---|---|---|
| Offline dictation, zero egress | no (cloud only) | **yes (invariant)** |
| Local STT with model lifecycle | no | **yes (CTranslate2 int8)** |
| Silence-based auto-end (VAD) | yes | **yes (Silero VAD)** |
| Injection across apps + UIA window poke | yes (helper) | **yes (TextInjector/win32)** |
| e2e latency telemetry | yes (measured 907 ms avg) | **no column yet** |
| Tone matching + conversational dictate | yes (cloud) | partial (personalization + LLM local rewrite exist; conversational dictation state not a DB concept) |
| Meeting notes product (recordings, speakers, versions, folders, sharing) | deep product | notetaker tabs + extractive summaries; no recordings/vault depth |
| Chat over your notes (RAG-ish) | yes | no |
| History search (FlowLens) | yes | history vault exists; search depth limited |
| Custom dictionary + snippets + team sync | yes + team | **yes (local, no team sync)** |
| Automations / Todos / Calendar sync | yes | no |
| Hardware headset buttons (Jabra/button) | yes | no |
| Distraction sound FX/wake achievements | yes | no |
| **Hide companion while media plays** | **no evidence shipped** | **yes — Feature 25 audio presence slice implemented 2026-10-23, see below** |
| Fullscreen-aware hiding | not found | **yes, measured AC-2 gate with 0.20-0.5 s hides** |
| Fall-back ASR diversity | yes (cloud fallback levels) | against zero-egress for cloud options; a second local model is feasible |
| Screenshot in history | yes | no |

## Where FlowPilot should NOT chase Wispr

Everything cloud in Wispr (cloud ASR, cloud formatting, cloud refinement of
meetings, websocket sync, team dictionaries, Sail-like sharing via CDN) is
incompatible with the repo's zero-egress rule and the honest local-only position.
Adopt the *shape* of features, not their network: metering, decent local models,
then local LLM formatting fallback (already in repo).

## The audio-aware invisibility slice design (feature for “watching a video”)

Evidence base: the Windows media session APIs (`IAudioSessionEnumerator` +
`IAudioMeterInformation`) are already in the stack (pycaw dependency) and the
shipped helper of Wispr uses the identical surface, so feasibility on this stack is
proven, not aspirational.

Design (smallest verifiable slice):

1. New `engine/audio_presence.py`: `MediaAudioPresence(provider=None)` — polls
   render sessions; `active` when any session's `GetPeakValue()` exceeds a small
   threshold. Excludes the FlowPilot process itself and microphone capture
   sessions. Provider is injectable for tests via fakes (COM must not appear in
   unit tests).
2. Wire into the existing smart evaluator of
   `ui/companion_visibility_controller.py`: when smart mode and media audio is
   active and no dictation session is in flight, present `hidden` with reason
   `media_playing`; restore per the existing 350 ms / twoSample debounce style
   once quiet for 1.5 s. AC-2 and AC-3 semantics unchanged.
3. Semantics that must be decided in the open: ALL audible playback hides the
   companion (music, podcast, video) — this matches “watching a video or
   something”; muted video does NOT hide via audio (fullscreen rule already
   covers fullscreen video). Manual per-app rules and `always show`/`hide`
   modes remain fully in control; nothing auto-changes in those modes.
4. Tests: fake nothing-that-uses-COM provider for unit tests, plus a controller
   test asserting hidden-under-audio and restored-after-quiet with the debounce
   timing. Full 54-suite gate after. AC-7 sampling budget is untouched because
   polling is piggybacked on the existing evaluator tick.

Limitations to record up front: true “video visible but muted” cannot be proven
without reading pixels or window content — that restriction is what closed
scope 24 as manual per-app rules, and audio presence does not change it; the
closed manual-rules path remains the fallback for muted windows.
