# Engine

## Overview

The engine holds the whole dictation pipeline: audio capture, speech to text with faster-whisper, text polishing under FactGuard, and Win32 text injection, plus meeting intelligence, transforms, personalization, and the optional local API. Everything runs on device with no cloud egress.

## Key files

| File | Owns |
|---|---|
| orchestrator.py | The nine state loop from recording through validation to insertion, owns history saving and telemetry |
| audio_recorder.py | sounddevice capture, 0.35s pre-roll ring buffer, level driven silence auto stop |
| audio_devices.py | Persistent microphone identity and fail closed resolution of missing or ambiguous inputs |
| stt_engine.py | faster-whisper load and transcribe, model path resolution, Silero asset patching at import |
| text_injector.py | Focus verified clipboard paste plus keybd_event injection, InjectionStatus truthfulness, clipboard restore |
| hotkey_service.py | RegisterHotKey message loop on its own thread plus pynput fallback, conflict tables |
| window_inspector.py | Active window and process enumeration per OS |
| companion_visibility.py | Pure Smart, Always and Hide presentation policy; no window content reads |
| media_presence.py | Windows render session audibility probe and background cached sampler for the Qt visibility tick |
| audio_ducker.py | pycaw session mute while dictating (Windows), external tool adapters elsewhere |
| personalization.py | Dictionary, aliases, voice snippets, prompt budget, process wide singleton |
| writing_intelligence.py | FactGuard polishing, conservative entity guard |
| config.py | Defaults, JSON persistence, env based config path resolution |
| local_llm.py | Strictly localhost calls to Ollama, LM Studio, llama.cpp |
| server.py | Optional FastAPI and WebSocket app, bearer token auth, static web UI |
| meeting_notetaker.py | Loopback system audio capture, extractive summaries, native translation |
| meeting_deliberation.py | Decision matrix, risk radar, catch up preview, action cards |

## Conventions

- Dictation and local text processing must not contact external hosts. `model_downloader.py` is the explicit, user initiated setup exception for downloading verified model weights over HTTPS. `local_llm.py` pins `ProxyHandler({})` and blocks redirects on purpose; keep that.
- Cross platform tiering: implement the win32 way first, then the pactl, osascript, or xdotool adapter, each behind a guarded import.
- Orchestrator state changes are the single source of UI truth; emit them through `StateBridge`, never through direct widget calls from engine code.
- Companion context sampling reads foreground executable identity, geometry, and Windows notification state only. It never reads window titles, URLs, screen pixels, clipboard, or transcript content.
- All shared personalization state flows through `get_shared_personalization`; do not add new singletons silently.
- Transform delivery methods return `InjectionResult` and refuse external Replace and Revert without dispatch. Do not add a typing fallback or accept a transaction merely because its `target_type` says verified.
- Orchestrator timing ends at the injection result. Keep visible-delivery latency unmeasured until a target document observer records actual text appearance; never graph dispatch completion as visible delivery.
- A saved missing or ambiguous microphone resolves to `DEVICE_MISSING_SENTINEL = -9999`. Only a verified explicit system default may use `device=None`; capture failures must never create synthetic frames or return a fabricated WAV, including in CI.

## Gotchas

- `engine/config.py` retains an import time `CONFIG_FILE` constant, while load and save resolve the path dynamically. Stage `FLOWPILOT_CONFIG_DIR` or `FLOWPILOT_CONFIG_FILE` before importing the server or other modules with startup side effects.
- Importing `engine.server` instantiates a full orchestrator at module level; it spins model preload and hotkey detection unless env is staged first.
- Importing `engine.stt_engine` monkeypatches `faster_whisper.utils.get_assets_path` for Silero assets; importing STT twice from cache layers is safe, changing the patch is not.
- Process detection and adaptive timing depend on the existing `psutil` import; retain it and test detection when changing those paths.
- `TextInjector` keeps `last_injected_text` and clipboard restore state as class attributes; overlapping sessions can race this state.
- `engine/orchestrator.py` sits at 850 lines, over the 800 line cap; add to it sparingly.
- Cross platform adapter paths silently call external tools (`pactl`, `osascript`, `xdotool`) that may not exist; they must fail soft, never crash the loop.

## Related specs

Persistent audio identity uses [spec 0002](../docs/specs/0002-persistent-audio-input-identity.md). Visible delivery observation uses [spec 0003](../docs/specs/0003-visible-delivery-benchmark-observer.md).

_Drafted by /audit from the repo, worth a quick human pass. Edit freely: once a line stops matching this draft, later runs treat it as curated and will flag rather than overwrite it._
