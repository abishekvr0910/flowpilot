"""Focused regressions for configuration, injection, formatting, and release gates."""

import json
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.config import load_config, save_config
from engine.text_injector import TextInjector
from engine.writing_intelligence import WritingIntelligence
from tests import run_all_tests
from ui.notetaker_view import _parse_decision_lines
from scripts.package_windows_release import REQUIRED_NOTICES, main as package_main


def test_injector_process_detection_is_live():
    with patch("engine.text_injector.HAS_WIN32", True), \
         patch("engine.text_injector.sys.platform", "win32"), \
         patch("engine.text_injector.win32process.GetWindowThreadProcessId", return_value=(7, os.getpid())), \
         patch("engine.text_injector.psutil.Process") as process:
        process.return_value.name.return_value = "Slack.exe"
        assert TextInjector._is_flowpilot_window(12345) is True
        assert TextInjector._get_target_process_name(12345) == "slack.exe"


def test_failed_config_write_keeps_last_good_file():
    with tempfile.TemporaryDirectory(prefix="flowpilot-config-atomic-") as folder:
        cfg_file = Path(folder) / "config.json"
        with patch.dict(os.environ, {"FLOWPILOT_CONFIG_FILE": str(cfg_file)}):
            assert save_config({"hotkey": "F9"}) is True
            with patch("engine.config.json.dump", side_effect=RuntimeError("interrupted serialization")):
                assert save_config({"hotkey": "F10"}) is False
        assert json.loads(cfg_file.read_text(encoding="utf-8")) == {"hotkey": "F9"}
        assert not list(Path(folder).glob(".config.json.*.tmp"))


def test_spoken_tab_requires_explicit_command():
    writer = WritingIntelligence(config={"language": "en"}, personalization=object())
    prose, changes = writer._apply_spoken_commands("The browser tab crashed.")
    assert prose == "The browser tab crashed."
    assert "Inserted tab" not in changes
    command, changes = writer._apply_spoken_commands("name press tab value")
    assert "\t" in command
    assert "Inserted tab" in changes


def test_decision_export_drops_markup_prefix():
    assert _parse_decision_lines("- **Decision:** Ship on Friday\n- Other note") == ["Ship on Friday"]


def test_strict_release_gate_rejects_skips():
    skipped = subprocess.CompletedProcess(
        args=["python", "fake.py"], returncode=0,
        stdout="[RESULT] SKIPPED: no interactive desktop", stderr=""
    )
    with patch.object(run_all_tests, "TESTS", [("synthetic skip", "fake.py")]), \
         patch.object(run_all_tests.subprocess, "run", return_value=skipped):
        with redirect_stdout(io.StringIO()) as output:
            assert run_all_tests.run_suite(require_all=True) is False
            assert run_all_tests.run_suite(require_all=False) is True
        assert "RELEASE GATE BLOCKED" in output.getvalue()


def test_fresh_profile_keeps_history_disabled():
    with tempfile.TemporaryDirectory(prefix="flowpilot-fresh-profile-") as folder:
        config_file = Path(folder) / "config.json"
        with patch.dict(os.environ, {
            "FLOWPILOT_CONFIG_DIR": folder,
            "FLOWPILOT_CONFIG_FILE": str(config_file),
        }):
            assert load_config()["save_history_text"] is False
        assert json.loads(config_file.read_text(encoding="utf-8"))["save_history_text"] is False
        assert not (Path(folder) / "history" / "history_vault.json").exists()


