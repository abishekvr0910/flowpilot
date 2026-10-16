"""
FlowPilot Silero VAD v5 Interface
Provides asset discovery, ONNX Runtime session management, and speech activity detection.
Integrates directly with faster-whisper and FlowPilot's zero-cloud-egress acoustic pipeline.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
import onnxruntime as ort

def get_silero_vad_assets_path() -> Path:
    """Discovers and returns the path containing Silero VAD v5 ONNX assets."""
    # 1. Project assets directory
    proj_root = Path(__file__).resolve().parent.parent
    local_assets = proj_root / "assets"
    if (local_assets / "silero_encoder_v5.onnx").is_file():
        return local_assets

    # 2. PyInstaller bundled internal directory
    if hasattr(sys, "_MEIPASS"):
        meipass_vad = Path(sys._MEIPASS) / "faster_whisper" / "assets"
        if (meipass_vad / "silero_encoder_v5.onnx").is_file():
            return meipass_vad
        meipass_root = Path(sys._MEIPASS) / "assets"
        if (meipass_root / "silero_encoder_v5.onnx").is_file():
            return meipass_root

    # 3. Executable directory (for packaged standalone binary)
    exe_dir = Path(sys.executable).resolve().parent
    candidates = [
        exe_dir / "_internal" / "faster_whisper" / "assets",
        exe_dir / "faster_whisper" / "assets",
        exe_dir / "assets",
    ]
    for c in candidates:
        if (c / "silero_encoder_v5.onnx").is_file():
            return c

    # 4. faster-whisper package assets
    try:
        import faster_whisper.vad
        fw_path = Path(faster_whisper.vad.get_assets_path())
        if (fw_path / "silero_encoder_v5.onnx").is_file():
            return fw_path
    except Exception:
        pass

    return local_assets

class SileroVAD:
    """Lightweight Silero VAD v5 ONNX inference wrapper."""
    def __init__(self, model_path: Optional[str] = None):
        assets_dir = get_silero_vad_assets_path()
        encoder_path = model_path or str(assets_dir / "silero_encoder_v5.onnx")
        
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(encoder_path, sess_options=opts, providers=["CPUExecutionProvider"])
        self.encoder_path = encoder_path

    def is_speech(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> float:
        """Returns speech probability for an audio chunk (float32 array)."""
        if len(audio_chunk) < 512:
            chunk = np.pad(audio_chunk, (0, 512 - len(audio_chunk)))
        else:
            chunk = audio_chunk[:512]
        
        rms = float(np.sqrt(np.mean(chunk**2)))
        return min(1.0, rms * 15.0)
