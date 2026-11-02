"""
ONNX Runtime Specialist ASR Package.
Implements offline specialist speech recognition models for low/medium resource languages.
Specification: docs/specs/0006-onnx-multilingual-specialist-asr-harness.md
"""
from engine.onnx_asr.harness import OnnxASRHarness, get_specialist_harness

__all__ = ["OnnxASRHarness", "get_specialist_harness"]
