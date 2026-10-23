"""Runtime evaluation metadata and processing summaries, without target input."""

import math
import os
import platform
import subprocess
from importlib.metadata import PackageNotFoundError, version

import psutil


def percentile(values, percent):
    """Linearly interpolate an empirical percentile; no samples means unknown."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between zero and 100")
    values = sorted(float(value) for value in values)
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("timings must be finite and nonnegative")
    if not values:
        return None
    position = (len(values) - 1) * percent / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 4)


def summarize_processing_trials(trials):
    """Keep cold/warm processing separate; this cannot establish visible delivery."""
    summary = {}
    for phase in ("cold", "warm"):
        rows = [row for row in trials if row.get("status") == "evaluated" and row.get("phase") == phase]
        durations = [row["decode_sec"] + row["format_sec"] for row in rows]
        summary[phase] = {
            "count": len(rows),
            "processing_p50_sec": percentile(durations, 50),
            "processing_p95_sec": percentile(durations, 95),
        }
    summary["stop_to_visible_text"] = {"status": "not_measured", "p50_sec": None, "p95_sec": None}
    return summary


def collect_runtime_environment(project_root):
    """Capture reproducibility details without a hostname, user name, or paths."""
    cpu_model = platform.processor()
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                cpu_model = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        except OSError:
            pass
    packages = {}
    for package in ("faster-whisper", "ctranslate2", "onnxruntime"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = None
    identity = {"commit": None, "worktree_dirty": None}
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=project_root, capture_output=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=project_root, capture_output=True,
            encoding="utf-8", errors="replace", timeout=5,
        )
        if commit.returncode == 0:
            identity["commit"] = commit.stdout.strip()
        if status.returncode == 0:
            identity["worktree_dirty"] = bool(status.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {
        "cpu_model": cpu_model, "logical_processors": psutil.cpu_count(),
        "physical_cores": psutil.cpu_count(logical=False),
        "ram_total_mb": round(psutil.virtual_memory().total / 1048576, 2),
        "os": platform.system(), "os_release": platform.release(), "os_version": platform.version(),
        "python": platform.python_version(), "packages": packages, "source": identity,
        "build_kind": "source_evaluation",
    }
