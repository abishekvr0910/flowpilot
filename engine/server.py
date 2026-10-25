"""Feature 11: Token protected local API and web companion."""

import asyncio
import hmac
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from engine import __version__
from engine.orchestrator import FlowOrchestrator
from engine.config import OBSOLETE_CLOUD_KEYS, load_config, local_only_config, save_config

def redact_sensitive_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Return only supported local settings to API clients."""
    return local_only_config(cfg)

# Active WebSocket connections
active_connections: List[WebSocket] = []
loop = None

def _api_token() -> Optional[str]:
    """The optional server must never expose dictation controls without a secret."""
    token = os.environ.get("FLOWPILOT_API_TOKEN", "")
    return token if len(token) >= 32 else None

def _origin_allowed(origin: Optional[str], host: Optional[str]) -> bool:
    """Allow same-origin browser clients; CLI clients without Origin still need a token."""
    return not origin or (host is not None and origin in (f"http://{host}", f"https://{host}"))

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
    if _api_token() is None:
        raise RuntimeError("Set FLOWPILOT_API_TOKEN to a random value of at least 32 characters before starting the optional API server.")
    loop = asyncio.get_running_loop()
    try:
        orchestrator.start_hotkey_listener()
    except Exception as e:
        print(f"[Server] Hotkey listener notice: {e}")
    print("[Server] Engine server started on http://127.0.0.1:8765")
    yield

app = FastAPI(title="FlowPilot Engine API", lifespan=lifespan)

@app.middleware("http")
async def require_api_token(request: Request, call_next):
    if request.url.path.startswith(("/api/", "/v1/")):
        token = _api_token()
        if token is None:
            return JSONResponse({"detail": "Local API token is not configured."}, status_code=503)
        if not _origin_allowed(request.headers.get("origin"), request.headers.get("host")):
            return JSONResponse({"detail": "Cross-origin API requests are not allowed."}, status_code=403)
        supplied = request.headers.get("authorization", "")
        if not supplied.startswith("Bearer ") or not hmac.compare_digest(supplied[7:], token):
            return JSONResponse({"detail": "A valid local API token is required."}, status_code=401)
    return await call_next(request)

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
    return {"status": "healthy"}

@app.get("/api/v1/status")
async def api_status():
    return {
        "status": "online",
        "version": __version__,
        "engine_state": getattr(orchestrator.state, "value", str(orchestrator.state)),
        "is_recording": orchestrator.recorder.is_recording,
        "active_profile": orchestrator.config.get("profile", "developer"),
        "model": orchestrator.config.get("local_model_size", "base")
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = _api_token()
    offered = [part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    protocol = next((part for part in offered if part.startswith("flowpilot-token.")), None)
    supplied = protocol.removeprefix("flowpilot-token.") if protocol else ""
    if (token is None or not _origin_allowed(websocket.headers.get("origin"), websocket.headers.get("host"))
            or not hmac.compare_digest(supplied, token)):
        await websocket.close(code=1008)
        return
    await websocket.accept(subprotocol=protocol)
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
    if OBSOLETE_CLOUD_KEYS.intersection(new_config) or new_config.get("engine_mode", "local") != "local":
        raise HTTPException(status_code=422, detail="Cloud speech settings are unsupported. Use local mode.")
    if not orchestrator.update_config(new_config):
        raise HTTPException(status_code=500, detail="Configuration could not be saved.")
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
    previous_history = orchestrator.config.get("history", [])
    orchestrator.config["history"] = []
    if not save_config(orchestrator.config):
        orchestrator.config["history"] = previous_history
        raise HTTPException(status_code=500, detail="History could not be cleared.")
    return {"status": "cleared"}

# --- OpenAI-Compatible Speech API (Cursor IDE / Open WebUI Drop-in) ---

@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models catalog endpoint."""
    return {
        "object": "list",
        "data": [
            {
                "id": "whisper-1",
                "object": "model",
                "created": 1677610602,
                "owned_by": "flowpilot"
            },
            {
                "id": orchestrator.config.get("local_model_size", "base"),
                "object": "model",
                "created": 1677610602,
                "owned_by": "flowpilot"
            }
        ]
    }

@app.post("/v1/audio/transcriptions")
async def openai_compatible_transcribe(
    file: UploadFile = File(...),
    model: Optional[str] = Form("whisper-1"),
    language: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    response_format: Optional[str] = Form("json"),
    temperature: Optional[float] = Form(0.0)
):
    """
    OpenAI-compatible speech-to-text endpoint (POST /v1/audio/transcriptions).
    Direct drop-in replacement for api.openai.com/v1/audio/transcriptions.
    Compatible with Cursor IDE, Open WebUI, Obsidian plugins, and custom developer scripts.
    """
    if not file:
        raise HTTPException(status_code=400, detail="Missing audio file in form upload.")

    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        vocab = [prompt] if prompt else None
        res = orchestrator.stt.transcribe(audio_bytes, custom_vocabulary=vocab)
        raw_text = res.get("text", "")

        # Polish text according to active context processor
        final_text = orchestrator.processor.process(raw_text) if raw_text else ""

        fmt = (response_format or "json").lower()
        if fmt == "text":
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(final_text)
        elif fmt == "verbose_json":
            return {
                "task": "transcribe",
                "language": res.get("detected_language", "en"),
                "duration": res.get("duration", 0),
                "text": final_text,
                "engine": "flowpilot_faster_whisper",
                "segments": []
            }
        else:
            return {"text": final_text}
    except Exception as e:
        print(f"[Server Error] /v1/audio/transcriptions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount UI static files safely (disallow raw Python source and sensitive config disclosure)
class SafeStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        lower_path = path.lower()
        if lower_path.endswith((".py", ".pyc", ".pyd", ".json", ".lock", ".toml", ".spec")):
            raise HTTPException(status_code=403, detail="Access to source files is prohibited.")
        return await super().get_response(path, scope)

ui_dir = Path(__file__).parent.parent / "ui"
if ui_dir.exists():
    app.mount("/", SafeStaticFiles(directory=str(ui_dir), html=True), name="ui")
