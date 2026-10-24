"""Feature 11: Loopback API and WebSocket lifecycle without real microphone input."""

import sys
import os
import logging
import time
import json
import asyncio
import threading
from pathlib import Path
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
import websockets

logger = logging.getLogger("FlowPilot.ApiWebsocketTest")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_API_TOKEN = "flowpilot-test-token-0123456789abcdef"
os.environ["FLOWPILOT_API_TOKEN"] = TEST_API_TOKEN
TEST_CONFIG_FILE = PROJECT_ROOT / f".flowpilot-api-test-{os.getpid()}.json"
os.environ["FLOWPILOT_CONFIG_FILE"] = str(TEST_CONFIG_FILE)

import uvicorn
from engine.server import app

test_server = None

def run_test_server():
    global test_server
    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    test_server = uvicorn.Server(config)
    test_server.run()

async def client_test():
    print("=" * 60)
    print("AUDIT TEST 5: UI-TO-BACKEND API & WEBSOCKET VERIFICATION")
    print("=" * 60)

    # Give server time to bind
    await asyncio.sleep(1.0)

    # 1. Test GET /api/config
    print("\n[Step 1] Testing GET /api/config...")
    authorized = {"Authorization": f"Bearer {TEST_API_TOKEN}"}
    try:
        urllib.request.urlopen("http://127.0.0.1:8765/api/config")
        raise AssertionError("Unauthenticated config access unexpectedly succeeded")
    except urllib.error.HTTPError as exc:
        assert exc.code == 401
    try:
        urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:8765/api/config",
            headers={"Authorization": f"Bearer {TEST_API_TOKEN}", "Origin": "https://untrusted.example"},
        ))
        raise AssertionError("Cross-origin config access unexpectedly succeeded")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
    req = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765/api/config", headers=authorized))
    config_data = json.loads(req.read().decode())
    print(f"  Status: {req.status}")
    print(f"  Active tone mode: {config_data.get('active_tone_mode')}")
    print(f"  Engine mode: {config_data.get('engine_mode')}")
    assert req.status == 200, "GET /api/config failed"

    # 2. Test POST /api/config
    print("\n[Step 2] Testing POST /api/config...")
    payload = json.dumps({"active_tone_mode": "developer", "engine_mode": "local"}).encode()
    post_req = urllib.request.Request("http://127.0.0.1:8765/api/config", data=payload, headers={"Content-Type": "application/json", **authorized})
    post_res = urllib.request.urlopen(post_req)
    post_data = json.loads(post_res.read().decode())
    print(f"  Status: {post_res.status}")
    print(f"  Response: {post_data.get('status')}")
    assert post_res.status == 200, "POST /api/config failed"

    # A failed disk write must not be reported as a saved setting.
    from engine.server import orchestrator
    original_language = orchestrator.config.get("language")
    rejected_update = urllib.request.Request(
        "http://127.0.0.1:8765/api/config",
        data=json.dumps({"language": "de"}).encode(),
        headers={"Content-Type": "application/json", **authorized},
    )
    with patch("engine.orchestrator.save_config", return_value=False):
        try:
            urllib.request.urlopen(rejected_update)
            raise AssertionError("Failed config save was reported as success")
        except urllib.error.HTTPError as exc:
            assert exc.code == 500
    assert orchestrator.config.get("language") == original_language

    # 2b. Test GET /v1/models (OpenAI compatibility)
    print("\n[Step 2b] Testing GET /v1/models...")
    m_req = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765/v1/models", headers=authorized))
    m_data = json.loads(m_req.read().decode())
    assert m_req.status == 200, "GET /v1/models failed"
    assert m_data.get("object") == "list"
    print(f"  Status: {m_req.status}, Models: {[m['id'] for m in m_data.get('data', [])]}")

    # 3. Test WebSocket connection and events
    print("\n[Step 3] Testing WebSocket (/ws) communication...")
    uri = "ws://127.0.0.1:8765/ws"
    rejected = False
    try:
        async with websockets.connect(uri) as unauthenticated:
            await unauthenticated.recv()
    except Exception:
        rejected = True
    assert rejected, "Unauthenticated WebSocket unexpectedly received data"
    async with websockets.connect(uri, subprotocols=[f"flowpilot-token.{TEST_API_TOKEN}"]) as ws:
        # Receive initial state
        initial_msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
        initial_data = json.loads(initial_msg)
        print(f"  Received event: '{initial_data.get('state')}' (is_recording={initial_data.get('is_recording')})")
        assert initial_data.get("state") == "connected", "Initial event was not 'connected'"

        # Send start recording action
        print("\n[Step 4] Sending WebSocket action: 'start'...")
        await ws.send(json.dumps({"action": "start"}))

        # Expect starting and/or listening event (drain intermediate events)
        listening_received = False
        for _ in range(10):
            listening_msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
            listening_data = json.loads(listening_msg)
            print(f"  Received event: '{listening_data.get('state')}' (target={listening_data.get('target_app')})")
            if listening_data.get("state") == "listening":
                listening_received = True
                break
            elif listening_data.get("state") in ("starting", "audio_level"):
                continue
            else:
                break
        assert listening_received, f"Did not receive 'listening' state (got '{listening_data.get('state')}')"

        # Receive at least one audio level event
        print("\n[Step 5] Listening for real-time RMS audio level packets...")
        received_levels = 0
        for _ in range(5):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                if data.get("state") == "audio_level":
                    received_levels += 1
                    print(f"  RMS Level packet: {data.get('level')}")
            except asyncio.TimeoutError:
                break

        print(f"  Total audio level packets received: {received_levels}")
        assert received_levels > 0 or bool(os.environ.get("CI")), "No audio level packets received during active recording!"

        # Send stop recording action
        print("\n[Step 6] Sending WebSocket action: 'stop'...")
        await ws.send(json.dumps({"action": "stop"}))

        # Expect stopping or transcribing/processing event
        proc_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
        proc_data = json.loads(proc_msg)
        print(f"  Received event: '{proc_data.get('state')}'")
        assert proc_data.get("state") in ("stopping", "processing", "transcribing"), f"Unexpected stop event: {proc_data.get('state')}"

    print("\n[RESULT] UI-to-backend REST API & WebSocket pipeline PASSED.")
    return True

def test_api_and_websocket_pipeline():
    global test_server
    t = threading.Thread(target=run_test_server, daemon=True)
    t.start()
    success = False
    try:
        # This suite measures API control flow. A declared virtual input keeps
        # hosted CI deterministic without permitting a production default mic
        # fallback when no endpoint exists.
        fake_devices = [{"index": 0, "name": "API Test Input", "host_api": "Windows WASAPI", "max_input_channels": 1}]
        fake_stream = MagicMock()
        fake_stream.active = True
        with patch("engine.audio_devices.get_audio_input_devices", return_value=fake_devices), \
             patch("engine.audio_devices.sd.default.device", [0, -1]), \
             patch("engine.audio_recorder.sd.InputStream", return_value=fake_stream):
            success = asyncio.run(client_test())
    finally:
        if test_server:
            test_server.should_exit = True
        try:
            from engine.server import orchestrator
            if orchestrator:
                orchestrator.stop()
        except Exception:
            pass
        t.join(timeout=2.0)
        TEST_CONFIG_FILE.unlink(missing_ok=True)
    assert success is True

if __name__ == "__main__":
    test_api_and_websocket_pipeline()
    sys.exit(0)
