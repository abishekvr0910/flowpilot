# Feature: Multilingual Model Provisioning & Integrity Tests
"""
Unit tests for engine/model_downloader.py:
Validates model specs, checksum computation, download worker lifecycle,
atomic temp-to-final replacement, and integrity verification.
"""

import os
import sys
import tempfile
import unittest
import hashlib
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.model_downloader import (
    MODEL_REGISTRY,
    ModelFileSpec,
    get_model_specs,
    get_total_model_bytes,
    compute_file_sha256,
    get_target_model_dir,
    verify_model_integrity,
    download_model,
    ModelDownloadWorker,
)


class TestModelDownloader(unittest.TestCase):
    def test_model_specs_registry(self):
        small_specs = get_model_specs("small")
        self.assertEqual(len(small_specs), 4)
        names = {s.name for s in small_specs}
        self.assertEqual(names, {"config.json", "model.bin", "tokenizer.json", "vocabulary.txt"})

        base_specs = get_model_specs("base")
        self.assertEqual(len(base_specs), 4)

        with self.assertRaises(ValueError):
            get_model_specs("nonexistent_model")

        total_bytes = get_total_model_bytes("small")
        self.assertGreater(total_bytes, 400 * 1024 * 1024)

    def test_verify_real_local_small_model(self):
        real_small = Path(__file__).resolve().parent.parent / "models" / "faster-whisper-small"
        if (real_small / "model.bin").is_file():
            is_valid, msg, per_file = verify_model_integrity(real_small, size="small", check_hashes=True)
            self.assertTrue(is_valid, f"Verification failed: {msg}")
            self.assertTrue(all(per_file.values()))

    def test_verify_missing_and_corrupted_model(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            p = Path(tmp_dir)
            is_valid, msg, per_file = verify_model_integrity(p, size="small", check_hashes=False)
            self.assertFalse(is_valid)
            self.assertIn("Missing", msg)

            # Create dummy files with wrong sizes
            (p / "config.json").write_bytes(b"{}")
            (p / "model.bin").write_bytes(b"wrong_size")
            (p / "tokenizer.json").write_bytes(b"{}")
            (p / "vocabulary.txt").write_bytes(b"word")

            is_valid, msg, per_file = verify_model_integrity(p, size="small", check_hashes=False)
            self.assertFalse(is_valid)
            self.assertIn("size mismatch", msg)

    def test_target_model_dir_resolution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"FLOWPILOT_MODEL_DIR": tmp_dir}):
                target = get_target_model_dir("small")
                self.assertEqual(target, Path(tmp_dir) / "faster-whisper-small")

    def test_frozen_app_downloads_to_user_profile(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            user_models = Path(tmp_dir) / ".flowpilot" / "models"
            with patch.dict(os.environ, {"FLOWPILOT_MODEL_DIR": ""}), \
                 patch.object(sys, "frozen", True, create=True), \
                 patch("engine.model_downloader.os.path.expanduser", return_value=str(user_models)):
                self.assertEqual(get_target_model_dir("small"), user_models / "faster-whisper-small")

    def test_failed_atomic_replace_preserves_existing_model_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir)
            prior = dest / "config.json"
            prior.write_bytes(b"wrong!!")
            payload = b"correct"
            spec = ModelFileSpec("config.json", "https://example.invalid/config.json", len(payload), hashlib.sha256(payload).hexdigest())
            response = MagicMock()
            response.headers = {"content-length": str(len(payload))}
            response.read.side_effect = [payload, b""]
            response.__enter__.return_value = response
            with patch("engine.model_downloader.get_model_specs", return_value=[spec]), \
                 patch("urllib.request.urlopen", return_value=response), \
                 patch.object(Path, "replace", side_effect=OSError("file locked")):
                success, message, _ = download_model(size="small", target_dir=dest)
            self.assertFalse(success)
            self.assertIn("file locked", message)
            self.assertEqual(prior.read_bytes(), b"wrong!!")
            self.assertEqual(list(dest.glob("*.tmp")), [])

    def test_mock_download_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir)
            specs = get_model_specs("small")

            dummy_specs = [
                ModelFileSpec(
                    name=s.name, url=s.url, size=100,
                    sha256=hashlib.sha256(b"x" * 100).hexdigest()
                )
                for s in specs
            ]

            def fake_urlopen(req, timeout=60):
                url = req.full_url
                matching = next(s for s in dummy_specs if s.url == url)
                content = b"x" * matching.size
                mock_resp = MagicMock()
                mock_resp.headers = {"content-length": str(matching.size)}
                half = matching.size // 2
                mock_resp.read.side_effect = [content[:half], content[half:], b""]
                mock_resp.__enter__.return_value = mock_resp
                return mock_resp

            with patch("engine.model_downloader.get_model_specs", return_value=dummy_specs), \
                 patch("urllib.request.urlopen", side_effect=fake_urlopen):
                success, msg, out_dir = download_model(size="small", target_dir=dest)
                self.assertTrue(success, f"Download failed: {msg}")
                for s in dummy_specs:
                    self.assertTrue((dest / s.name).is_file())
                    self.assertFalse((dest / f"{s.name}.tmp").exists())

    def test_mock_download_cancelled(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dest = Path(tmp_dir)
            cancel_called = False

            def cancel_checker():
                nonlocal cancel_called
                cancel_called = True
                return True

            success, msg, out_dir = download_model(size="small", target_dir=dest, cancel_check=cancel_checker)
            self.assertFalse(success)
            self.assertIn("cancelled", msg.lower())

    def test_qt_download_worker_is_independent_of_closing_dialog(self):
        if ModelDownloadWorker is None:
            self.skipTest("PySide6 is not installed")
        from PySide6.QtCore import QCoreApplication, QObject
        app = QCoreApplication.instance() or QCoreApplication([])
        dialog = QObject()
        worker = ModelDownloadWorker(size="small", parent=dialog)
        self.assertIsNone(worker.parent())
        events = []
        worker.download_finished.connect(lambda success, message, dest: events.append((success, message, dest)))
        with patch("engine.model_downloader.download_model", return_value=(False, "cancelled", Path("unused"))):
            worker.start()
            self.assertTrue(worker.wait(2000))
            app.processEvents()
        self.assertEqual(events, [(False, "cancelled", "unused")])
        del dialog

    def test_qt_download_worker_reports_setup_error(self):
        if ModelDownloadWorker is None:
            self.skipTest("PySide6 is not installed")
        from PySide6.QtCore import QCoreApplication
        app = QCoreApplication.instance() or QCoreApplication([])
        worker = ModelDownloadWorker(size="small")
        events = []
        worker.download_finished.connect(lambda success, message, dest: events.append((success, message)))
        with patch("engine.model_downloader.download_model", side_effect=OSError("disk full")):
            worker.start()
            self.assertTrue(worker.wait(2000))
            app.processEvents()
        self.assertEqual(events, [(False, "Model download failed: disk full")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
