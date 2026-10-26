# Feature: Multilingual Model Provisioning & Integrity Verifier
"""
FlowPilot Model Provisioning & Integrity Service.
Manages user-initiated downloading, SHA-256 integrity verification, and directory
provisioning for offline speech recognition models (e.g. faster-whisper-small for Indic languages).
Ensures dictation runtime remains strictly offline (zero cloud egress) by separating
setup-time asset acquisition from real-time speech processing.
"""

import os
import sys
import time
import hashlib
import logging
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Union

logger = logging.getLogger("FlowPilot.ModelDownloader")


@dataclass
class ModelFileSpec:
    name: str
    url: str
    size: int
    sha256: str


MODEL_REGISTRY: Dict[str, List[ModelFileSpec]] = {
    "small": [
        ModelFileSpec(
            name="config.json",
            url="https://huggingface.co/Systran/faster-whisper-small/resolve/main/config.json",
            size=2370,
            sha256="b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828",
        ),
        ModelFileSpec(
            name="model.bin",
            url="https://huggingface.co/Systran/faster-whisper-small/resolve/main/model.bin",
            size=483546902,
            sha256="3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671",
        ),
        ModelFileSpec(
            name="tokenizer.json",
            url="https://huggingface.co/Systran/faster-whisper-small/resolve/main/tokenizer.json",
            size=2203239,
            sha256="fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
        ),
        ModelFileSpec(
            name="vocabulary.txt",
            url="https://huggingface.co/Systran/faster-whisper-small/resolve/main/vocabulary.txt",
            size=459861,
            sha256="34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
        ),
    ],
    "base": [
        ModelFileSpec(
            name="config.json",
            url="https://huggingface.co/Systran/faster-whisper-base/resolve/main/config.json",
            size=2309,
            sha256="56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a",
        ),
        ModelFileSpec(
            name="model.bin",
            url="https://huggingface.co/Systran/faster-whisper-base/resolve/main/model.bin",
            size=145217532,
            sha256="d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9",
        ),
        ModelFileSpec(
            name="tokenizer.json",
            url="https://huggingface.co/Systran/faster-whisper-base/resolve/main/tokenizer.json",
            size=2203239,
            sha256="fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab",
        ),
        ModelFileSpec(
            name="vocabulary.txt",
            url="https://huggingface.co/Systran/faster-whisper-base/resolve/main/vocabulary.txt",
            size=459861,
            sha256="34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913",
        ),
    ],
}


def get_model_specs(size: str = "small") -> List[ModelFileSpec]:
    """Returns the expected file specifications for a given model size."""
    size_clean = str(size).strip().lower()
    if size_clean not in MODEL_REGISTRY:
        raise ValueError(f"Unknown or unsupported model size: {size_clean}. Supported: {list(MODEL_REGISTRY.keys())}")
    return MODEL_REGISTRY[size_clean]


def get_total_model_bytes(size: str = "small") -> int:
    """Returns total download size in bytes for the specified model."""
    specs = get_model_specs(size)
    return sum(spec.size for spec in specs)


