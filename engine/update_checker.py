"""
FlowPilot In-App Update Checker
Asynchronously checks GitHub Releases for new updates outside of active dictation.
Strictly adheres to FlowPilot's Zero Cloud Egress Invariant during dictation.
"""

import os
import sys
import json
import time
import urllib.request
import threading
from typing import Optional, Dict, Any, Callable

GITHUB_REPO = "abishekvr0910/flowpilot"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "3.1.0"
CHECK_INTERVAL_SECONDS = 86400  # 24 hours


def is_network_testing_active() -> bool:
    """Detects test suite or headless sandbox environments to keep network dormant."""
    return any(
        os.environ.get(var)
        for var in ("FLOWPILOT_HEADLESS", "FLOWPILOT_NO_NETWORK", "CI", "PYTEST_CURRENT_TEST")
    )


def compare_versions(current: str, remote: str) -> bool:
    """Returns True if remote version is newer than current version."""
    import re
    def normalize(v: str):
        v = v.lstrip("v").strip()
        nums = [int(x) for x in re.findall(r"\d+", v)]
        is_rc = "-rc" in v.lower() or "rc" in v.lower()
        return (nums, 0 if is_rc else 1)

    try:
        cur_norm = normalize(current)
        rem_norm = normalize(remote)
        return rem_norm > cur_norm
    except Exception:
        return remote.lstrip("v") != current.lstrip("v")


class UpdateChecker:
    def __init__(self, current_version: str = CURRENT_VERSION):
        self.current_version = current_version
        self._lock = threading.Lock()
        self._active_thread: Optional[threading.Thread] = None
        self._abort_requested = False

    def check_for_updates_async(
        self,
        config: Dict[str, Any],
        on_result: Optional[Callable[[Dict[str, Any]], None]] = None,
        force: bool = False
    ) -> None:
        """
        Asynchronously checks for new releases on GitHub.
        Preempted immediately if network test environment is detected or dictation starts.
        """
        if is_network_testing_active():
            return

        if not force and not config.get("check_for_updates", True):
            return

        now = time.time()
        last_check = config.get("last_update_check_ts", 0)
        if not force and (now - last_check < CHECK_INTERVAL_SECONDS):
            return

        with self._lock:
            if self._active_thread and self._active_thread.is_alive():
                return
            self._abort_requested = False
            self._active_thread = threading.Thread(
                target=self._worker,
                args=(config, on_result),
                daemon=True,
                name="FlowPilot-UpdateChecker"
            )
            self._active_thread.start()

    def abort(self) -> None:
        """Immediately aborts any active update check when dictation begins."""
        self._abort_requested = True

    def _worker(self, config: Dict[str, Any], on_result: Optional[Callable[[Dict[str, Any]], None]]):
        result = {
            "update_available": False,
            "latest_version": self.current_version,
            "release_url": f"https://github.com/{GITHUB_REPO}/releases",
            "release_name": "",
            "checked_at": time.time()
        }
        try:
            req = urllib.request.Request(
                LATEST_RELEASE_API,
                headers={
                    "User-Agent": f"FlowPilot-Desktop/{self.current_version} (Windows NT 10.0; x64)",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if self._abort_requested:
                    return
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    tag = data.get("tag_name", "").lstrip("v")
                    url = data.get("html_url", result["release_url"])
                    name = data.get("name", tag)

                    if tag and compare_versions(self.current_version, tag):
                        result["update_available"] = True
                        result["latest_version"] = tag
                        result["release_url"] = url
                        result["release_name"] = name
                    config["last_update_check_ts"] = time.time()
        except Exception:
            # Silent failure: unauthenticated GitHub rate limits or offline network
            pass

        if not self._abort_requested and on_result:
            try:
                on_result(result)
            except Exception:
                pass


# Global singleton
_checker: Optional[UpdateChecker] = None

def get_update_checker() -> UpdateChecker:
    global _checker
    if _checker is None:
        _checker = UpdateChecker()
    return _checker
