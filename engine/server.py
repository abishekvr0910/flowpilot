import asyncio
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from engine.orchestrator import FlowOrchestrator
from engine.config import load_config, save_config

app = FastAPI(title="FlowPilot Engine API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: List[WebSocket] = []
loop = None

def broadcast_state(payload: Dict[str, Any]):
    """Called from background threads when engine state changes."""
    global loop
    if not loop or loop.is_closed():
        return
    message = json.dumps(payload)
    for conn in list(active_connections):
        try:
            asyncio.run_coroutine_threadsafe(conn.send_text(message), loop)
        except Exception:
            pass

orchestrator = FlowOrchestrator(on_state_change=broadcast_state)

@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    # Start global hotkey listener
    orchestrator.start_hotkey_listener()
    print("[Server] Engine server started on http://127.0.0.1:8765")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send initial config and state
        await websocket.send_text(json.dumps({
            "state": "connected",
            "config": orchestrator.config,
            "is_recording": orchestrator.recorder.is_recording
        }))
        while True:
            # Keep alive and listen for client commands
            data = await websocket.receive_text()
            try:
                cmd = json.loads(data)
                action = cmd.get("action")
                if action == "toggle":
                    orchestrator.toggle_dictation()
                elif action == "start":
                    orchestrator.start_dictation()
                elif action == "stop":
                    orchestrator.stop_dictation_and_process()
            except Exception as e:
                print(f"[WS Error] {e}")
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)

@app.get("/api/config")
async def get_config():
    return orchestrator.config

@app.post("/api/config")
async def set_config(new_config: Dict[str, Any]):
    orchestrator.update_config(new_config)
    return {"status": "success", "config": orchestrator.config}

@app.post("/api/toggle")
async def toggle_dictation():
    orchestrator.toggle_dictation()
    return {"status": "triggered", "is_recording": orchestrator.recorder.is_recording}

@app.get("/api/history")
async def get_history():
    return {"history": orchestrator.config.get("history", [])}

@app.delete("/api/history")
async def clear_history():
    orchestrator.config["history"] = []
    save_config(orchestrator.config)
    return {"status": "cleared"}

# Mount UI static files
ui_dir = Path(__file__).parent.parent / "ui"
if ui_dir.exists():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")