def compute_file_sha256(path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Computes SHA-256 hash of a local file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest().lower()


def get_target_model_dir(size: str = "small") -> Path:
    """
    Determines the appropriate writable target directory for model provisioning.
    Priority:
    1. FLOWPILOT_MODEL_DIR environment variable
    2. Project root models/ directory (if exists and writable, development mode)
    3. User profile ~/.flowpilot/models/ directory (always user-writable)
    """
    size_clean = str(size).strip().lower()
    get_model_specs(size_clean)

    env_dir = os.environ.get("FLOWPILOT_MODEL_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.name.lower() in (f"faster-whisper-{size_clean}", size_clean):
            return p
        return p / f"faster-whisper-{size_clean}"

    proj_root = Path(__file__).resolve().parent.parent
    dev_models = proj_root / "models"
    if not (getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")) and dev_models.is_dir() and os.access(dev_models, os.W_OK):
        target = dev_models / f"faster-whisper-{size_clean}"
        return target

    user_models = Path(os.path.expanduser("~/.flowpilot/models"))
    user_models.mkdir(parents=True, exist_ok=True)
    return user_models / f"faster-whisper-{size_clean}"


def verify_model_integrity(
    model_dir: Union[str, Path], size: str = "small", check_hashes: bool = True
) -> Tuple[bool, str, Dict[str, bool]]:
    """
    Verifies that all required model files are present, match expected sizes,
    and have valid SHA-256 checksums.

    Returns:
        (is_valid, summary_message, per_file_status)
    """
    target = Path(model_dir)
    if not target.is_dir():
        return False, f"Directory does not exist: {target}", {}

    specs = get_model_specs(size)
    per_file: Dict[str, bool] = {}
    missing_or_corrupt: List[str] = []

    for spec in specs:
        file_path = target / spec.name
        if not file_path.is_file():
            per_file[spec.name] = False
            missing_or_corrupt.append(f"Missing {spec.name}")
            continue

        actual_size = file_path.stat().st_size
        if actual_size != spec.size:
            per_file[spec.name] = False
            missing_or_corrupt.append(f"{spec.name} size mismatch (expected {spec.size}, got {actual_size})")
            continue

        if check_hashes:
            actual_hash = compute_file_sha256(file_path)
            if actual_hash != spec.sha256.lower():
                per_file[spec.name] = False
                missing_or_corrupt.append(f"{spec.name} SHA-256 hash mismatch")
                continue

        per_file[spec.name] = True

    if missing_or_corrupt:
        msg = f"Integrity check failed ({len(missing_or_corrupt)} issues): " + "; ".join(missing_or_corrupt)
        return False, msg, per_file

    return True, f"All {len(specs)} model files verified with valid SHA-256.", per_file


def download_model(
    size: str = "small",
    target_dir: Optional[Union[str, Path]] = None,
    progress_callback: Optional[Callable[[int, int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    timeout: int = 60,
) -> Tuple[bool, str, Path]:
    """
    Downloads model files directly to target_dir with streaming progress and atomic verification.
    Dictation remains strictly offline; this function is exclusively invoked by explicit
    user onboarding actions.

    Arguments:
        size: "small" or "base"
        target_dir: Path to directory (resolved automatically if None)
        progress_callback: callback(percent, bytes_downloaded, total_bytes, current_file)
        cancel_check: callable returning True if download was cancelled by user
        timeout: socket timeout in seconds

    Returns:
        (success, status_message, target_directory)
    """
    specs = get_model_specs(size)
    dest = Path(target_dir) if target_dir else get_target_model_dir(size)
    dest.mkdir(parents=True, exist_ok=True)
    total_bytes = sum(s.size for s in specs)
    bytes_completed_prior = 0

    # First verify if already complete
    is_valid, msg, _ = verify_model_integrity(dest, size=size, check_hashes=True)
    if is_valid:
        if progress_callback:
            progress_callback(100, total_bytes, total_bytes, "Complete")
        return True, "Model is already present and fully verified.", dest

    logger.info("Starting model download for '%s' into '%s' (total %d bytes)", size, dest, total_bytes)

    for spec in specs:
        if cancel_check and cancel_check():
            return False, "Download cancelled by user.", dest

        file_dest = dest / spec.name
        temp_dest = None

        # Check if this individual file is already complete and verified
        if file_dest.is_file() and file_dest.stat().st_size == spec.size:
            if compute_file_sha256(file_dest) == spec.sha256.lower():
                bytes_completed_prior += spec.size
                if progress_callback:
                    pct = int((bytes_completed_prior / total_bytes) * 100)
                    progress_callback(pct, bytes_completed_prior, total_bytes, spec.name)
                continue

        # Download to temporary file
        logger.info("Downloading %s (%d bytes) from %s", spec.name, spec.size, spec.url)
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{spec.name}.", suffix=".tmp", dir=dest, delete=False
            ) as temp_file:
                temp_dest = Path(temp_file.name)
            req = urllib.request.Request(
                spec.url,
                headers={"User-Agent": "FlowPilot-Model-Downloader/3.1 (Windows; OfflineDictation)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                file_size = int(response.headers.get("content-length", spec.size))
                downloaded_file_bytes = 0
                hasher = hashlib.sha256()

                with open(temp_dest, "wb") as out_f:
                    while True:
                        if cancel_check and cancel_check():
                            out_f.close()
                            if temp_dest.exists():
                                temp_dest.unlink(missing_ok=True)
                            return False, "Download cancelled by user.", dest

                        chunk = response.read(65536)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        hasher.update(chunk)
                        downloaded_file_bytes += len(chunk)

                        if progress_callback:
                            current_total = bytes_completed_prior + downloaded_file_bytes
                            pct = min(99, int((current_total / total_bytes) * 100))
                            progress_callback(pct, current_total, total_bytes, spec.name)

            # Verify downloaded temp file
            actual_hash = hasher.hexdigest().lower()
            if actual_hash != spec.sha256.lower():
                temp_dest.unlink(missing_ok=True)
                err_msg = f"Checksum verification failed for {spec.name} (expected {spec.sha256}, got {actual_hash})"
                logger.error(err_msg)
                return False, err_msg, dest

            # Atomic replace
            temp_dest.replace(file_dest)
            bytes_completed_prior += spec.size

        except Exception as e:
            if temp_dest is not None and temp_dest.exists():
                temp_dest.unlink(missing_ok=True)
            err_msg = f"Failed to download {spec.name}: {e}"
            logger.error(err_msg)
            return False, err_msg, dest

    # Final holistic verification
    is_valid, msg, _ = verify_model_integrity(dest, size=size, check_hashes=True)
    if is_valid:
        if progress_callback:
            progress_callback(100, total_bytes, total_bytes, "Complete")
        logger.info("Model '%s' successfully provisioned and verified at %s", size, dest)
        return True, "Model successfully downloaded and verified.", dest

    return False, f"Post-download verification failed: {msg}", dest


# Optional Qt Worker for background execution in GUI
try:
    from PySide6.QtCore import QCoreApplication, QThread, Signal

    _ACTIVE_DOWNLOAD_WORKERS = set()
    _SHUTDOWN_HOOK_INSTALLED = False

    def _stop_active_downloads():
        workers = tuple(_ACTIVE_DOWNLOAD_WORKERS)
        for worker in workers:
            worker.cancel()
        for worker in workers:
            worker.wait(11000)

    class ModelDownloadWorker(QThread):
        """Asynchronous background worker for downloading Whisper models in PySide6."""

        progress = Signal(int, int, int, str)  # percent, downloaded_bytes, total_bytes, filename
        download_finished = Signal(bool, str, str)  # success, message, target_dir

        def __init__(self, size: str = "small", target_dir: Optional[Union[str, Path]] = None, parent=None):
            # The dialog can close while an HTTPS read is in progress.
            super().__init__(None)
            self.size = size
            self.target_dir = target_dir
            self._cancelled = False
            self.finished.connect(lambda: _ACTIVE_DOWNLOAD_WORKERS.discard(self))

        def start(self, priority=QThread.InheritPriority):
            global _SHUTDOWN_HOOK_INSTALLED
            _ACTIVE_DOWNLOAD_WORKERS.add(self)
            app = QCoreApplication.instance()
            if app is not None and not _SHUTDOWN_HOOK_INSTALLED:
                app.aboutToQuit.connect(_stop_active_downloads)
                _SHUTDOWN_HOOK_INSTALLED = True
            try:
                super().start(priority)
            except Exception:
                _ACTIVE_DOWNLOAD_WORKERS.discard(self)
                raise

        def cancel(self):
            self._cancelled = True

        def run(self):
            def cancel_check():
                return self._cancelled

            def on_progress(pct, done, total, fname):
                self.progress.emit(pct, done, total, fname)

            try:
                success, message, dest = download_model(
                    size=self.size,
                    target_dir=self.target_dir,
                    progress_callback=on_progress,
                    cancel_check=cancel_check,
                    timeout=10,
                )
            except Exception as exc:
                logger.exception("Model download worker failed")
                success, message, dest = False, f"Model download failed: {exc}", self.target_dir or ""
            self.download_finished.emit(success, message, str(dest))

except ImportError:
    ModelDownloadWorker = None
