"""Verify privacy markers without reading or altering the real clipboard."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.text_injector import TextInjector


class ClipboardExclusionTests(unittest.TestCase):
    def apply_markers(self, clipboard):
        with patch.dict(sys.modules, {"win32clipboard": clipboard}), \
             patch("engine.text_injector.HAS_WIN32", True), \
             patch("engine.text_injector.sys.platform", "win32"), \
             patch("engine.text_injector.time.sleep"):
            return TextInjector._exclude_clipboard_from_history_and_cloud()

    def test_documented_names_and_serialized_dword_values(self):
        clipboard = MagicMock()
        clipboard.RegisterClipboardFormat.side_effect = [101, 102, 103]
        self.assertTrue(self.apply_markers(clipboard))
        self.assertEqual([c.args[0] for c in clipboard.RegisterClipboardFormat.call_args_list], [
            "ExcludeClipboardContentFromMonitorProcessing",
            "CanIncludeInClipboardHistory", "CanUploadToCloudClipboard",
        ])
        self.assertEqual([c.args for c in clipboard.SetClipboardData.call_args_list], [
            (101, bytes([1, 0, 0, 0])), (102, bytes(4)), (103, bytes(4)),
        ])
        clipboard.CloseClipboard.assert_called_once()
        clipboard.EmptyClipboard.assert_not_called()

    def test_write_failure_closes_clipboard_and_reports_failure(self):
        clipboard = MagicMock()
        clipboard.SetClipboardData.side_effect = OSError("unavailable")
        self.assertFalse(self.apply_markers(clipboard))
        clipboard.CloseClipboard.assert_called_once()

    def test_lock_contention_has_bounded_retries(self):
        clipboard = MagicMock()
        clipboard.OpenClipboard.side_effect = OSError("busy")
        self.assertFalse(self.apply_markers(clipboard))
        self.assertEqual(clipboard.OpenClipboard.call_count, 3)
        clipboard.CloseClipboard.assert_not_called()
        clipboard.SetClipboardData.assert_not_called()


if __name__ == "__main__":
    unittest.main()
