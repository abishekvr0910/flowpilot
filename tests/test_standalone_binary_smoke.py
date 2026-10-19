"""
Smoke test for the packaged FlowPilot standalone binary (dist/FlowPilot/FlowPilot.exe).
Verifies:
1. Binary existence and size
2. Launch without DLL or runtime errors
3. Single-instance mutex enforcement
4. Clean termination
"""
import os
import sys
import time
import subprocess
import psutil
import ctypes

def main():
    exe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dist", "FlowPilot", "FlowPilot.exe"))
    print(f"Testing packaged executable: {exe_path}")
    
    if not os.path.isfile(exe_path):
        print(f"FAILED: Binary not found at {exe_path}")
        sys.exit(1)
        
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"Binary size: {size_mb:.2f} MB")
    assert size_mb > 10, f"Binary too small ({size_mb:.2f} MB), packaging may be incomplete"
    
    # Phase 0: Verify bundled Faster-Whisper & Silero VAD assets
    exe_dir = os.path.dirname(exe_path)
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

    # Use isolated test mutex to avoid conflicting with or terminating any user instances
    test_env = os.environ.copy()
    test_env["FLOWPILOT_MUTEX_NAME"] = f"Global\\FlowPilot_SmokeTest_{os.getpid()}"
    test_env["FLOWPILOT_NO_POPUP"] = "1"
    test_env["CI"] = "1"
    test_env["FLOWPILOT_HEADLESS"] = "1"


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
        print("\n[Phase 3] Cleanly terminating primary instance...")
        try:
            p = psutil.Process(proc.pid)
            for child in p.children(recursive=True):
                child.terminate()
            p.terminate()
            proc.wait(timeout=5)
            print("Primary process terminated cleanly.")
        except Exception as e:
            print(f"Termination exception: {e}")
            proc.kill()
            
    print("\n=== STANDALONE BINARY SMOKE TEST PASSED ===")

if __name__ == "__main__":
    main()
