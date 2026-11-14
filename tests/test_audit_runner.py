"""Strict release gates must recognize framework skips on either output stream."""
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests import run_all_tests


class AuditRunnerTests(unittest.TestCase):
    def test_framework_skips_block_strict_release_gate(self):
        for stdout, stderr in (("", "OK (skipped=2)"), ("4 passed, 1 skipped in 0.2s", ""),
                               ("", "[SKIP] no desktop"), ("[RESULT] SKIPPED: no model", "")):
            with self.subTest(stdout=stdout, stderr=stderr):
                result = subprocess.CompletedProcess([], 0, stdout, stderr)
                with patch.object(run_all_tests, "TESTS", [("probe", "probe.py")]), \
                     patch.object(run_all_tests.subprocess, "run", return_value=result), \
                     redirect_stdout(io.StringIO()):
                    self.assertFalse(run_all_tests.run_suite(require_all=True))
                    self.assertTrue(run_all_tests.run_suite(require_all=False))

    def test_zero_skips_does_not_block(self):
        result = subprocess.CompletedProcess([], 0, "3 passed, 0 skipped", "")
        with patch.object(run_all_tests, "TESTS", [("probe", "probe.py")]), \
             patch.object(run_all_tests.subprocess, "run", return_value=result), \
             redirect_stdout(io.StringIO()):
            self.assertTrue(run_all_tests.run_suite(require_all=True))


if __name__ == "__main__":
    unittest.main()
