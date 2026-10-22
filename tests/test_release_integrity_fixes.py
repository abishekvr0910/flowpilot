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

from engine.config import save_config
from engine.text_injector import TextInjector
from engine.writing_intelligence import WritingIntelligence
from tests import run_all_tests
from ui.notetaker_view import _parse_decision_lines


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


if __name__ == "__main__":
    test_injector_process_detection_is_live()
    test_failed_config_write_keeps_last_good_file()
    test_spoken_tab_requires_explicit_command()
    test_decision_export_drops_markup_prefix()
    test_strict_release_gate_rejects_skips()
    print("[RESULT] Release integrity regression guards PASSED.")
