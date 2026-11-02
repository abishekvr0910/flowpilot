"""
Suite: ONNX Runtime Specialist ASR Harness (IndicConformer Medium).
Validates offline specialist model discovery, NeMo log-mel feature extraction,
CTC greedy decoding, STTEngine integration, custom vocabulary biasing,
Tamil Unicode spelling repair, and zero network egress.
Specification: docs/specs/0006-onnx-multilingual-specialist-asr-harness.md
"""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import soundfile as sf
import numpy as np
from engine.onnx_asr.harness import (
    OnnxASRHarness, get_specialist_harness,
    apply_custom_vocabulary_biasing, repair_tamil_unicode
)
from engine.stt_engine import STTEngine
from engine.transliteration import apply_transliteration_if_enabled


class TestOnnxSpecialistASR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = get_specialist_harness()
        cls.ta_fixture = PROJECT_ROOT / "private" / "corpus" / "ta" / "ta-conv-01.wav"

    def test_01_model_and_vocab_availability(self):
        """Verifies that the quantized IndicConformer model and vocab are available locally."""
        self.assertTrue(self.harness.is_available("ta"), "IndicConformer for Tamil should be available")
        model_path, vocab_path = self.harness._resolve_model_files("ta")
        self.assertIsNotNone(model_path)
        self.assertIsNotNone(vocab_path)
        self.assertTrue(model_path.is_file())
        self.assertTrue(vocab_path.is_file())

    def test_02_feature_extraction_properties(self):
        """Verifies 80-channel log-mel filterbank extraction and CMVN normalization."""
        audio, sr = sf.read(str(self.ta_fixture))
        features = self.harness.extract_features(audio, sr=sr)
        self.assertEqual(features.shape[0], 80, "Must produce 80 mel channels")
        self.assertGreater(features.shape[1], 100, "Time dimension should reflect audio duration")
        self.assertFalse(np.isnan(features).any(), "Features must not contain NaNs")
        self.assertFalse(np.isinf(features).any(), "Features must not contain Infs")

        # Verify per-feature zero mean approximately
        means = np.mean(features, axis=1)
        self.assertTrue(np.allclose(means, 0.0, atol=1e-3), "CMVN should yield near-zero channel means")

    def test_03_transcribe_end_to_end_indicconformer(self):
        """Verifies offline CTC decoding on authentic spoken Tamil speech."""
        audio_bytes = self.ta_fixture.read_bytes()
        res = self.harness.transcribe(audio_bytes, language="ta")

        self.assertIn("text", res)
        self.assertEqual(res["engine"], "indic_conformer_onnx")
        self.assertEqual(res["detected_language"], "ta")
        self.assertGreater(res["duration"], 4.0)

        raw_text = res["text"]
        print(f"\n[IndicConformer Raw Transcript]: '{raw_text}'")
        self.assertIn("வணக்கம்", raw_text)
        self.assertIn("எப்படி", raw_text)

        # Test downstream Tanglish transformation
        tanglish = apply_transliteration_if_enabled(raw_text, "ta", {"tamil_script_mode": "tanglish"})
        print(f"[IndicConformer Tanglish]: '{tanglish}'")
        self.assertIn("vanakkam", tanglish.lower())
        self.assertIn("eppadi", tanglish.lower())

    def test_04_stt_engine_specialist_integration(self):
        """Verifies STTEngine routes Tamil to IndicConformer when specialist is enabled."""
        stt = STTEngine({"use_specialist_asr": True, "local_model_size": "base"})
        audio_bytes = self.ta_fixture.read_bytes()
        res = stt.transcribe(audio_bytes, language="ta")

        self.assertEqual(res.get("engine"), "indic_conformer_onnx")
        self.assertIn("வணக்கம்", res["text"])

    def test_05_stt_engine_whisper_fallback_when_disabled(self):
        """Verifies STTEngine cleanly falls back to Whisper when specialist is disabled."""
        stt = STTEngine({"use_specialist_asr": False, "local_model_size": "small", "cpu_threads": 4})
        audio_bytes = self.ta_fixture.read_bytes()
        res = stt.transcribe(audio_bytes, language="ta")

        self.assertEqual(res.get("engine"), "local_faster_whisper")
        self.assertIn("வணக்கம்", res["text"])

    def test_06_custom_vocabulary_biasing(self):
        """Verifies custom dictionary term preservation and case restoration in Tamil dictation."""
        vocab = ["Docker", "Kubernetes", "GraphQL", "Python", "FlowPilot"]
        
        # Test phonetic loanword with suffix replacement
        sample_input = "இங்கே டாக்கருக்கு ரன் பண்ணு மற்றும் பைதான் ஸ்கிரிப்ட் இயக்கு"
        biased = apply_custom_vocabulary_biasing(sample_input, vocab)
        self.assertIn("Docker-ukku", biased)
        self.assertIn("Python", biased)

        # Test ASCII casing restoration
        ascii_input = "docker image build pannu flowpilot start"
        biased_ascii = apply_custom_vocabulary_biasing(ascii_input, vocab)
        self.assertIn("Docker", biased_ascii)
        self.assertIn("FlowPilot", biased_ascii)

    def test_07_repair_tamil_unicode_spelling_bugs(self):
        """Verifies that stacked combining vowel signs and illegal virama sequences are normalized."""
        # ta-cv-006 bug case: stacked vowel signs and virama + vowel
        corrupt = "அது தாவிிக்ொண்டு சந்தோஷமாக"
        clean = repair_tamil_unicode(corrupt)
        self.assertEqual(clean, "அது தாவிகொண்டு சந்தோஷமாக")
        self.assertNotIn("ிி", clean)
        self.assertNotIn("்ொ", clean)

    def test_08_dynamic_arbitrary_user_vocabulary_biasing(self):
        """Verifies dynamic arbitrary user-defined terms (names, new frameworks) bias correctly."""
        user_vocab = ["Abishek", "Vercel", "Supabase", "Kavitha", "Sridhar"]
        
        # Arbitrary names with and without suffixes
        input_text = "அபிஷேக் மற்றும் கவிதாவுக்கு வெர்சல்-ல் deploy செய்யப்பட்டது"
        biased = apply_custom_vocabulary_biasing(input_text, user_vocab)
        self.assertIn("Abishek", biased)
        self.assertIn("Kavitha-ukku", biased)
        self.assertIn("Vercel-il", biased)


if __name__ == "__main__":
    unittest.main()
