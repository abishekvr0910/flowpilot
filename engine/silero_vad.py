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
    """True Silero VAD v5 ONNX neural inference engine."""
    def __init__(self, encoder_path: Optional[str] = None, decoder_path: Optional[str] = None):
        assets_dir = get_silero_vad_assets_path()
        enc_path = encoder_path or str(assets_dir / "silero_encoder_v5.onnx")
        dec_cand = Path(enc_path).parent / "silero_decoder_v5.onnx"
        dec_path = decoder_path or (str(dec_cand) if dec_cand.is_file() else str(assets_dir / "silero_decoder_v5.onnx"))
        
        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        opts.log_severity_level = 4
        
        self.encoder_path = enc_path
        self.decoder_path = dec_path
        self.encoder_session = ort.InferenceSession(enc_path, sess_options=opts, providers=["CPUExecutionProvider"])
        self.decoder_session = ort.InferenceSession(dec_path, sess_options=opts, providers=["CPUExecutionProvider"])
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)

    def reset(self):
        """Resets recurrent state and audio context."""
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)

    def is_speech(self, audio_chunk: np.ndarray, sample_rate: int = 16000) -> float:
        """
        Executes true Silero VAD v5 ONNX neural inference on an audio chunk.
        Returns speech probability between 0.0 and 1.0.
        """
        chunk = audio_chunk.flatten().astype(np.float32)
        if sample_rate != 16000 and len(chunk) > 0:
            num_samples = int(len(chunk) * 16000 / sample_rate)
            chunk = np.interp(
                np.linspace(0, len(chunk), num_samples, endpoint=False),
                np.arange(len(chunk)),
                chunk
            ).astype(np.float32)

        # Pad or slice to 512 samples
        if len(chunk) < 512:
            chunk = np.pad(chunk, (0, 512 - len(chunk)))
        else:
            chunk = chunk[:512]

        # 576-sample frame: 64 context samples + 512 audio samples
        x = np.concatenate([self.context, chunk.reshape(1, 512)], axis=1)
        self.context = chunk[-64:].reshape(1, 64)

        # 1. Run Silero Encoder ONNX
        enc_out = self.encoder_session.run(None, {"input": x})[0]
        enc_feat = enc_out.reshape(1, 128)

        # 2. Run Silero Decoder ONNX
        prob_out, new_state = self.decoder_session.run(None, {"input": enc_feat, "state": self.state})
        self.state = new_state

        return float(np.squeeze(prob_out))
