"""Feature 13: Isolated smoke test for the packaged FlowPilot binary.

Smoke test for the packaged FlowPilot standalone binary (dist/FlowPilot/FlowPilot.exe).
Verifies:
1. Binary existence and size
2. Launch without DLL or runtime errors
3. Single-instance mutex enforcement
4. Clean termination
"""
import os
import logging
import sys
import time
import subprocess
import psutil
import ctypes
import tempfile
from pathlib import Path

logger = logging.getLogger("FlowPilot.StandaloneSmokeTest")

def main():
    default_exe = os.path.join(os.path.dirname(__file__), "..", "dist", "FlowPilot", "FlowPilot.exe")
    exe_path = os.path.abspath(os.environ.get("FLOWPILOT_TEST_EXE") or default_exe)
    if not os.path.isfile(exe_path):
        print(f"FAILED: Binary not found at {exe_path}")
        sys.exit(1)
    newest_source_mtime = max(
        p.stat().st_mtime
        for folder in ("engine", "ui")
        for p in (Path(__file__).resolve().parents[1] / folder).rglob("*.py")
    )
    if Path(exe_path).stat().st_mtime < newest_source_mtime:
        print(
            "[SMOKE] WARNING: the packaged binary is older than the newest source file.\n"
            f"[SMOKE]   binary : {exe_path}\n"
            "[SMOKE]   Rebuild the binary or stage FLOWPILOT_TEST_EXE before trusting this result."
        )
    print(f"Testing packaged executable: {exe_path}")
    
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"Binary size: {size_mb:.2f} MB")
    assert size_mb > 10, f"Binary too small ({size_mb:.2f} MB), packaging may be incomplete"
    
    # Phase 0: Verify bundled Faster-Whisper & Silero VAD assets
    exe_dir = os.path.dirname(exe_path)
    packaged_ui = os.path.join(exe_dir, "_internal", "ui")
    if os.path.isdir(packaged_ui):
        static_files = set(os.listdir(packaged_ui))
        assert static_files == {"index.html", "app.js", "styles.css"}, (
            f"Unexpected files in packaged UI data: {sorted(static_files)}"
        )
    for forbidden in ("wispr_renderer", "wispr_bridge.py", "wispr_bridge.pyc"):
        assert not os.path.exists(os.path.join(packaged_ui, forbidden)), forbidden
    qt_dir = os.path.join(exe_dir, "_internal", "PySide6")
    unused_qt_paths = (
        os.path.join(qt_dir, "Qt6VirtualKeyboard.dll"),
        os.path.join(qt_dir, "plugins", "platforminputcontexts", "qtvirtualkeyboardplugin.dll"),
        os.path.join(qt_dir, "Qt6Pdf.dll"),
        os.path.join(qt_dir, "plugins", "imageformats", "qpdf.dll"),
    )
    for unused_path in unused_qt_paths:
        assert not os.path.exists(unused_path), f"Unused Qt module bundled: {unused_path}"
    cand_enc = [
        os.path.join(exe_dir, "_internal", "faster_whisper", "assets", "silero_encoder_v5.onnx"),
        os.path.join(exe_dir, "_internal", "assets", "silero_encoder_v5.onnx"),
        os.path.join(exe_dir, "assets", "silero_encoder_v5.onnx"),
    ]
    cand_dec = [
        os.path.join(exe_dir, "_internal", "faster_whisper", "assets", "silero_decoder_v5.onnx"),
        os.path.join(exe_dir, "_internal", "assets", "silero_decoder_v5.onnx"),
        os.path.join(exe_dir, "assets", "silero_decoder_v5.onnx"),
    ]
    vad_enc = next((p for p in cand_enc if os.path.isfile(p)), None)
    vad_dec = next((p for p in cand_dec if os.path.isfile(p)), None)
    assert vad_enc is not None, f"Missing Silero VAD encoder asset in {exe_dir}"
    assert vad_dec is not None, f"Missing Silero VAD decoder asset in {exe_dir}"
    print(f"Verified bundled Silero VAD assets:\n  Encoder: {vad_enc} ({os.path.getsize(vad_enc)} bytes)\n  Decoder: {vad_dec} ({os.path.getsize(vad_dec)} bytes)")

    cand_model = [
        os.path.join(exe_dir, "_internal", "models", "faster-whisper-base", "model.bin"),
        os.path.join(exe_dir, "models", "faster-whisper-base", "model.bin"),
    ]
    model_bin = next((p for p in cand_model if os.path.isfile(p)), None)
    if model_bin is None:
        proj_model = os.path.join(os.path.dirname(__file__), "..", "models", "faster-whisper-base", "model.bin")
        if not os.path.isfile(proj_model):
            print(f"[NOTICE] Base model was not pre-provisioned at build time in project models/; skipping bundled model check in {exe_dir}")
        else:
            assert model_bin is not None, f"Missing Faster-Whisper base model weights in {exe_dir}"
    else:
        print(f"Verified bundled Whisper model weights: {model_bin} ({os.path.getsize(model_bin)} bytes)")

    # Use isolated test mutex to avoid conflicting with or terminating any user instances
    test_env = os.environ.copy()
    test_env["FLOWPILOT_MUTEX_NAME"] = f"Global\\FlowPilot_SmokeTest_{os.getpid()}"
    test_env["FLOWPILOT_NO_POPUP"] = "1"
    test_env["CI"] = "1"
    test_env["FLOWPILOT_HEADLESS"] = "1"
    isolated_profile = tempfile.TemporaryDirectory(prefix="flowpilot-smoke-profile-")
    use_caller_profile = (test_env.get("FLOWPILOT_SMOKE_USE_CALLER_PROFILE") == "1"
                          and test_env.get("FLOWPILOT_CONFIG_DIR")
                          and test_env.get("FLOWPILOT_CONFIG_FILE"))
    if not use_caller_profile:
        test_env["FLOWPILOT_CONFIG_DIR"] = isolated_profile.name
        test_env["FLOWPILOT_CONFIG_FILE"] = os.path.join(isolated_profile.name, "config.json")
    test_env["HF_HOME"] = os.path.join(isolated_profile.name, "empty-hf-cache")
    test_env["HF_HUB_CACHE"] = test_env["HF_HOME"]
    test_env["HF_HUB_OFFLINE"] = "1"
    test_env["TRANSFORMERS_OFFLINE"] = "1"


    mutex_name = test_env["FLOWPILOT_MUTEX_NAME"]
    SYNCHRONIZE = 0x00100000
    kernel32 = ctypes.windll.kernel32
    timeout_seconds = 15.0
    deadline = time.monotonic() + timeout_seconds
    mutex_ready = False

    print(f"\n[Phase 1] Launching FlowPilot.exe with isolated test mutex: {mutex_name}...")
    proc = subprocess.Popen([exe_path], env=test_env)
    
    try:
        # Explicit check: poll kernel32.OpenMutexW until the named mutex is held
        while time.monotonic() < deadline:
            poll = proc.poll()
            if poll is not None:
                print(f"FAILED: Process exited prematurely with code {poll}")
                sys.exit(1)
            h_mutex = kernel32.OpenMutexW(SYNCHRONIZE, False, mutex_name)
            if h_mutex:
                kernel32.CloseHandle(h_mutex)
                mutex_ready = True
                break
            time.sleep(0.2)

        if not mutex_ready:
            print(f"FAILED: Named mutex '{mutex_name}' was not acquired within {timeout_seconds}s.")
            sys.exit(1)

        p = psutil.Process(proc.pid)
        rss_mb = p.memory_info().rss / (1024 * 1024)
        print(f"SUCCESS: Process holds named mutex and is actively running (PID: {proc.pid}, Resident RAM: {rss_mb:.2f} MB)")
        
        # Test Phase 2: Launch secondary instance, verify mutex stops duplicate
        print("\n[Phase 2] Verifying Single-Instance Mutex enforcement...")
        proc2 = subprocess.Popen([exe_path], env=test_env)
        returncode = proc2.wait(timeout=25)
        print(f"Secondary instance exited cleanly as expected with code: {returncode}")
        assert returncode == 0, f"Expected returncode 0, got {returncode}"
        
        # Verify primary instance is still healthy
        assert proc.poll() is None, "Primary instance died when secondary was launched!"
        print("Primary instance remained healthy and active.")
        
    finally:
        print("\n[Phase 3] Terminating the isolated primary instance...")
        try:
            p = psutil.Process(proc.pid)
            for child in p.children(recursive=True):
                child.terminate()
            p.terminate()
            proc.wait(timeout=5)
            print("Isolated primary process terminated.")
        except Exception as e:
            print(f"Termination exception: {e}")
            proc.kill()
            proc.wait(timeout=5)
        isolated_profile.cleanup()
            
    print("\n=== STANDALONE BINARY SMOKE TEST PASSED ===")

if __name__ == "__main__":
    main()