def test_existing_profile_survives_packaged_launch():
    """Launch the actual candidate with an isolated, previously populated profile."""
    with tempfile.TemporaryDirectory(prefix="flowpilot-existing-profile-") as folder:
        root = Path(folder)
        (root / "history").mkdir()
        expected = {
            "config.json": {
                "hotkey": "<f9>",
                "language": "hi",
                "save_history_text": True,
                "local_model_size": "base",
            },
            "personalization.json": {
                "version": 2,
                "dictionary": [{
                    "term": "ReleaseProbe", "alias": "release probe",
                    "aliases": ["release probe"], "language": "en", "profile": "developer",
                }],
                "snippets": [{"trigger": "existing phrase", "expansion": "Existing pilot output"}],
                "tombstones": ["term:deleted probe"],
            },
            "companion.json": {
                "schema_version": 1,
                "selected_asset_id": "kitty",
                "appearance_locked": True,
                "cat_palette": "orange tabby",
                "hud_x": 120,
                "hud_y": 160,
            },
            "history/history_vault.json": {
                "entries": [{
                    "id": "existing-record", "formatted_text": "Existing pilot note",
                    "raw_text": "Existing pilot note", "language": "en",
                }],
            },
        }
        for relative_path, content in expected.items():
            (root / relative_path).write_text(
                json.dumps(content, ensure_ascii=False), encoding="utf-8"
            )

        test_env = os.environ.copy()
        test_env["FLOWPILOT_CONFIG_DIR"] = folder
        test_env["FLOWPILOT_CONFIG_FILE"] = str(root / "config.json")
        test_env["FLOWPILOT_SMOKE_USE_CALLER_PROFILE"] = "1"
        test_env["FLOWPILOT_TEST_EXE"] = os.path.abspath(
            test_env.get("FLOWPILOT_TEST_EXE")
            or str(PROJECT_ROOT / "dist" / "FlowPilot" / "FlowPilot.exe")
        )
        newest_source_mtime = max(
            p.stat().st_mtime
            for folder in ("engine", "ui")
            for p in PROJECT_ROOT.rglob(folder + "/*.py")
        )
        if Path(test_env["FLOWPILOT_TEST_EXE"]).stat().st_mtime < newest_source_mtime:
            print(
                "[RELEASE] WARNING: the packaged binary is older than the newest source file.\n"
                f"[RELEASE]   binary : {test_env['FLOWPILOT_TEST_EXE']}\n"
                "[RELEASE]   Rebuild the binary or stage FLOWPILOT_TEST_EXE before trusting this result."
            )
        smoke = subprocess.run(
            [sys.executable, "-X", "utf8", str(PROJECT_ROOT / "tests" / "test_standalone_binary_smoke.py")],
            cwd=PROJECT_ROOT, env=test_env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=90,
        )
        assert smoke.returncode == 0, (smoke.stdout[-2000:], smoke.stderr[-2000:])
        assert "STANDALONE BINARY SMOKE TEST PASSED" in smoke.stdout
        for relative_path, content in expected.items():
            actual = json.loads((root / relative_path).read_text(encoding="utf-8"))
            for key, value in content.items():
                if relative_path == "companion.json" and key == "schema_version":
                    assert actual.get(key) == 2, (relative_path, key)
                    assert actual.get("visibility_mode") == "smart"
                    assert actual.get("last_visible_mode") == "smart"
                    continue
                assert actual.get(key) == value, (relative_path, key)


def test_requested_signing_failure_never_creates_archive():
    with tempfile.TemporaryDirectory(prefix="flowpilot-signing-check-") as folder:
        bundle = Path(folder) / "bundle"
        bundle.mkdir()
        cert = Path(folder) / "signing.pfx"
        cert.write_bytes(b"test certificate placeholder")
        archive = Path(folder) / "candidate.zip"
        with patch("scripts.package_windows_release.sign_executable", return_value={
            "signed": False, "status": "SIGN_FAILED",
        }), patch("scripts.package_windows_release.package") as package:
            try:
                package_main(["--bundle", str(bundle), "--archive", str(archive), "--cert", str(cert)])
            except RuntimeError as exc:
                assert "SIGN_FAILED" in str(exc)
            else:
                raise AssertionError("Requested signing did not fail closed")
            package.assert_not_called()
        assert not archive.exists()


def test_packager_help_imports_cleanly():
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(PROJECT_ROOT / "scripts" / "package_windows_release.py"), "--help"],
        cwd=PROJECT_ROOT, capture_output=True, encoding="utf-8", errors="replace", timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert "--cert-password-env" in result.stdout


def test_release_notices_exist_in_a_fresh_checkout():
    for relative_path in REQUIRED_NOTICES:
        assert (PROJECT_ROOT / relative_path).is_file(), relative_path


if __name__ == "__main__":
    test_injector_process_detection_is_live()
    test_failed_config_write_keeps_last_good_file()
    test_spoken_tab_requires_explicit_command()
    test_decision_export_drops_markup_prefix()
    test_strict_release_gate_rejects_skips()
    test_fresh_profile_keeps_history_disabled()
    test_existing_profile_survives_packaged_launch()
    test_requested_signing_failure_never_creates_archive()
    test_packager_help_imports_cleanly()
    test_release_notices_exist_in_a_fresh_checkout()
    print("[RESULT] Release integrity regression guards PASSED.")
