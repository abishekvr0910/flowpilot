"""
FlowPilot Forensic Network Egress Verification Test
Monitors process socket activity during audio recording, STT inference,
and ContextProcessor polishing to mathematically prove zero outbound egress.
Includes socket connect monkey-patching and configuration adversarial testing.
"""

import sys
import os
import time
import socket
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psutil
import numpy as np
import io
import soundfile as sf
from engine.config import load_config
from engine.stt_engine import STTEngine
from engine.writing_intelligence import WritingIntelligence
from engine.context_processor import ContextProcessor
from engine.audio_recorder import AudioRecorder

# Track all connection attempts at socket level
outbound_connection_attempts = []
_orig_socket_connect = socket.socket.connect

def guarded_socket_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    # Allow local loopback addresses only
    if host not in ("127.0.0.1", "::1", "localhost", "0.0.0.0"):
        outbound_connection_attempts.append(address)
        raise ConnectionRefusedError(f"[FORENSIC AUDIT] Zero-Egress Guard blocked outbound connection to: {address}")
    return _orig_socket_connect(self, address)

socket.socket.connect = guarded_socket_connect

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
    # Even if API keys are configured, zero egress must be mathematically invariant
    config["groq_api_key"] = "gsk_forensic_audit_dummy_key_123"
    config["openai_api_key"] = "sk-forensic_audit_dummy_key_456"

    stt = STTEngine(config)
    cp = ContextProcessor(config)
    recorder = AudioRecorder(sample_rate=16000)

    # 3. Audio Capture (with graceful fallback for headless CI)
    print("\nStarting audio capture (1.0s)...")
    audio_bytes = None
    try:
        recorder.start_recording()
        time.sleep(1.0)
        audio_bytes = recorder.stop_recording()
    except Exception as e:
        print(f"Note: Audio device capture deferred ({e}). Generating test PCM fixture...")
        fs = 16000
        t = np.linspace(0, 1.0, fs, dtype=np.float32)
        tone = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, tone, fs, format="WAV", subtype="PCM_16")
        audio_bytes = buf.getvalue()
    finally:
        recorder.close()

    assert audio_bytes is not None and len(audio_bytes) > 0

    # Check sockets during audio processing
    mid_conns = get_process_connections(current_pid)
    print(f"Remote connections after audio capture: {mid_conns}")
    assert len(mid_conns) == 0, f"Outbound socket opened during capture: {mid_conns}"
    assert len(outbound_connection_attempts) == 0, f"Outbound socket connection attempted: {outbound_connection_attempts}"

    # 4. Transcribe locally via faster-whisper (local_files_only=True)
    print("\nExecuting local Whisper inference...")
    res = stt.transcribe(audio_bytes)
    raw_text = res.get("text", "")
    print(f"Transcription: '{raw_text}'")

    # Check sockets after Whisper inference
    post_stt_conns = get_process_connections(current_pid)
    print(f"Remote connections post-STT: {post_stt_conns}")
    assert len(post_stt_conns) == 0, f"Outbound socket opened during STT: {post_stt_conns}"
    assert len(outbound_connection_attempts) == 0, f"Outbound connection attempted: {outbound_connection_attempts}"

    # 5. Verify that cloud STT mode is strictly blocked and rejected
    print("\nVerifying cloud STT mode hard-disablement...")
    stt_cloud = STTEngine({"engine_mode": "cloud", "groq_api_key": "dummy"})
    try:
        stt_cloud.transcribe(audio_bytes)
        assert False, "Cloud STT transcription should have raised RuntimeError!"
    except RuntimeError as re:
        print(f"Cloud STT attempt successfully blocked: {re}")
    assert len(outbound_connection_attempts) == 0, "Cloud STT attempted outbound connection!"

    # 6. Execute ContextProcessor with API keys configured (must remain 100% local)
    print("\nExecuting ContextProcessor polishing with API keys configured...")
    test_phrase = "Schedule meeting for Tuesday -- actually Wednesday with $10,000 budget and do not cancel."
    polished = cp.process(test_phrase)
    print(f"Polished: '{polished}'")

    # Verify FactGuard invariant preservation
    assert "$10,000" in polished, "FactGuard failed: number was mutated"
    assert "not cancel" in polished or "do not cancel" in polished, "FactGuard failed: negation lost"
    assert "Wednesday" in polished, "Self-correction failed"

    # Check sockets post ContextProcessor
    final_conns = get_process_connections(current_pid)
    print(f"Final remote connections: {final_conns}")
    assert len(final_conns) == 0, f"Outbound socket opened during polishing: {final_conns}"
    assert len(outbound_connection_attempts) == 0, f"Outbound connection attempted: {outbound_connection_attempts}"

    print("\n" + "=" * 70)
    print("VERDICT: ZERO NETWORK EGRESS CONFIRMED (0 Outbound Sockets Detected)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_zero_network_egress()
    sys.exit(0 if success else 1)
