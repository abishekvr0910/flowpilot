"""
FlowPilot Local Preference Learning Module
Hermes-inspired deterministic adaptation with zero surveillance.
Tracks deliberate FlowPilot configuration choices per foreground application,
proposing transparent rules only after 3-day consensus.
Contains NO keystroke loggers, NO clipboard scrapers, and NO audio retention.
"""

import os
import json
import copy
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

MAX_OBSERVATIONS = 300
OBSERVATION_RETENTION_DAYS = 30
CONSENSUS_DAYS_REQUIRED = 3
CONSENSUS_WINDOW_DAYS = 14
CONSENSUS_THRESHOLD = 0.80

def _get_default_learning_data() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "enabled": False,         # Explicit opt-in required
        "observations": [],       # [{app_id, setting_key, value, date_str}]
        "approved_rules": {},     # {app_id: {setting_key: value}}
        "tombstones": []          # ["app_id:setting_key"]
    }

DEFAULT_LEARNING_DATA = _get_default_learning_data()

class PreferenceLearningEngine:
    _lock = threading.RLock()

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir)
        elif os.environ.get("FLOWPILOT_CONFIG_DIR"):
            self.storage_dir = Path(os.environ["FLOWPILOT_CONFIG_DIR"])
        else:
            self.storage_dir = Path.home() / ".flowpilot"

        self.storage_file = self.storage_dir / "learning.json"
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        with self._lock:
            if not self.storage_file.exists():
                self._data = _get_default_learning_data()
                self._persist_unlocked()
                return copy.deepcopy(self._data)

            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                data = _get_default_learning_data()
                data.update(loaded)
                self._data = data
                self._prune_expired_observations()
            except Exception as e:
                print(f"[LearningEngine] Error reading {self.storage_file}: {e}")
                self._data = _get_default_learning_data()
            return copy.deepcopy(self._data)


    def is_enabled(self) -> bool:
        with self._lock:
            return bool(self._data.get("enabled", False))

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._data["enabled"] = bool(enabled)
            self._persist_unlocked()

    def record_setting_action(self, app_id: str, setting_key: str, value: Any) -> None:
        """Records a deliberate user action within FlowPilot while app_id was foregrounded."""
        if not self.is_enabled():
            return
        if not app_id or not setting_key:
            return

        app_id_clean = Path(app_id).name.lower()
        tombstone_key = f"{app_id_clean}:{setting_key}"

        with self._lock:
            if tombstone_key in self._data.get("tombstones", []):
                return  # User suppressed suggestions for this rule

            today_str = datetime.now().strftime("%Y-%m-%d")
            observations = self._data.setdefault("observations", [])

            # Max 1 observation per app/setting/day to prevent rapid click poisoning
            for obs in observations:
                if (obs.get("app_id") == app_id_clean and 
                    obs.get("setting_key") == setting_key and 
                    obs.get("date_str") == today_str):
                    obs["value"] = value  # Update to latest value of the day
                    self._persist_unlocked()
                    return

            observations.append({
                "app_id": app_id_clean,
                "setting_key": setting_key,
                "value": value,
                "date_str": today_str
            })

            # Enforce max storage cap
            if len(observations) > MAX_OBSERVATIONS:
                self._data["observations"] = observations[-MAX_OBSERVATIONS:]

            self._persist_unlocked()

    def get_proposals(self) -> List[Dict[str, Any]]:
        """Evaluates historical observations and returns qualified suggestion cards."""
        with self._lock:
            if not self._data.get("enabled", False):
                return []

            cutoff = datetime.now() - timedelta(days=CONSENSUS_WINDOW_DAYS)
            proposals = []
            grouped: Dict[str, List[Dict[str, Any]]] = {}

            # Group recent observations by (app_id, setting_key)
            for obs in self._data.get("observations", []):
                try:
                    obs_date = datetime.strptime(obs["date_str"], "%Y-%m-%d")
                    if obs_date < cutoff:
                        continue
                except Exception:
                    continue

                key = f"{obs['app_id']}:{obs['setting_key']}"
                if key in self._data.get("tombstones", []):
                    continue
                if obs["app_id"] in self._data.get("approved_rules", {}):
                    if obs["setting_key"] in self._data["approved_rules"][obs["app_id"]]:
                        continue  # Rule already approved

                grouped.setdefault(key, []).append(obs)

            # Check 3-day consensus heuristic
            for key, obs_list in grouped.items():
                distinct_dates = {o["date_str"] for o in obs_list}
                if len(distinct_dates) >= CONSENSUS_DAYS_REQUIRED:
                    # Check consensus on specific value
                    value_counts: Dict[str, int] = {}
                    for o in obs_list:
                        val_str = json.dumps(o["value"], sort_keys=True)
                        value_counts[val_str] = value_counts.get(val_str, 0) + 1

                    total_obs = len(obs_list)
                    for val_str, count in value_counts.items():
                        if (count / total_obs) >= CONSENSUS_THRESHOLD:
                            app_id, setting_key = key.split(":", 1)
                            target_val = json.loads(val_str)
                            proposals.append({
                                "id": f"prop_{key}",
                                "app_id": app_id,
                                "setting_key": setting_key,
                                "value": target_val,
                                "days_observed": len(distinct_dates),
                                "consensus_pct": int((count / total_obs) * 100)
                            })
                            break

            return proposals

    def accept_proposal(self, proposal: Dict[str, Any]) -> None:
        """Approves a proposal into a permanent active rule."""
        app_id = proposal.get("app_id", "").lower()
        setting_key = proposal.get("setting_key", "")
        value = proposal.get("value")

        if not app_id or not setting_key:
            return

        with self._lock:
            rules = self._data.setdefault("approved_rules", {})
            rules.setdefault(app_id, {})[setting_key] = value
            self._persist_unlocked()

    def dismiss_proposal(self, proposal: Dict[str, Any], never_suggest: bool = False) -> None:
        """Dismisses a proposal; optionally adds a tombstone to permanently suppress it."""
        app_id = proposal.get("app_id", "").lower()
        setting_key = proposal.get("setting_key", "")
        key = f"{app_id}:{setting_key}"

        with self._lock:
            if never_suggest:
                tombstones = self._data.setdefault("tombstones", [])
                if key not in tombstones:
                    tombstones.append(key)

            # Remove associated observations so it doesn't immediately resurface
            self._data["observations"] = [
                o for o in self._data.get("observations", [])
                if f"{o.get('app_id')}:{o.get('setting_key')}" != key
            ]
            self._persist_unlocked()

    def get_approved_rules(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return self._data.get("approved_rules", {}).copy()

    def forget_rule(self, app_id: str, setting_key: str) -> None:
        """Deletes an active rule and records a tombstone preventing resurrection."""
        app_id_clean = app_id.lower()
        key = f"{app_id_clean}:{setting_key}"

        with self._lock:
            if app_id_clean in self._data.get("approved_rules", {}):
                self._data["approved_rules"][app_id_clean].pop(setting_key, None)
                if not self._data["approved_rules"][app_id_clean]:
                    self._data["approved_rules"].pop(app_id_clean, None)

            tombstones = self._data.setdefault("tombstones", [])
            if key not in tombstones:
                tombstones.append(key)

            self._persist_unlocked()

    def clear_all_learning_data(self) -> None:
        """Completely purges all observations, proposals, and approved rules."""
        with self._lock:
            enabled = self.is_enabled()
            self._data = _get_default_learning_data()
            self._data["enabled"] = enabled
            self._persist_unlocked()


    def _prune_expired_observations(self) -> None:
        cutoff = datetime.now() - timedelta(days=OBSERVATION_RETENTION_DAYS)
        valid = []
        for obs in self._data.get("observations", []):
            try:
                if datetime.strptime(obs["date_str"], "%Y-%m-%d") >= cutoff:
                    valid.append(obs)
            except Exception:
                pass
        self._data["observations"] = valid

    def _persist_unlocked(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            temp_path = self.storage_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.storage_file)
        except Exception as e:
            print(f"[LearningEngine Error] Failed to save {self.storage_file}: {e}")

_learning_instance: Optional[PreferenceLearningEngine] = None

def get_learning_engine() -> PreferenceLearningEngine:
    global _learning_instance
    if _learning_instance is None:
        _learning_instance = PreferenceLearningEngine()
    return _learning_instance
