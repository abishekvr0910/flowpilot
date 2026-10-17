"""
FlowPilot Local Productivity Insights Engine
Zero-egress, deterministic metrics tracking:
- Lifetime word count (e.g. 63.9K)
- Rolling dictation speed (Words Per Minute / WPM)
- Daily usage streaks
- Estimated typing time saved
- Active application breakdown
"""

import json
import os
import threading
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

INSIGHTS_FILE = Path.home() / ".flowpilot" / "insights.json"

DEFAULT_INSIGHTS: Dict[str, Any] = {
    "total_words": 0,
    "total_utterances": 0,
    "wpm_rolling": 150.0,
    "daily_streak": 1,
    "last_active_date": "",
    "time_saved_minutes": 0.0,
    "app_breakdown": {},
    "recent_sessions": []
}

class InsightsEngine:
    def __init__(self, storage_path: Optional[Path] = None):
        self._path = storage_path or INSIGHTS_FILE
        self._lock = threading.RLock()
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self._path.exists():
            return dict(DEFAULT_INSIGHTS)
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                saved = json.load(f)
                merged = dict(DEFAULT_INSIGHTS)
                merged.update(saved)
                return merged
        except Exception as e:
            print(f"[InsightsEngine Warning] Failed to read insights: {e}. Using defaults.")
            return dict(DEFAULT_INSIGHTS)

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            if os.path.exists(self._path):
                os.replace(tmp, self._path)
            else:
                os.rename(tmp, self._path)
        except Exception as e:
            print(f"[InsightsEngine Warning] Failed to write insights: {e}")

    def record_dictation(self, text: str, duration_sec: float, target_app: str = "Desktop") -> Dict[str, Any]:
        """
        Record completed dictation, recalculate WPM, streaks, and time saved.
        """
        if not text:
            return self.get_metrics()

        words = [w for w in text.strip().split() if w]
        word_count = len(words)
        if word_count == 0:
            return self.get_metrics()

        dur = max(0.5, float(duration_sec))
        session_wpm = round((word_count / dur) * 60.0, 1)

        # Clamped realistic bounds: 40 WPM to 350 WPM
        session_wpm = max(40.0, min(350.0, session_wpm))

        with self._lock:
            self._data["total_words"] += word_count
            self._data["total_utterances"] += 1

            # Exponentially weighted moving average for rolling WPM (alpha = 0.25)
            old_wpm = self._data.get("wpm_rolling", 150.0)
            new_wpm = round((0.75 * old_wpm) + (0.25 * session_wpm), 1)
            self._data["wpm_rolling"] = new_wpm

            # Update streak
            today_str = date.today().isoformat()
            last_date_str = self._data.get("last_active_date", "")

            if not last_date_str:
                self._data["daily_streak"] = 1
                self._data["last_active_date"] = today_str
            elif last_date_str != today_str:
                try:
                    last_date = date.fromisoformat(last_date_str)
                    diff = (date.today() - last_date).days
                    if diff == 1:
                        self._data["daily_streak"] += 1
                    elif diff > 1:
                        self._data["daily_streak"] = 1
                    self._data["last_active_date"] = today_str
                except Exception:
                    self._data["daily_streak"] = 1
                    self._data["last_active_date"] = today_str

            # Time saved: Average typing velocity is ~40 WPM; dictation velocity ~150 WPM
            # Saved time per word = (1/40 - 1/150) minutes ~ 0.01833 minutes
            minutes_saved = round(word_count * (1.0 / 40.0 - 1.0 / max(60.0, new_wpm)), 2)
            self._data["time_saved_minutes"] = round(self._data.get("time_saved_minutes", 0.0) + max(0.0, minutes_saved), 2)

            # App breakdown
            app_clean = target_app.strip() or "General"
            apps = self._data.setdefault("app_breakdown", {})
            apps[app_clean] = apps.get(app_clean, 0) + word_count

            # Keep last 50 session entries
            recent = self._data.setdefault("recent_sessions", [])
            recent.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "words": word_count,
                "duration": round(dur, 2),
                "wpm": session_wpm,
                "app": app_clean
            })
            if len(recent) > 50:
                self._data["recent_sessions"] = recent[-50:]

            self._save()

        return self.get_metrics()

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            total_words = self._data.get("total_words", 0)
            if total_words >= 1000:
                words_display = f"{total_words / 1000.0:.1f}K"
            else:
                words_display = str(total_words)

            return {
                "total_words": total_words,
                "total_words_formatted": words_display,
                "wpm": int(round(self._data.get("wpm_rolling", 150.0))),
                "streak": self._data.get("daily_streak", 1),
                "time_saved_minutes": round(self._data.get("time_saved_minutes", 0.0), 2),
                "time_saved_hours": round(self._data.get("time_saved_minutes", 0.0) / 60.0, 2),
                "total_utterances": self._data.get("total_utterances", 0),
                "recent_sessions": list(self._data.get("recent_sessions", [])),
                "app_breakdown": dict(self._data.get("app_breakdown", {}))
            }

    def reset_metrics(self) -> None:
        with self._lock:
            self._data = dict(DEFAULT_INSIGHTS)
            self._save()

_GLOBAL_INSIGHTS_ENGINE: Optional[InsightsEngine] = None
_INSIGHTS_LOCK = threading.Lock()

def get_insights_engine() -> InsightsEngine:
    global _GLOBAL_INSIGHTS_ENGINE
    if _GLOBAL_INSIGHTS_ENGINE is None:
        with _INSIGHTS_LOCK:
            if _GLOBAL_INSIGHTS_ENGINE is None:
                _GLOBAL_INSIGHTS_ENGINE = InsightsEngine()
    return _GLOBAL_INSIGHTS_ENGINE
