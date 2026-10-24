"""Feature 28: Shared input choices that preserve unavailable selections."""
import logging
from engine.audio_devices import (
    get_audio_input_devices, build_device_selection, resolve_audio_input,
    DeviceResolutionStatus,
)

logger = logging.getLogger("FlowPilot.AudioInputPicker")


def populate_audio_inputs(combo, config):
    """Populate without silently replacing a saved identity with the default."""
    devices = get_audio_input_devices()
    selection = config.get("audio_input_selection")
    if "audio_input_selection" not in config:
        selection = build_device_selection(config.get("audio_device_index", config.get("mic_device")), devices)
    combo.clear()
    combo.addItem("Windows System Default Recording Device", {"mode": "default"})
    for device in devices:
        payload = build_device_selection(device["index"], devices)
        combo.addItem(f"{device['name']} [{device['host_api']}] ({device['max_input_channels']} channels)", payload)
    if selection == {"mode": "default"}:
        combo.setCurrentIndex(0)
        return
    resolution = resolve_audio_input(selection, devices=devices)
    if resolution.status == DeviceResolutionStatus.RESOLVED:
        for index, device in enumerate(devices, 1):
            if device["index"] == resolution.device_index:
                combo.setCurrentIndex(index)
                return
    name = selection.get("name", "Saved microphone") if isinstance(selection, dict) else "Saved microphone"
    combo.addItem(f"[Unavailable: {resolution.status.value}] {name}. Select an input.", selection or {"mode": "unresolved"})
    combo.setCurrentIndex(combo.count() - 1)
