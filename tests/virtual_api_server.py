"""Feature 11: Explicit virtual hardware for the Node API protocol test."""

import argparse
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("FlowPilot.VirtualApiServerTest")


class VirtualHotkeyService:
    def __init__(self):
        self.alive = False
        self.stats = {"errors": []}

    def is_alive(self):
        return self.alive

    def register(self, *_args, **_kwargs):
        return None

    def start(self, timeout=3.0):
        self.alive = True
        return True

    def stop(self):
        self.alive = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Invalid loopback port")

    input_device = [{
        "index": 0, "name": "Node API Virtual Input",
        "host_api": "Windows WASAPI", "max_input_channels": 1,
    }]
    stream = MagicMock()
    stream.active = True
    ducker = MagicMock()

    # Patches exist only in this test server process. Production resolution
    # remains fail closed when no real input endpoint is available.
    with patch("engine.audio_devices.get_audio_input_devices", return_value=input_device), \
         patch("engine.audio_devices.sd.default.device", [0, -1]), \
         patch("engine.audio_recorder.sd.InputStream", return_value=stream), \
         patch("engine.orchestrator.get_hotkey_service", side_effect=VirtualHotkeyService), \
         patch("engine.orchestrator.AudioDucker", return_value=ducker):
        import uvicorn
        from engine.server import app
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
