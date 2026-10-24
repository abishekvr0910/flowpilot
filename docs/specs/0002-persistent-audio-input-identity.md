# 0002. Persistent Audio Input Identity and Resolution

**Date:** 2026-10-24
**Status:** In Progress (P1)
**Audience:** FlowPilot maintainers, Codex, Gemini
**Baseline:** commit `6555e3dc9cd507b5fbc31d71f3d0be95d1c4078a` (v3.1.0-RC3)
**Scope Item:** Feature 28 (Voice & Audio Capture: Persistent Microphone Selection)

---

## 1. Summary

FlowPilot must reliably capture speech using the microphone selected by the user across Windows reboots, device unplug/replug events, driver updates, and PortAudio enumeration shifts.

Previously, `ui/settings_dialog.py` and `ui/setup_wizard.py` persisted a transient integer `audio_device_index` (or legacy `mic_device`) and deduplicated devices solely by display name. On Windows, where the same hardware input is enumerated concurrently across multiple host APIs (MME, DirectSound, WASAPI, WDM-KS) and where device indices shift dynamically, saving a raw integer causes silent selection of wrong microphones or crashes when indices change.

This specification establishes:
1. A structured **persistent input selection contract** stored in `config.json`.
2. A dedicated, deterministic resolver module `engine/audio_devices.py`.
3. Safe migration of legacy integer configs.
4. Truthful resolution states (`RESOLVED`, `DEFAULT`, `MISSING`, `AMBIGUOUS`, `UNAVAILABLE`).
5. Concrete integration across `engine/audio_recorder.py`, `engine/orchestrator.py`, `ui/settings_dialog.py`, `ui/setup_wizard.py`, and `ui/scratchpad_view.py`.
6. Preserved thread-safety, pre-roll ring buffer preservation, deferred switching during active dictation, and clean stream lifecycle.

---

## 2. Problems Addressed

1. **Index Shift Risk**: If microphone *A* is index 4 when saved, but after a reboot or USB re-enumeration microphone *B* occupies index 4 and *A* moves to index 12, reading `audio_device_index: 4` silently captures from *B*.
2. **Host API Ambiguity**: Sounddevice exposes multiple PortAudio host APIs on Windows. Deduplicating by name alone (`seen.add(name)`) drops devices or arbitrarily picks whatever host API happened to enumerate first (often higher-latency MME instead of WASAPI).
3. **Silent Fallback Anti-Pattern**: If a chosen microphone is unplugged, blindly defaulting to index 0 or whatever is at the old index violates truthful status and may capture unintended room audio.
4. **Configuration Coupling**: Different components (`FlowOrchestrator`, `SettingsDialog`, `SetupWizard`, `ScratchpadView`) independently read `audio_device_index` or `mic_device` using ad-hoc fallback logic.

---

## 3. Data Contract

### 3.1 Persisted Config Schema (`config.json`)

The config key `audio_input_selection` is introduced. The legacy `audio_device_index` and `mic_device` are preserved for backward compatibility during migration, but the authoritative selection is `audio_input_selection`.

```json
// Case A: Explicit System Default (tracks OS default input dynamically)
{
  "audio_input_selection": {
    "mode": "default"
  }
}

// Case B: Explicit Physical Endpoint
{
  "audio_input_selection": {
    "mode": "endpoint",
    "name": "Microphone Array (Intel® Smart Sound Technology for Digital Microphones)",
    "host_api": "Windows WASAPI",
    "max_channels": 4
  }
}
```

### 3.2 Resolution Status Enum & Result (`ResolutionResult`)

```python
class DeviceResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"            # Stored endpoint matched unambiguously to current PortAudio index
    DEFAULT = "DEFAULT"              # Explicit system default mode resolved to current OS default
    MISSING = "MISSING"              # Stored endpoint not found in current device enumeration
    AMBIGUOUS = "AMBIGUOUS"          # Multiple identical devices matched without disambiguating attributes
    UNAVAILABLE = "UNAVAILABLE"      # Host audio subsystem or PortAudio failed to query devices

@dataclass
class ResolutionResult:
    status: DeviceResolutionStatus
    device_index: Optional[int]      # None only for a verified system default; -9999 blocks capture
    device_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    fallback_used: bool = False
```

---

## 4. Resolution Algorithm (`AudioDeviceResolver`)

The resolver function `resolve_audio_input(selection, devices=None, default_device_index=None, sd_module=None) -> ResolutionResult` behaves deterministically:

1. **None / Invalid Selection**:
   - `None` means an explicit or new profile system default. An empty or invalid stored object is unusable and must not start capture.
