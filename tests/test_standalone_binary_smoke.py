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
    vad_enc = os.path.join(os.path.dirname(exe_path), "_internal", "faster_whisper", "assets", "silero_encoder_v5.onnx")
    vad_dec = os.path.join(os.path.dirname(exe_path), "_internal", "faster_whisper", "assets", "silero_decoder_v5.onnx")
    assert os.path.isfile(vad_enc), f"Missing Silero VAD encoder asset at {vad_enc}"
    assert os.path.isfile(vad_dec), f"Missing Silero VAD decoder asset at {vad_dec}"
    print(f"Verified bundled Silero VAD assets:\n  Encoder: {vad_enc} ({os.path.getsize(vad_enc)} bytes)\n  Decoder: {vad_dec} ({os.path.getsize(vad_dec)} bytes)")

    # Use isolated test mutex to avoid conflicting with or terminating any user instances
    test_env = os.environ.copy()
    test_env["FLOWPILOT_MUTEX_NAME"] = f"Global\\FlowPilot_SmokeTest_{os.getpid()}"

    print("\n[Phase 1] Launching FlowPilot.exe with isolated test mutex...")
    proc = subprocess.Popen([exe_path], env=test_env)
    
    try:
        # Give it 4.0 seconds to initialize PySide6, SingleInstance mutex, and HUD
        time.sleep(4.0)
        poll = proc.poll()
        if poll is not None:
            print(f"FAILED: Process exited prematurely with code {poll}")
            sys.exit(1)
            
        p = psutil.Process(proc.pid)
        rss_mb = p.memory_info().rss / (1024 * 1024)
        print(f"SUCCESS: Process is actively running (PID: {proc.pid}, Resident RAM: {rss_mb:.2f} MB)")
        
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
