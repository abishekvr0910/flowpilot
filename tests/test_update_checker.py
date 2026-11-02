"""
Tests for FlowPilot In-App Update Checker.
Validates PEP 440 version parsing, SemVer RC ordering, channel filtering, and API release selection.
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from packaging.version import Version
from engine.update_checker import (
    parse_release_version,
    compare_versions,
    select_best_release,
    UpdateChecker
)

class TestUpdateChecker(unittest.TestCase):

    def test_parse_release_version(self):
        self.assertEqual(parse_release_version("v3.1.0"), Version("3.1.0"))
        self.assertEqual(parse_release_version("3.1.0"), Version("3.1.0"))
        self.assertEqual(parse_release_version("v3.1.0-RC13"), Version("3.1.0rc13"))
        self.assertEqual(parse_release_version("v3.0.2-release"), Version("3.0.2"))
        self.assertIsNone(parse_release_version(""))
        self.assertIsNone(parse_release_version(None))

    def test_compare_versions_pep440_ordering(self):
        # 3.1.0-RC11 vs 3.1.0-RC13
        self.assertTrue(compare_versions("3.1.0-RC11", "3.1.0-RC13"))
        self.assertFalse(compare_versions("3.1.0-RC13", "3.1.0-RC11"))

        # RC vs Final Release: RC is older than final
        self.assertTrue(compare_versions("3.1.0-RC13", "3.1.0"))
        self.assertFalse(compare_versions("3.1.0", "3.1.0-RC13"))

        # 3.0.2 vs 3.1.0-RC13
        self.assertTrue(compare_versions("3.0.2", "3.1.0-RC13"))

        # Identical versions
        self.assertFalse(compare_versions("3.1.0", "3.1.0"))
        self.assertFalse(compare_versions("v3.1.0-RC13", "3.1.0-RC13"))

    def test_select_best_release_stable_user(self):
        releases = [
            {"tag_name": "v3.1.0-RC13", "prerelease": True, "draft": False},
            {"tag_name": "v3.1.0-RC12", "prerelease": True, "draft": False},
            {"tag_name": "v3.0.2-release", "prerelease": False, "draft": False},
        ]
        # User on stable 3.0.2 with prereleases disabled: no stable update exists
        best = select_best_release(releases, current_version="3.0.2", include_prereleases=False)
        self.assertIsNone(best)

        # User on stable 3.0.1: 3.0.2 is selected
        best2 = select_best_release(releases, current_version="3.0.1", include_prereleases=False)
        self.assertIsNotNone(best2)
        self.assertEqual(best2["tag_name"], "v3.0.2-release")

    def test_select_best_release_prerelease_user(self):
        releases = [
            {"tag_name": "v3.1.0-RC13", "prerelease": True, "draft": False},
            {"tag_name": "v3.1.0-RC11", "prerelease": True, "draft": False},
            {"tag_name": "v3.0.2-release", "prerelease": False, "draft": False},
        ]
        # User on 3.1.0-RC11: naturally receives RC13 update
        best = select_best_release(releases, current_version="3.1.0-RC11", include_prereleases=False)
        self.assertIsNotNone(best)
        self.assertEqual(best["tag_name"], "v3.1.0-RC13")

        # User on 3.1.0-RC13: up to date
        best2 = select_best_release(releases, current_version="3.1.0-RC13", include_prereleases=False)
        self.assertIsNone(best2)

    def test_select_best_release_draft_ignored(self):
        releases = [
            {"tag_name": "v3.2.0", "prerelease": False, "draft": True},
            {"tag_name": "v3.0.2-release", "prerelease": False, "draft": False},
        ]
        best = select_best_release(releases, current_version="3.0.1")
        self.assertEqual(best["tag_name"], "v3.0.2-release")

    def test_worker_persists_throttle_timestamp_to_disk(self):
        import tempfile
        import os
        from unittest.mock import patch, MagicMock
        from engine.config import load_config, save_config

        with tempfile.TemporaryDirectory() as td:
            cfg_file = os.path.join(td, "config.json")
            with patch.dict(os.environ, {"FLOWPILOT_CONFIG_FILE": cfg_file}):
                cfg = load_config()
                self.assertEqual(cfg.get("last_update_check_ts", 0), 0)

                checker = UpdateChecker("3.1.0")
                # Mock network request to raise an exception (e.g. offline)
                with patch("urllib.request.urlopen", side_effect=Exception("offline test")):
                    checker._worker(cfg, on_result=None)

                # Verify in-memory dict updated
                self.assertGreater(cfg.get("last_update_check_ts", 0), 0)

                # Reload from disk to verify atomic file persistence
                reloaded = load_config()
                self.assertEqual(reloaded["last_update_check_ts"], cfg["last_update_check_ts"])


    def test_async_reports_skip_when_network_disabled(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"FLOWPILOT_NO_NETWORK": "1"}):
            started = UpdateChecker("3.1.0").check_for_updates_async({}, on_result=None, force=True)
        self.assertFalse(started)

    def test_worker_reports_error_when_offline(self):
        import tempfile, os
        from unittest.mock import patch
        from engine.config import load_config
        received = []
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"FLOWPILOT_CONFIG_FILE": os.path.join(td, "config.json")}):
                cfg = load_config()
                with patch("urllib.request.urlopen", side_effect=OSError("offline test")):
                    UpdateChecker("3.1.0")._worker(cfg, on_result=received.append)
        self.assertEqual(len(received), 1)
        self.assertFalse(received[0]["update_available"])
        self.assertTrue(received[0]["error"])

    def test_worker_keeps_settings_saved_meanwhile(self):
        """The throttle write must not overwrite settings the UI saved after the check began."""
        import tempfile, os
        from unittest.mock import patch
        from engine.config import load_config, save_config
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"FLOWPILOT_CONFIG_FILE": os.path.join(td, "config.json")}):
                stale = load_config()
                newer = load_config()
                newer["hotkey"] = "F9"
                save_config(newer)
                with patch("urllib.request.urlopen", side_effect=OSError("offline test")):
                    UpdateChecker("3.1.0")._worker(stale, on_result=None)
                reloaded = load_config()
        self.assertEqual(reloaded["hotkey"], "F9")
        self.assertGreater(reloaded["last_update_check_ts"], 0)

    def test_settings_relay_delivers_result_on_gui_thread(self):
        """Regression: results from the worker thread must reach the Qt GUI thread."""
        import os, threading
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from ui.settings_dialog import _UpdateResultRelay
        app = QApplication.instance() or QApplication([])
        relay = _UpdateResultRelay()
        seen = []
        relay.result_ready.connect(lambda res: seen.append((res, threading.current_thread() is threading.main_thread())))
        threading.Thread(target=relay.result_ready.emit, args=({"update_available": False, "error": None},)).start()
        QTimer.singleShot(800, app.quit)
        app.exec()
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0][1], "result was not delivered on the GUI thread")


if __name__ == "__main__":
    unittest.main()
