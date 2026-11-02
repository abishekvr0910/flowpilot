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


if __name__ == "__main__":
    unittest.main()
