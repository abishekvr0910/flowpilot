"""
FlowPilot Audio Devices Resolver (Feature 28: Persistent Microphone Selection)
Windows-first, offline, deterministic audio input identity resolution.

Survives:
- PortAudio device index renumbering on reboot, sleep/resume, and driver updates
- Host API duplication (MME, DirectSound, WASAPI, WDM-KS)
- Disconnection / missing device detection without silent false-positive switching
- Explicit system default tracking
"""

import sys
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger("FlowPilot.AudioDevices")

# Sentinel value indicating that the requested audio input endpoint is disconnected or missing.
# NEVER use None for a missing device, as sounddevice and PortAudio treat None as the system default!
DEVICE_MISSING_SENTINEL: int = -9999

try:
    import sounddevice as sd
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False


class DeviceResolutionStatus(str, Enum):
    """Authoritative truthfulness states for audio input resolution."""
    RESOLVED = "RESOLVED"            # Stored endpoint matched unambiguously to current PortAudio index
    DEFAULT = "DEFAULT"              # Explicit system default mode resolved to current OS default
    MISSING = "MISSING"              # Stored endpoint not found in current device enumeration
    AMBIGUOUS = "AMBIGUOUS"          # Multiple identical devices matched without disambiguating attributes
    UNAVAILABLE = "UNAVAILABLE"      # Host audio subsystem or PortAudio failed to query devices


@dataclass
class ResolutionResult:
    """Structured result returned by AudioDeviceResolver."""
    status: DeviceResolutionStatus
    device_index: Optional[int]
    device_info: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    fallback_used: bool = False


# Preferred Host APIs in order of preference for low latency & reliability on Windows
PREFERRED_HOST_APIS = [
    "Windows WASAPI",
    "Windows DirectSound",
    "MME",
    "Windows WDM-KS",
    "ALSA",
    "Core Audio"
]


def get_audio_input_devices(sd_module=None) -> List[Dict[str, Any]]:
    """
    Enumerates all input devices from SoundDevice, enriching each with
    its host API name, channel count, and PortAudio integer index.
    """
    target_sd = sd_module if sd_module is not None else (sd if HAS_SOUNDDEVICE else None)
    if target_sd is None:
        return []

    try:
        raw_devices = target_sd.query_devices()
        raw_hostapis = target_sd.query_hostapis()
    except Exception as e:
        logger.warning(f"Could not query audio devices: {e}")
        return []

    input_devices = []
    hostapi_names = {}
    for h_idx, h in enumerate(raw_hostapis):
        hostapi_names[h_idx] = h.get("name", f"HostAPI {h_idx}")

    for idx, d in enumerate(raw_devices):
        if d.get("max_input_channels", 0) > 0:
            h_idx = d.get("hostapi", -1)
            h_name = hostapi_names.get(h_idx, "Unknown API")
            dev_dict = dict(d)
            dev_dict["index"] = idx
            dev_dict["host_api"] = h_name
            input_devices.append(dev_dict)

    return input_devices


