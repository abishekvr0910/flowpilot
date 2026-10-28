"""Feature 31: Independent FluidVoice parity tranche for hold to mute."""

# FluidVoice parity tranche

**Status:** Accepted  
**Date:** 2026-10-28  
**Scope:** Windows desktop dictation session controls

## Summary

FlowPilot already covers most of the useful behavior observed in FluidVoice, including local speech models, live preview, writing commands, per app
profiles, recovery shortcuts, history, and privacy controls. This tranche adds an opt in hold to mute control that keeps one dictation session alive
while excluding the muted interval from audio, transcription, and saved history. The implementation is independent and uses no FluidVoice source,
assets, private runtime, or telemetry.

## Context

FluidVoice is a public macOS application whose current repository is GPLv3. Its README documents hold to mute as a temporary pause that preserves the
same dictation session and does not type a space for a long hold. FlowPilot is Windows first and already owns the recorder, global hotkey service,
state machine, and privacy defaults. Copying GPL implementation code would create obligations that are not part of FlowPilot's release plan, so the
behavior is reproduced from the public description using existing FlowPilot contracts.

The missing behavior is useful when a speaker needs to think, cough, or handle a side conversation without finalizing the recording. It must not
interrupt the microphone stream, trigger silence auto stop, add muted frames to the transcript, or create a false success state.

## Requirements

**User stories**:

- As a dictation user, I want to hold a configurable shortcut to mute the current session so I can pause speaking without ending dictation.
- As a privacy conscious user, I want muted audio excluded from transcription and local history.
- As a user with an existing keyboard layout, I want the feature disabled by default and never to capture an unmodified Space key globally.

**Acceptance criteria**:

- **AC-1:** When an active recording receives the configured mute shortcut press, the recorder enters a muted state without stopping the stream or changing
  the orchestrator recording state.
- **AC-2:** While muted, callback frames are discarded, audio level notifications report zero, callback health timestamps continue to update, and silence
  auto stop cannot finalize the session.
- **AC-3:** When the shortcut is released, the recorder leaves the muted state and subsequent frames are captured into the same session.
- **AC-4:** Stopping a session after a mute interval produces audio containing only captured frames before mute and after unmute. Muted frames do not reach
  STT, text repair, injection, or saved history.
- **AC-5:** The default configuration keeps the feature disabled. Enabling it requires a modifier shortcut such as Ctrl+Space; bare Space is rejected
  for global registration.
- **AC-6:** Configuration changes rebind the mute shortcut without disturbing the primary dictation shortcut or recovery shortcuts. Invalid or conflicting
  shortcuts are rejected without persisting a partial update.
- **AC-7:** The local API and WebSocket state expose `is_muted` alongside `is_recording`, without exposing audio or transcript content.
- **AC-8:** Unit tests cover press, release, idle presses, disabled mode, conflict rejection, frame exclusion, and the no auto stop rule.

## Options considered

### Option 1: Add mute to the existing recorder and hotkey services

The recorder owns the capture exclusion and the existing global hotkey service owns press and release callbacks.

**Pros**:

- Small change with no new dependency.
- Reuses existing Windows and cross platform release monitoring.
- Easy rollback behind a configuration flag.

**Cons**:

- A global bare Space shortcut cannot be supported safely through RegisterHotKey.

### Option 2: Add a low level keyboard hook for bare Space

Install a process wide keyboard hook and emulate a quick Space tap when the hold is not used.

**Pros**:

- Closer to the macOS interaction described by FluidVoice.

**Cons**:

- Higher input interception and accessibility risk.
- More failure modes across elevated windows, games, secure fields, and keyboard layouts.

## Decision

**Chosen option:** Option 1, an opt in modifier based hold to mute control.

The public behavior is implemented independently in the existing recorder, orchestrator, hotkey service, settings, API, and test layers. No FluidVoice
GPLv3 source or assets are copied.

## Feature design

**Data model sketch**:

Configuration only, no database migration:

