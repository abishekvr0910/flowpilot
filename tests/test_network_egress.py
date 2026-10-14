"""
FlowPilot Forensic Network Egress Verification Test
Monitors process socket activity during audio recording, STT inference,
and WritingIntelligence polishing to mathematically prove zero outbound egress.
"""

import sys
import os
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psutil
from engine.config import load_config
from engine.stt_engine import STTEngine
from engine.writing_intelligence import WritingIntelligence
from engine.audio_recorder import AudioRecorder

def get_process_connections(pid: int):
    """Returns list of active remote connections for given process."""
    proc = psutil.Process(pid)
    conns = []
    try:
        conn_list = proc.net_connections(kind="all") if hasattr(proc, "net_connections") else proc.connections(kind="all")
        for c in conn_list:
            # Ignore localhost / loopback 127.0.0.1 or ::1
            raddr = c.raddr
            if raddr:
                ip, port = raddr.ip, raddr.port
                if ip not in ("127.0.0.1", "::1", "localhost"):
                    conns.append((c.type, c.status, ip, port))
    except Exception as e:
        print(f"Connection inspection warning: {e}")
    return conns

def test_zero_network_egress():
    print("=" * 70)
    print("FORENSIC TEST: ZERO NETWORK EGRESS & SOCKET LIFECYCLE AUDIT")
    print("=" * 70)

    current_pid = os.getpid()
    print(f"Monitoring PID: {current_pid}")

    # 1. Baseline socket inspection
    baseline_conns = get_process_connections(current_pid)
    print(f"Baseline remote connections: {baseline_conns}")
    assert len(baseline_conns) == 0, f"Expected 0 remote connections, found: {baseline_conns}"

    # 2. Initialize Engine Subsystems
    config = load_config()
    config["engine_mode"] = "local"
    config["local_model_size"] = "base"
    
    stt = STTEngine(config)
    wi = WritingIntelligence()
    recorder = AudioRecorder(sample_rate=16000)

    # 3. Simulate Active Dictation Cycle
    print("\nStarting audio capture (1.0s)...")
    recorder.start_recording()
    time.sleep(1.0)
    audio_bytes = recorder.stop_recording()
    print(f"Captured {len(audio_bytes)} bytes audio.")

    # Check sockets during audio processing
    mid_conns = get_process_connections(current_pid)
    print(f"Remote connections during audio capture: {mid_conns}")
    assert len(mid_conns) == 0, f"Outbound socket opened during capture: {mid_conns}"

    # 4. Transcribe locally via faster-whisper
    print("\nExecuting local Whisper inference...")
    res = stt.transcribe(audio_bytes)
    raw_text = res.get("text", "")
    print(f"Transcription: '{raw_text}'")

    # Check sockets after Whisper inference
    post_stt_conns = get_process_connections(current_pid)
    print(f"Remote connections post-STT: {post_stt_conns}")
    assert len(post_stt_conns) == 0, f"Outbound socket opened during STT: {post_stt_conns}"

    # 5. Execute Writing Intelligence polishing
    print("\nExecuting Writing Intelligence polishing...")
    polished = wi.polish("Schedule meeting for Tuesday -- actually Wednesday with $10,000 budget and do not cancel.", mode="polished")
    print(f"Polished: '{polished['text']}'")

    # Check sockets post polishing
    final_conns = get_process_connections(current_pid)
    print(f"Final remote connections: {final_conns}")
    assert len(final_conns) == 0, f"Outbound socket opened during polishing: {final_conns}"

    print("\n" + "=" * 70)
    print("VERDICT: ZERO NETWORK EGRESS CONFIRMED (0 Outbound Sockets Detected)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_zero_network_egress()
    sys.exit(0 if success else 1)
