import json
import os
from pathlib import Path
from typing import List, Dict, Any

CONFIG_FILE = Path.home() / ".flowpilot" / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "engine_mode": "local",  # Local Faster-Whisper; cloud mode is rejected by STTEngine
    "cloud_provider": "groq",  # "groq" or "openai"
    "groq_api_key": "",
    "openai_api_key": "",
    "local_model_size": "base",  # "tiny", "base", "small", "medium"
    "beam_size": 1,  # Default greedy decoding (3x faster than beam search on CPU)
    "vad_filter": False,  # Pre-gated dictation audio does not require redundant VAD chunking (~480ms saved)
    "language": "en",  # Default English avoids ~1,060ms language-detection pass; 'auto' available in settings
    "enable_code_switching": True,
    "hotkey": "<ctrl>+<shift>+<space>",  # or push-to-talk key
    "hotkey_mode": "toggle",  # "toggle" (press to start, press to stop) or "push_to_talk"
    "active_tone_mode": "developer",  # "verbatim", "cleaned", "developer", "casual", "email"
    "auto_detect_active_app": True,
    "custom_vocabulary": [
        "Kubernetes", "GraphQL", "FastAPI", "Pydantic", "PostgreSQL",
        "Next.js", "TypeScript", "Python", "Whisper", "Docker", "AWS Lambda"
    ],
    "telemetry_enabled": False,  # Default disabled; opt-in required for pilot diagnostics
    "save_history_text": False,  # Legacy config history only; History Vault still stores dictations locally
    "auto_stop_on_silence": True,  # Wispr Flow behavior: auto-finalize after pause in speech
    "silence_timeout_sec": 0.85,  # Optimized conversational pause (down from 1.4s, saving ~550ms)
    "hud_style": "mascot",  # "mascot" (Cartoon companion Pilot) or "wave" (Wispr dynamic bars)
    "history": []
}

def load_config() -> Dict[str, Any]:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Merge defaults for any missing keys
            config = DEFAULT_CONFIG.copy()
            config.update(data)
            # Normalize hotkey format
            hk = config.get("hotkey", "<ctrl>+<shift>+<space>")
            if "+space" in hk and "+<space>" not in hk:
                config["hotkey"] = hk.replace("+space", "+<space>")
                save_config(config)
            return config
    except Exception as e:
        print(f"[Config] Error loading config: {e}. Using defaults.")
        return DEFAULT_CONFIG.copy()

def save_config(config: Dict[str, Any]) -> None:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Config] Error saving config: {e}")