def resolve_audio_input(
    selection: Optional[Dict[str, Any]],
    devices: Optional[List[Dict[str, Any]]] = None,
    default_device_index: Optional[int] = None,
    sd_module=None
) -> ResolutionResult:
    """
    Deterministically resolves a stored selection contract to a current
    PortAudio device index.

    Contracts supported:
      {"mode": "default"}
      {"mode": "endpoint", "name": "...", "host_api": "...", "max_channels": 2}
    """
    target_sd = sd_module if sd_module is not None else (sd if HAS_SOUNDDEVICE else None)

    # 1. Gather devices if not passed in
    if devices is None:
        devices = get_audio_input_devices(target_sd)

    if not devices:
        return ResolutionResult(
            status=DeviceResolutionStatus.UNAVAILABLE,
            device_index=DEVICE_MISSING_SENTINEL,
            error_message="No audio input devices enumerated."
        )

    # Resolve OS default input index if needed
    def_idx = default_device_index
    if def_idx is None and target_sd is not None:
        try:
            default_pair = target_sd.default.device
            def_idx = default_pair if isinstance(default_pair, int) else default_pair[0]
        except Exception:
            def_idx = None

    # 2. Handle Default Mode
    if selection is None or (isinstance(selection, dict) and selection.get("mode") == "default"):
        dev_info = None
        if def_idx is not None and any(d["index"] == def_idx for d in devices):
            dev_info = next((d for d in devices if d["index"] == def_idx), None)
        if dev_info is None:
            return ResolutionResult(DeviceResolutionStatus.UNAVAILABLE, DEVICE_MISSING_SENTINEL,
                                    error_message="Windows has no available default input. Select a microphone.")
        return ResolutionResult(
            status=DeviceResolutionStatus.DEFAULT,
            device_index=None,
            device_info=dev_info
        )

    # 3. Handle Endpoint Mode
    if not isinstance(selection, dict):
        return ResolutionResult(DeviceResolutionStatus.MISSING, DEVICE_MISSING_SENTINEL,
                                error_message="Invalid audio selection. Select a microphone.")
    if selection.get("mode") == "endpoint":
        target_name = str(selection.get("name") or "").strip()
        target_api = str(selection.get("host_api") or "").strip()
        target_channels = selection.get("max_channels")

        if not target_name:
            return ResolutionResult(
                status=DeviceResolutionStatus.MISSING,
                device_index=DEVICE_MISSING_SENTINEL,
                error_message="Invalid selection contract: missing device name."
            )

        # 3.1 Exact match: name AND host_api
        exact_matches = [
            d for d in devices
            if d.get("name", "").strip() == target_name and d.get("host_api", "").strip() == target_api
        ]
        if target_channels is not None:
            exact_matches = [d for d in exact_matches if d.get("max_input_channels") == target_channels]
        if len(exact_matches) == 1:
            return ResolutionResult(
                status=DeviceResolutionStatus.RESOLVED,
                device_index=exact_matches[0]["index"],
                device_info=exact_matches[0]
            )
        if len(exact_matches) > 1:
            # Disambiguate by max_channels if possible
            if target_channels is not None:
                chan_matches = [d for d in exact_matches if d.get("max_input_channels") == target_channels]
                if len(chan_matches) == 1:
                    return ResolutionResult(
                        status=DeviceResolutionStatus.RESOLVED,
                        device_index=chan_matches[0]["index"],
                        device_info=chan_matches[0]
                    )
            # Names and channel counts cannot distinguish identical physical mics.
            return ResolutionResult(
                status=DeviceResolutionStatus.AMBIGUOUS,
                device_index=DEVICE_MISSING_SENTINEL,
                error_message="Multiple identical input endpoints found."
            )

        # A changed host API cannot prove that this is the same physical endpoint.
        name_matches = [d for d in devices if d.get("name", "").strip() == target_name]
        if name_matches:
            return ResolutionResult(
                status=DeviceResolutionStatus.MISSING,
                device_index=DEVICE_MISSING_SENTINEL,
                error_message="Microphone identity changed. Select the intended input again."
            )

        # 3.3 Endpoint not found -> MISSING
        return ResolutionResult(
            status=DeviceResolutionStatus.MISSING,
            device_index=DEVICE_MISSING_SENTINEL,
            error_message=f"Selected microphone '{target_name}' is disconnected or unavailable."
        )

    # Unknown mode fallback
    return ResolutionResult(
        status=DeviceResolutionStatus.MISSING,
        device_index=DEVICE_MISSING_SENTINEL,
        error_message=f"Unrecognized audio input selection mode: {selection.get('mode')}"
    )


def build_device_selection(device_index: Optional[int], devices: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Constructs a persistent selection contract dictionary from a PortAudio device index.
    Only None means default. An invalid legacy index requires a new selection.
    """
    if device_index is None:
        return {"mode": "default"}

    if devices is None:
        devices = get_audio_input_devices()

    match = next((d for d in devices if d.get("index") == device_index), None)
    if not match:
        return {"mode": "unresolved", "legacy_index": device_index}

    return {
        "mode": "endpoint",
        "name": match.get("name", ""),
        "host_api": match.get("host_api", ""),
        "max_channels": match.get("max_input_channels", 1)
    }


def migrate_legacy_audio_config(config: Dict[str, Any], devices: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    Inspects config and ensures 'audio_input_selection' accurately migrates from
    legacy 'audio_device_index' or 'mic_device' when present.
    Returns True if config was modified and needs saving.
    """
    # Call with raw JSON, before defaults. An explicit default is authoritative too.
    if "audio_input_selection" in config:
        return False

    # Check for legacy integer
    legacy_idx = config.get("audio_device_index", config.get("mic_device"))
    config["audio_input_selection"] = build_device_selection(legacy_idx, devices)
    return True
