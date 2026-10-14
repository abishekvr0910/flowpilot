import json
import os
from pathlib import Path
from typing import List, Dict, Any

CONFIG_FILE = Path.home() / ".flowpilot" / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "engine_mode": "local",  # "local" (Faster-Whisper offline) or "cloud"
    "cloud_provider": "groq",  # "groq" or "openai"
    "groq_api_key": "",
    "openai_api_key": "",
    "local_model_size": "base",  # "tiny", "base", "small", "medium"
    "language": "auto",  # "auto" or ISO code e.g. "en", "es", "fr", "de", "hi", etc.
    "enable_code_switching": True,
    "hotkey": "<ctrl>+<shift>+<space>",  # or push-to-talk key
    "hotkey_mode": "toggle",  # "toggle" (press to start, press to stop) or "push_to_talk"
    "active_tone_mode": "developer",  # "verbatim", "cleaned", "developer", "casual", "email"
    "auto_detect_active_app": True,
    "custom_vocabulary": [
        "Kubernetes", "GraphQL", "FastAPI", "Pydantic", "PostgreSQL",
        "Next.js", "TypeScript", "Python", "Whisper", "Docker", "AWS Lambda"
    ],
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