2. **Default Mode (`mode == "default"`)**:
   - Queries `sd.default.device[0]` (default input).
   - If the index matches an enumerated input: returns `DEFAULT` with `device_index=None`, which instructs PortAudio to follow the checked OS default.
   - If no default exists (e.g. headless/no mics): returns `UNAVAILABLE` with `device_index=-9999` and prevents stream creation.
3. **Endpoint Mode (`mode == "endpoint"`)**:
   - Matches candidate devices where `max_input_channels > 0`.
   - **Step 3.1 (Exact match)**: `candidate['name'] == stored['name']` AND `candidate['host_api'] == stored['host_api']`.
     - If exactly 1 match: returns `RESOLVED` with candidate's index.
     - Checks `max_channels` when stored. If one match remains, returns `RESOLVED`. If multiple remain, returns `AMBIGUOUS` with `device_index=-9999`.
   - **Step 3.2 (Name-only match across host APIs)**:
     - A name match with a different host API cannot prove that it is the same endpoint. Return `MISSING` and require a new choice.
   - **Step 3.3 (No matches)**:
     - The device is physically disconnected or disabled.
     - Returns `MISSING` with `device_index=-9999`.
     - **Truthful policy**: Does NOT mutate config. Does NOT silently pretend device is connected.
     - Recorder warmup skips the stream and a dictation start reports an error. Synthetic capture is reserved for explicitly headless or CI runs.

---

## 5. Failure Behaviors & Policy Matrix

| Scenario | Resolver Behavior | Runtime / UI Behavior |
|---|---|---|
| **Reordered Indices** (A was index 4, now index 12) | Resolves A to index 12 (`RESOLVED`). | Stream warms up on index 12. Correct audio captured. |
| **Microphone Missing / Unplugged** | Returns `MISSING` (`device_index=-9999`). | Dictation attempt halts with a clear error. Settings retains an unavailable placeholder until the user selects another input. |
| **Duplicate Device Names** | Disambiguates by Host API and Channel Count. | Both devices selectable in UI with Host API in label. |
| **System Default Mode** | Checks the current OS default before capture (`DEFAULT`), otherwise blocks. | A new dictation start rechecks the device. |
| **Device Disconnected During Active Recording** | Hardware callback behavior varies by driver. | Needs physical unplug testing; the tested guarantee is fail closed at the next start. |
| **Deferred Switch During Active Recording** | `set_device` flags `_device_change_pending`. | Audio switch deferred until `stop_recording()`. Pre-switch audio frames preserved. |
| **Stream Open Failure** (e.g. exclusive mode conflict) | Recorder catches exception, falls back to native sample rate; if hard failure, raises clean exception. | Orchestrator halts dictation state cleanly, notifies user via `StateBridge`. |
| **Config Save Failure** (disk full / permission) | `save_config` returns `False`. | `update_config` reverts in-memory config change and returns `False`. |

---

## 6. Migration Contract

When `engine/config.py` loads `config.json`:
1. If `audio_input_selection` already exists, it is authoritative.
2. If `audio_input_selection` is absent:
   - Check `audio_device_index` or legacy `mic_device`.
   - If integer index `idx` is present and valid:
     - Query device at `idx`.
     - If device exists and is an input: migrate to `{"mode": "endpoint", "name": dev["name"], "host_api": host_api_name, "max_channels": dev["max_input_channels"]}`.
     - If the stored index is invalid: migrate to `{"mode": "unresolved", "legacy_index": idx}` and require a new selection. `None` selects default.
   - If neither exists: default to `{"mode": "default"}`.
   - Save migrated config atomically.

---

## 7. Verification Plan & Test Matrix

New unit test suite: `tests/test_audio_devices.py` (wired into `tests/run_all_tests.py`).

1. `test_resolve_reordered_indices`: Device A at index 4 saved, later A is at index 12 and B is at index 4. Assert resolved index is 12, never 4.
2. `test_resolve_default_mode`: Resolves system default input dynamically.
3. `test_resolve_missing_device`: Stored endpoint not present in device list returns `MISSING` and `device_index=-9999`.
4. `test_resolve_duplicate_names_disambiguated_by_hostapi`: Same name under MME and WASAPI resolves to requested host API.
5. `test_legacy_config_migration`: Old config with integer index migrates to persistent contract without silent mismatch.
6. `test_deferred_switch_preserves_frames`: Device switch during recording defers until stop and concatenates frames properly.
7. `test_recorder_rearm_with_resolved_device`: AudioRecorder correctly opens stream with resolved index.
