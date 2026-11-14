"""CUDA may fail only when faster-whisper's lazy segments are consumed."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.stt_engine import STTEngine


class CudaFallbackTests(unittest.TestCase):
    def model(self, device, error=None):
        def transcribe(audio, **kwargs):
            def segments():
                if error:
                    yield SimpleNamespace(text="Discard partial failed decoding")
                    raise RuntimeError(error)
                yield SimpleNamespace(text="Recovered on CPU")
            return segments(), SimpleNamespace(language="en", duration=1.0)
        return SimpleNamespace(transcribe=transcribe, hf_tokenizer=None)

    def test_lazy_cuda_failure_retries_cpu_and_keeps_cpu_model(self):
        constructed = []
        def factory(target, **kwargs):
            constructed.append(kwargs)
            return self.model(kwargs["device"],
                              "Library cublas64_12.dll is not found or cannot be loaded"
                              if kwargs["device"] == "cuda" else None)

        config = {"local_model_size": "base", "device": "auto", "compute_type": "auto"}
        with patch("ctranslate2.get_cuda_device_count", return_value=1), \
             patch("engine.stt_engine.WhisperModel", side_effect=factory):
            engine = STTEngine(config, personalization=object())
            for _ in range(2):
                result = engine._transcribe_local(np.zeros(16000, dtype=np.float32), "", "en")
                self.assertEqual(result["text"], "Recovered on CPU")
            self.assertEqual([x["device"] for x in constructed], ["cuda", "cpu"])
            self.assertTrue(all(x["local_files_only"] for x in constructed))
            self.assertEqual(constructed[-1]["compute_type"], "int8")
            self.assertEqual(engine.get_model_status()["active_device"], "cpu")
            self.assertEqual(engine.get_model_status()["active_inferences"], 0)
            self.assertEqual(config["device"], "auto")

    def test_constructor_fallback_is_cached(self):
        devices = []
        def factory(target, **kwargs):
            devices.append(kwargs["device"])
            if kwargs["device"] == "cuda":
                raise RuntimeError("CUDA driver unavailable")
            return self.model("cpu")
        with patch("engine.stt_engine.WhisperModel", side_effect=factory):
            engine = STTEngine({"device": "cuda", "compute_type": "auto"}, personalization=object())
            first = engine._get_local_model()
            self.assertIs(first, engine._get_local_model())
        self.assertEqual(devices, ["cuda", "cpu"])

    def test_non_cuda_error_is_not_retried(self):
        with patch("engine.stt_engine.WhisperModel", return_value=self.model("cpu", "invalid audio")) as factory:
            engine = STTEngine({"device": "cpu"}, personalization=object())
            with self.assertRaisesRegex(RuntimeError, "invalid audio"):
                engine._transcribe_local(np.zeros(16000, dtype=np.float32), "", "en")
            factory.assert_called_once()
            self.assertFalse(engine._cuda_failed)
            self.assertEqual(engine.get_model_status()["active_inferences"], 0)

    def test_cpu_retry_failure_is_propagated(self):
        devices = []
        def factory(target, **kwargs):
            devices.append(kwargs["device"])
            return self.model(kwargs["device"], "CUDA failed" if kwargs["device"] == "cuda" else "CPU failed")
        with patch("engine.stt_engine.WhisperModel", side_effect=factory):
            engine = STTEngine({"device": "cuda"}, personalization=object())
            with self.assertRaisesRegex(RuntimeError, "CPU failed"):
                engine._transcribe_local(np.zeros(16000, dtype=np.float32), "", "en")
        self.assertEqual(devices, ["cuda", "cpu"])


if __name__ == "__main__":
    unittest.main()
