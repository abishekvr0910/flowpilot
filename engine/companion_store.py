"""
FlowPilot Companion Store
Centralized, thread-safe, atomic persistence for companion settings,
asset selections, motion presets, and appearance lock state.
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional

DEFAULT_COMPANION_CONFIG: Dict[str, Any] = {
    "schema_version": 1,
    "selected_asset_id": "kitty",  # "kitty", "mascot", "edge_line", "wave_bar", or custom
    "appearance_locked": True,     # Replaces double-click cycling with locked, explicit selection
    "visible": True,
    "size_scale": 1.0,
    "motion_preset": "gentle_bob", # "breathe", "gentle_bob", "tiny_tilt", "audio_pulse", "celebration", "reduced_motion"
    "reduced_motion": False,
    "cat_palette": "orange tabby",
    "cat_sound": True,
    "hud_x": None,
    "hud_y": None,
    "tombstones": []
}

class CompanionStore:
    _lock = threading.RLock()

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir)
        elif os.environ.get("FLOWPILOT_CONFIG_DIR"):
            self.storage_dir = Path(os.environ["FLOWPILOT_CONFIG_DIR"])
        else:
            self.storage_dir = Path.home() / ".flowpilot"
            
        self.companion_file = self.storage_dir / "companion.json"
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads companion configuration atomically with migration fallback."""
        with self._lock:
            if not self.companion_file.exists():
                self._migrate_or_init()
                return self._data.copy()

            try:
                with open(self.companion_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                data = DEFAULT_COMPANION_CONFIG.copy()
                data.update(loaded)
                self._data = data
            except Exception as e:
                print(f"[CompanionStore Warning] Failed to read {self.companion_file}: {e}. Initializing defaults.")
                self._migrate_or_init()

            return self._data.copy()

    def _migrate_or_init(self) -> None:
        """Migrates legacy HUD settings from config.json if companion.json does not exist."""
        data = DEFAULT_COMPANION_CONFIG.copy()
        config_file = self.storage_dir / "config.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if "hud_style" in cfg:
                    data["selected_asset_id"] = cfg["hud_style"]
                if "cat_palette" in cfg:
                    data["cat_palette"] = cfg["cat_palette"]
                if "cat_sound" in cfg:
                    data["cat_sound"] = bool(cfg["cat_sound"])
                if "hud_x" in cfg:
                    data["hud_x"] = cfg["hud_x"]
                if "hud_y" in cfg:
                    data["hud_y"] = cfg["hud_y"]
                if "appearance_locked" in cfg:
                    data["appearance_locked"] = bool(cfg["appearance_locked"])
            except Exception:
                pass

        self._data = data
        self._persist_unlocked()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._data.copy()

    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Atomically updates specific keys and persists them to disk."""
        with self._lock:
            self._data.update(updates)
            self._persist_unlocked()
            return self._data.copy()

    def save(self, data: Dict[str, Any]) -> None:
        """Atomically writes configuration to companion.json using tempfile replacement."""
        with self._lock:
            self._data = DEFAULT_COMPANION_CONFIG.copy()
            self._data.update(data)
            self._persist_unlocked()

    def _persist_unlocked(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            temp_path = self.companion_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.companion_file)
        except Exception as e:
            print(f"[CompanionStore Error] Failed to persist companion.json: {e}")

# Global singleton accessor
_store_instance: Optional[CompanionStore] = None

def get_companion_store() -> CompanionStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = CompanionStore()
    return _store_instance
