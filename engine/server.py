import asyncio
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from engine.orchestrator import FlowOrchestrator
from engine.config import load_config, save_config

def redact_sensitive_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy of config with API keys masked."""
    safe = dict(cfg)
    for k in ("groq_api_key", "openai_api_key"):
        if safe.get(k):
            safe[k] = "***"
    return safe

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    global loop
    loop = asyncio.get_running_loop()
    try:
        orchestrator.start_hotkey_listener()
    except Exception as e:
        print(f"[Server] Hotkey listener notice: {e}")
    print("[Server] Engine server started on http://127.0.0.1:8765")
    yield

app = FastAPI(title="FlowPilot Engine API", lifespan=lifespan)

# Enable CORS with restricted origin policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://127.0.0.1:8766",
        "http://localhost:8766",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "engine_state": getattr(orchestrator.state, "value", str(orchestrator.state)),
        "is_recording": orchestrator.recorder.is_recording
    }

@app.get("/api/v1/status")
async def api_status():
    return {
        "status": "online",
        "version": "3.1.0-pilot",
        "engine_state": getattr(orchestrator.state, "value", str(orchestrator.state)),
        "is_recording": orchestrator.recorder.is_recording,
        "active_profile": orchestrator.config.get("profile", "developer"),
        "model": orchestrator.config.get("local_model_size", "base")
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send initial config and state with sensitive credentials masked
        await websocket.send_text(json.dumps({
            "state": "connected",
            "config": redact_sensitive_config(orchestrator.config),
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
    return redact_sensitive_config(orchestrator.config)

@app.post("/api/config")
async def set_config(new_config: Dict[str, Any]):
    # Prevent masked strings ('***') from wiping existing keys
    clean_config = {}
    for k, v in new_config.items():
        if k in ("groq_api_key", "openai_api_key") and v == "***":
            continue
        clean_config[k] = v
    orchestrator.update_config(clean_config)
    return {"status": "success", "config": redact_sensitive_config(orchestrator.config)}

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
