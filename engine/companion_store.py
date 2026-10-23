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
    "schema_version": 2,
    "selected_asset_id": "kitty",  # "kitty", "mascot", "edge_line", "wave_bar", or custom
    "appearance_locked": True,     # Replaces double-click cycling with locked, explicit selection
    "visible": True,
    "visibility_mode": "smart",
    "last_visible_mode": "smart",
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
                if not isinstance(loaded, dict):
                    raise ValueError("companion.json must contain an object")
                data = DEFAULT_COMPANION_CONFIG.copy()
                data.update(loaded)
                if loaded.get("visibility_mode") not in ("smart", "always", "hidden"):
                    if "visible" in loaded:
                        data["visibility_mode"] = "always" if loaded["visible"] else "hidden"
                    else:
                        data["visibility_mode"] = "smart"
                if loaded.get("last_visible_mode") not in ("smart", "always"):
                    data["last_visible_mode"] = "smart" if data["visibility_mode"] == "hidden" else data["visibility_mode"]
                data["schema_version"] = 2
                data["visible"] = data["visibility_mode"] != "hidden"
                self._data = data
                if data != loaded:
                    self._persist_unlocked()
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
                if "visible" in cfg:
                    data["visibility_mode"] = "always" if cfg["visible"] else "hidden"
                    data["visible"] = bool(cfg["visible"])
                    data["last_visible_mode"] = "always"
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

    def set(self, key: str, value: Any) -> Any:
        if key == "visibility_mode":
            self.set_visibility_mode(value)
            return value
        with self._lock:
            self._data[key] = value
            self._persist_unlocked()
            return value

    def update(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Atomically updates specific keys and persists them to disk."""
        with self._lock:
            if "visibility_mode" in updates:
                mode = updates["visibility_mode"]
                if mode not in ("smart", "always", "hidden"):
                    raise ValueError("Invalid companion visibility mode")
            previous = self._data
            self._data = {**self._data, **updates}
            if "visibility_mode" in updates:
                if mode != "hidden":
                    self._data["last_visible_mode"] = mode
                self._data["visible"] = mode != "hidden"
            if not self._persist_unlocked():
                self._data = previous
                raise OSError("Could not save companion settings")
            return self._data.copy()

    def set_visibility_mode(self, mode: str) -> Dict[str, Any]:
        if mode not in ("smart", "always", "hidden"):
            raise ValueError("Invalid companion visibility mode")
        return self.update({"visibility_mode": mode})

    def save(self, data: Dict[str, Any]) -> None:
        """Atomically writes configuration to companion.json using tempfile replacement."""
        with self._lock:
            merged = DEFAULT_COMPANION_CONFIG.copy()
            merged.update(data)
            mode = merged.get("visibility_mode", "smart")
            if mode not in ("smart", "always", "hidden"):
                raise ValueError("Invalid companion visibility mode")
            merged["visible"] = mode != "hidden"
            if mode != "hidden":
                merged["last_visible_mode"] = mode
            self._data = merged
            self._persist_unlocked()

    def _persist_unlocked(self) -> bool:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            temp_path = self.companion_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.companion_file)
            return True
        except Exception as e:
            print(f"[CompanionStore Error] Failed to persist companion.json: {e}")
            return False

# Global singleton accessor
_store_instance: Optional[CompanionStore] = None

def get_companion_store() -> CompanionStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = CompanionStore()
    return _store_instance
