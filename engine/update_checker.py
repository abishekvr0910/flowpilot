"""
FlowPilot In-App Update Checker
Asynchronously checks GitHub Releases for new updates outside of active dictation.
Strictly adheres to FlowPilot's Zero Cloud Egress Invariant during dictation.
"""

import os
import sys
import json
import time
import re
import urllib.request
import threading
from typing import Optional, Dict, Any, Callable
from packaging.version import Version, InvalidVersion

from engine import __version__ as CURRENT_VERSION

GITHUB_REPO = "abishekvr0910/flowpilot"
RELEASES_LIST_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=20"
CHECK_INTERVAL_SECONDS = 86400  # 24 hours


def is_network_testing_active() -> bool:
    """Detects test suite or headless sandbox environments to keep network dormant."""
    return any(
        os.environ.get(var)
        for var in ("FLOWPILOT_HEADLESS", "FLOWPILOT_NO_NETWORK", "CI", "PYTEST_CURRENT_TEST")
    )


def parse_release_version(tag_or_version: str) -> Optional[Version]:
    """Parses arbitrary GitHub release tags into strict PEP 440 / SemVer Version objects."""
    if not tag_or_version:
        return None
    raw = str(tag_or_version).strip()
    raw = re.sub(r'^[vV]', '', raw)
    raw = re.sub(r'[-_]release$', '', raw, flags=re.IGNORECASE)
    try:
        return Version(raw)
    except InvalidVersion:
        # Fallback for non-standard tags: extract dotted numbers + rc
        m = re.search(r'(\d+(?:\.\d+)+(?:[-._]?(?:rc|a|b|preview)\.?\d*)?)', raw, flags=re.IGNORECASE)
        if m:
            try:
                return Version(m.group(1))
            except InvalidVersion:
                pass
        return None


def compare_versions(current: str, remote: str) -> bool:
    """Returns True if remote version is strictly newer than current version."""
    v_cur = parse_release_version(current)
    v_rem = parse_release_version(remote)
    if v_cur is not None and v_rem is not None:
        return v_rem > v_cur
    return False


def select_best_release(
    releases: list,
    current_version: str,
    include_prereleases: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Selects the newest eligible release matching channel preferences.
    Ignores draft releases. Only considers pre-releases if include_prereleases=True
    or if current_version is itself a pre-release.
    """
    cur_ver = parse_release_version(current_version)
    if cur_ver is None:
        return None

    allow_prereleases = include_prereleases or bool(cur_ver.is_prerelease)
    best_ver: Optional[Version] = None
    best_release: Optional[Dict[str, Any]] = None

    for rel in releases:
        if not isinstance(rel, dict) or rel.get("draft"):
            continue
        is_pre = bool(rel.get("prerelease", False))
        if is_pre and not allow_prereleases:
            continue

        tag = rel.get("tag_name", "")
        v = parse_release_version(tag)
        if v is None:
            continue

        if v > cur_ver:
            if best_ver is None or v > best_ver:
                best_ver = v
                best_release = rel

    return best_release


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
    ) -> bool:
        """
        Asynchronously checks for new releases on GitHub.
        Preempted immediately if network test environment is detected or dictation starts.

        on_result is invoked on the worker thread. GUI callers must marshal it to the
        Qt main thread (for example by passing a Qt Signal's ``emit``).
        Returns True when a check was started, False when it was skipped.
        """
        if is_network_testing_active():
            return False

        if not force and not config.get("check_for_updates", True):
            return False

        now = time.time()
        last_check = config.get("last_update_check_ts", 0)
        if not force and (now - last_check < CHECK_INTERVAL_SECONDS):
            return False

        with self._lock:
            if self._active_thread and self._active_thread.is_alive():
                return False
            self._abort_requested = False
            self._active_thread = threading.Thread(
                target=self._worker,
                args=(config, on_result),
                daemon=True,
                name="FlowPilot-UpdateChecker"
            )
            self._active_thread.start()
        return True

    def abort(self) -> None:
        """Immediately aborts any active update check when dictation begins."""
        self._abort_requested = True

    def _worker(self, config: Dict[str, Any], on_result: Optional[Callable[[Dict[str, Any]], None]]):
        result = {
            "update_available": False,
            "latest_version": self.current_version,
            "release_url": f"https://github.com/{GITHUB_REPO}/releases",
            "release_name": "",
            "checked_at": time.time(),
            "error": None,
        }
        try:
            if not RELEASES_LIST_API.startswith("https://"):
                raise ValueError(f"Insecure update URL scheme: {RELEASES_LIST_API}")
            req = urllib.request.Request(
                RELEASES_LIST_API,
                headers={
                    "User-Agent": f"FlowPilot-Desktop/{self.current_version} (Windows NT 10.0; x64)",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req, timeout=6.0) as resp:  # nosec B310
                if self._abort_requested:
                    return
                if resp.status != 200:
                    result["error"] = f"GitHub returned HTTP {resp.status}"
                else:
                    releases = json.loads(resp.read(1024 * 1024).decode("utf-8"))
                    channel_pre = bool(config.get("update_channel_prerelease", False))
                    best = select_best_release(
                        releases,
                        current_version=self.current_version,
                        include_prereleases=channel_pre
                    )
                    if best:
                        tag_clean = best.get("tag_name", "").lstrip("v")
                        result["update_available"] = True
                        result["latest_version"] = tag_clean
                        result["release_url"] = best.get("html_url", result["release_url"])
                        result["release_name"] = best.get("name", tag_clean)
        except Exception as exc:
            # Offline network or unauthenticated GitHub rate limits: report, never raise.
            result["error"] = f"{type(exc).__name__}: {exc}"[:200]
        finally:
            if not self._abort_requested:
                ts = int(time.time())
                config["last_update_check_ts"] = ts
                try:
                    # Persist only the throttle timestamp onto a fresh copy of the saved
                    # config so settings saved meanwhile by the UI are never overwritten.
                    from engine.config import load_config, save_config
                    fresh = load_config()
                    fresh["last_update_check_ts"] = ts
                    save_config(fresh)
                except Exception:
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