| Field | Type | Required | Default | Rule |
|---|---|---:|---|---|
| `hold_to_mute_enabled` | boolean | yes | false | Opt in gate |
| `mute_hotkey` | string | yes | `Ctrl+Space` | Must include a modifier and have one primary key |

Runtime state lives on `AudioRecorder.is_muted` and is reset on stop, cancel, close, or capture failure.

**State transitions**:

`recording and unmuted` → `recording and muted` on valid press.  
`recording and muted` → `recording and unmuted` on release.  
Any terminal transition resets to unmuted.

**API surface**:

| Surface | Method | Output |
|---|---|---|
| `/api/v1/status` | GET | Existing status plus boolean `is_muted` |
| `/ws` initial and state events | send | Existing state plus boolean `is_muted` |

**Key invariants**:

- Muting never stops or restarts the input stream.
- Muted callback frames are never appended to `audio_frames` or the pre roll buffer.
- Health monitoring still observes callback arrival while muted.
- A mute shortcut cannot equal the dictation, transform, paste last, or copy last shortcut.
- A disabled feature has no registered global mute shortcut.
- No cloud provider or telemetry path is introduced.

**Security model**:

The shortcut is local machine input only. It is not accepted as a shell command, never reads clipboard content, and cannot access credentials. The
existing zero cloud egress and target verification rules remain unchanged.

**Configuration required**:

- `hold_to_mute_enabled`: local opt in feature flag.
- `mute_hotkey`: local modifier based shortcut.

**Critical test scenarios**:

- Press and release during an active recording, verifies **AC-1**, **AC-2**, and **AC-3**.
- Frame injection before, during, and after mute, verifies **AC-4**.
- Disabled mode and bare Space rejection, verifies **AC-5**.
- Rebind and conflict failure, verifies **AC-6**.
- API state response, verifies **AC-7**.
- Test suite coverage, verifies **AC-8**.

## Build plan

1. Add recorder mute state, frame exclusion, state reporting, and terminal reset behavior, satisfying **AC-1**, **AC-2**, **AC-3**, and **AC-4**.
2. Add configuration defaults and validation, satisfying **AC-5** and **AC-6**.
3. Register the modifier based press and release callbacks in the orchestrator without changing existing shortcut aliases, satisfying **AC-1**, **AC-3**, and
   **AC-6**.
4. Expose truthful mute state through the local API and WebSocket payloads, satisfying **AC-7**.
5. Add focused unit and API regression tests, satisfying **AC-8**.
6. Run focused suites, then the full audit suite. Keep the existing RC10 artifact immutable until a later candidate rebuild is explicitly approved.

### Verification record

- Focused audio device suite: 30 tests passed.
- Hotkey suite: passed, including press and release callbacks and bare Space rejection.
- Settings, API and WebSocket, pilot reliability, state machine, and desktop lifecycle suites: passed.
- Full audit: 60 suites passed, 0 skipped, 0 failed in 144.73 seconds.
- `git diff --check`: clean.

## Consequences

**Positive**:

- Users can pause one dictation without losing session context.
- Muted speech is excluded from downstream processing and history.
- The feature is disabled by default and has a small rollback surface.

**Negative / tradeoffs**:

- Bare Space parity is intentionally not implemented because a global Windows hook could interfere with normal typing and protected windows.
- A user must choose a modifier shortcut, and that shortcut may be unavailable if another application owns it.

**Neutral**:

- The feature does not add a model, network path, or packaged asset.

## Follow-up

- [ ] Evaluate richer local speech engine adapters separately after measuring Windows CPU, memory, and language quality.
- [ ] Evaluate a signed updater separately; do not bundle update code into this tranche.
- [ ] Add a manual interactive check for mute overlay visuals on the physical Windows desktop.

## References

- FluidVoice README feature description and license: https://github.com/altic-dev/FluidVoice
- FlowPilot `AGENTS.md`, `engine/AGENTS.md`, `ui/AGENTS.md`, and existing specs 0001 through 0004.
