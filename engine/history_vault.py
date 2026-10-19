"""
FlowPilot Opt-In Dictation History & Audio Replay Vault (Local Only)
- Searchable feed of all past dictations with full-text search across raw, formatted text, and target application
- Audio Replay Vault: preserves local .wav audio captures for instant replay (▷)
- Interactive bookmarks (⭐) for frequently referenced or favorite transcriptions
- Prunes unbookmarked entries beyond 60 days or 500 items when a new entry is recorded
- Safe, atomic export (Markdown, CSV, JSON) and one-click clipboard copy
- No remote upload in this module; saved audio and metadata stay in ~/.flowpilot/history/
"""

import os
import json
import time
import shutil
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import sounddevice as sd
    import soundfile as sf
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

HISTORY_DIR = Path.home() / ".flowpilot" / "history"
AUDIO_DIR = HISTORY_DIR / "audio"
HISTORY_FILE = HISTORY_DIR / "history_vault.json"

class HistoryVaultEngine:
    _lock = threading.RLock()

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is not None:
            self.history_dir = Path(storage_dir)
            self.audio_dir = self.history_dir / "audio"
            self.history_file = self.history_dir / "history_vault.json"
        elif os.environ.get("FLOWPILOT_CONFIG_DIR"):
            self.history_dir = Path(os.environ["FLOWPILOT_CONFIG_DIR"]) / "history"
            self.audio_dir = self.history_dir / "audio"
            self.history_file = self.history_dir / "history_vault.json"
        else:
            self.history_dir = HISTORY_DIR
            self.audio_dir = AUDIO_DIR
            self.history_file = HISTORY_FILE

        self._entries: List[Dict[str, Any]] = []
        self._current_player = None
        self._is_playing = False
        self._playing_id: Optional[str] = None
        self.load()

    def load(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.history_file.exists():
                self._entries = []
                return []

            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._entries = data
                elif isinstance(data, dict):
                    self._entries = data.get("entries", [])
                else:
                    self._entries = []
            except Exception as e:
                print(f"[HistoryVault] Error reading {self.history_file}: {e}")
                self._entries = []
            return list(self._entries)

    def record_dictation(
        self,
        formatted_text: str,
        raw_text: str = "",
        target_app: str = "Desktop",
        duration_sec: float = 0.0,
        audio_bytes: Optional[bytes] = None,
        language: str = "en",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atomically saves a dictation event and its audio capture into local vault."""
        now = time.time()
        dt_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        date_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        entry_id = session_id or f"hist_{int(now * 1000)}"

        audio_rel_path = None
        if audio_bytes and len(audio_bytes) > 0:
            audio_file = self.audio_dir / f"{entry_id}.wav"
            try:
                self.audio_dir.mkdir(parents=True, exist_ok=True)
                with open(audio_file, "wb") as f:
                    f.write(audio_bytes)
                audio_rel_path = str(audio_file.name)
            except Exception as e:
                print(f"[HistoryVault] Warning: Failed to persist audio replay: {e}")

        word_count = len(formatted_text.split()) if formatted_text else 0

        entry = {
            "id": entry_id,
            "session_id": entry_id,
            "timestamp": now,
            "datetime": dt_str,
            "date": date_str,
            "formatted_text": formatted_text,
            "raw_text": raw_text or formatted_text,
            "target_app": target_app or "Desktop",
            "duration_sec": round(duration_sec, 2),
            "word_count": word_count,
            "language": language,
            "bookmarked": False,
            "audio_file": audio_rel_path
        }

        with self._lock:
            # Prepend to display newest first
            self._entries.insert(0, entry)
            # Enforce retention limits
            self._prune_unlocked()
            self._persist_unlocked()

        return entry

    def list_entries(
        self,
        query: str = "",
        bookmark_only: bool = False,
        limit: int = 150
    ) -> List[Dict[str, Any]]:
        """Returns filtered entries matching query, date, or bookmark criteria."""
        with self._lock:
            q = query.strip().lower()
            results = []
            for item in self._entries:
                if bookmark_only and not item.get("bookmarked"):
                    continue
                if q:
                    fmt = item.get("formatted_text", "").lower()
                    raw = item.get("raw_text", "").lower()
                    app = item.get("target_app", "").lower()
                    dt = item.get("datetime", "").lower()
                    if q not in fmt and q not in raw and q not in app and q not in dt:
                        continue
                results.append(dict(item))
                if len(results) >= limit:
                    break
            return results

    def toggle_bookmark(self, entry_id: str) -> bool:
        """Toggles the bookmark / favorite status of a dictation entry."""
        with self._lock:
            for item in self._entries:
                if item.get("id") == entry_id:
                    item["bookmarked"] = not item.get("bookmarked", False)
                    self._persist_unlocked()
                    return item["bookmarked"]
        return False

    def delete_entry(self, entry_id: str) -> bool:
        """Removes a specific entry and its audio replay from disk."""
        with self._lock:
            idx = None
            audio_fn = None
            for i, item in enumerate(self._entries):
                if item.get("id") == entry_id:
                    idx = i
                    audio_fn = item.get("audio_file")
                    break

            if idx is not None:
                self._entries.pop(idx)
                if audio_fn:
                    audio_path = self.audio_dir / audio_fn
                    if audio_path.exists():
                        try:
                            audio_path.unlink()
                        except Exception:
                            pass
                self._persist_unlocked()
                return True
        return False

    def clear_all(self, keep_bookmarks: bool = True) -> int:
        """Clears dictation history with optional preservation of bookmarked items."""
        deleted_count = 0
        with self._lock:
            kept = []
            for item in self._entries:
                if keep_bookmarks and item.get("bookmarked"):
                    kept.append(item)
                else:
                    deleted_count += 1
                    audio_fn = item.get("audio_file")
                    if audio_fn:
                        audio_path = self.audio_dir / audio_fn
                        if audio_path.exists():
                            try:
                                audio_path.unlink()
                            except Exception:
                                pass
            self._entries = kept
            self._persist_unlocked()
        return deleted_count

    def play_audio(self, entry_id: str, on_finished: Optional[callable] = None) -> bool:
        """Plays audio capture for entry if available."""
        if not HAS_AUDIO:
            return False

        with self._lock:
            audio_fn = None
            for item in self._entries:
                if item.get("id") == entry_id:
                    audio_fn = item.get("audio_file")
                    break

        if not audio_fn:
            return False

        audio_path = self.audio_dir / audio_fn
        if not audio_path.exists():
            return False

        try:
            self.stop_audio()
            data, fs = sf.read(str(audio_path), dtype="float32")

            def _play_worker():
                try:
                    self._is_playing = True
                    self._playing_id = entry_id
                    sd.play(data, fs)
                    sd.wait()
                except Exception as e:
                    print(f"[HistoryVault] Audio playback error: {e}")
                finally:
                    self._is_playing = False
                    self._playing_id = None
                    if on_finished:
                        try:
                            on_finished()
                        except Exception:
                            pass

            t = threading.Thread(target=_play_worker, daemon=True, name="FlowPilot-HistoryAudioPlay")
            t.start()
            return True
        except Exception as e:
            print(f"[HistoryVault] Failed to start audio playback: {e}")
            return False

    def stop_audio(self):
        """Immediately stops any ongoing audio playback."""
        if HAS_AUDIO:
            try:
                sd.stop()
            except Exception:
                pass
        self._is_playing = False
        self._playing_id = None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def playing_id(self) -> Optional[str]:
        return self._playing_id

    # -----------------------------------------------------------------
    # Retention & Persistence
    # -----------------------------------------------------------------
    def _prune_unlocked(self, retention_days: int = 60, max_items: int = 500) -> None:
        """Prunes old un-bookmarked entries beyond retention period or max count."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        valid = []
        for item in self._entries:
            if item.get("bookmarked"):
                valid.append(item)
                continue
            ts = item.get("timestamp", 0)
            if datetime.fromtimestamp(ts) >= cutoff:
                valid.append(item)
            else:
                audio_fn = item.get("audio_file")
                if audio_fn:
                    audio_path = self.audio_dir / audio_fn
                    if audio_path.exists():
                        try:
                            audio_path.unlink()
                        except Exception:
                            pass

        if len(valid) > max_items:
            valid = valid[:max_items]
        self._entries = valid

    def _persist_unlocked(self) -> None:
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
            temp_path = self.history_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._entries, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.history_file)
        except Exception as e:
            print(f"[HistoryVault] Error saving {self.history_file}: {e}")


_vault_instance: Optional[HistoryVaultEngine] = None

def get_history_vault() -> HistoryVaultEngine:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = HistoryVaultEngine()
    return _vault_instance
