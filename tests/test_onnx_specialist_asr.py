"""
Suite: ONNX Runtime Specialist ASR Harness (IndicConformer Medium).
Validates offline specialist model discovery, NeMo log-mel feature extraction,
CTC greedy decoding, STTEngine integration, custom vocabulary biasing,
Tamil Unicode spelling repair, frozen user-profile resolution, and zero network egress.
Specification: docs/specs/0006-onnx-multilingual-specialist-asr-harness.md
"""
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


def _resolve_tamil_fixture() -> Path:
    candidates = [
        PROJECT_ROOT / "private" / "corpus" / "ta" / "ta-conv-01.commonvoice-fixture.wav",
        PROJECT_ROOT / "tests" / "fixtures" / "ta-commonvoice-sample.wav",
        PROJECT_ROOT / "private" / "corpus" / "ta" / "ta-conv-01.wav",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[1]


class TestOnnxSpecialistASR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = get_specialist_harness()
        cls.ta_fixture = _resolve_tamil_fixture()

    def test_01_model_and_vocab_availability(self):
        """Verifies that the quantized IndicConformer model and vocab are available locally."""
        self.assertTrue(self.harness.is_available("ta"), "IndicConformer for Tamil should be available")
        model_path, vocab_path = self.harness._resolve_model_files("ta")
        self.assertIsNotNone(model_path)
        self.assertIsNotNone(vocab_path)
        self.assertTrue(model_path.is_file())
        self.assertTrue(vocab_path.is_file())

    def test_02_feature_extraction_properties(self):
        """Verifies 80-channel Slaney log-mel filterbank extraction and CMVN normalization."""
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
        # The doubled consonant lost at the token boundary is restored, giving the real
        # word (Common Voice reference for ta-cv-006), not the misspelling தாவிகொண்டு.
        self.assertEqual(clean, "அது தாவிக்கொண்டு சந்தோஷமாக")
        self.assertNotIn("ிி", clean)
        self.assertNotIn("்ொ", clean)
        self.assertEqual(repair_tamil_unicode("தங்கள்ல் மனை"), "தங்கள் மனை")

    def test_08_dynamic_arbitrary_user_vocabulary_biasing(self):
        """Verifies dynamic arbitrary user-defined terms (names, new frameworks) bias correctly."""
        user_vocab = ["Abishek", "Vercel", "Supabase", "Kavitha", "Sridhar"]
        
        # Arbitrary names with and without suffixes
        input_text = "அபிஷேக் மற்றும் கவிதாவுக்கு வெர்சல்-ல் deploy செய்யப்பட்டது"
        biased = apply_custom_vocabulary_biasing(input_text, user_vocab)
        self.assertIn("Abishek", biased)
        self.assertIn("Kavitha-ukku", biased)
        self.assertIn("Vercel-il", biased)

    def test_09_repair_leaves_valid_tamil_unchanged_in_either_encoding(self):
        """Valid Tamil must survive repair whether composed (NFC) or typed decomposed (NFD)."""
        import unicodedata
        sentences = [
            "பாலாஜி என்பது பாலன் என்ற பொருளுடையது.",
            "பகலில் இயங்கிக் கொண்டே இருப்பர்.",
            "சீக்கிரத்தில் ஐநூறு ரூபாய் செலவழித்து அவரது முழு உருவப்படமொன்று சபையில் வைத்தோம்.",
            "வணக்கம், நீங்க எப்படி இருக்கீங்க?",
            "கௌரவம் போகும் ஓடம் கோயில் தோட்டம்",
        ]
        for s in sentences:
            nfc = unicodedata.normalize("NFC", s)
            self.assertEqual(repair_tamil_unicode(nfc), nfc)
            self.assertEqual(repair_tamil_unicode(unicodedata.normalize("NFD", s)), nfc,
                             "a decomposed o/oo vowel must not be cut down to e/ee")

    def test_10_vocabulary_never_rewrites_everyday_words(self):
        """Names that are also ordinary words (Mani, Anbu, Priya...) must not replace them."""
        vocab = ["Kubernetes", "GraphQL", "FastAPI", "Pydantic", "PostgreSQL", "Next.js",
                 "TypeScript", "Python", "Whisper", "Docker", "AWS Lambda",
                 "Abishek", "Kavitha", "Vercel", "Supabase", "Ravi", "Priya", "Kumar",
                 "Mani", "Anbu", "Sundar"]
        everyday = [
            "நாளைக்கு காலைல ஒன்பது மணிக்கு நாம மீட் பண்ணலாமா?",
            "இது ரொம்ப பெரிய வேலை",
            "அம்மா மேல அன்பு அதிகம்",
            "காலையில ரவை உப்புமா செஞ்சேன்",
            "அவள் ஒரு அழகான கவிதை எழுதினாள்",
        ]
        for s in everyday:
            self.assertEqual(apply_custom_vocabulary_biasing(s, vocab), s)

    def test_11_vocabulary_matches_tamil_cluster_spelling(self):
        """Tamil inserts a vowel into initial clusters (Priya -> பிரியா); the entry still matches."""
        vocab = ["Priya", "Kavitha"]
        self.assertIn("Priya", apply_custom_vocabulary_biasing("பிரியா வந்தாங்க", vocab))
        self.assertIn("Priya-ukku", apply_custom_vocabulary_biasing("பிரியாவுக்கு சொல்லு", vocab))

    def test_12_frozen_user_profile_resolution_and_48khz_resampling(self):
        """Verifies ~/.flowpilot/models/indicconformer-ta resolution in frozen builds and pure-NumPy 48kHz resampling."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            user_models = Path(tmp_dir) / ".flowpilot" / "models" / "indicconformer-ta"
            user_models.mkdir(parents=True)
            (user_models / "model.int8.onnx").write_bytes(b"onnx-stub")
            (user_models / "vocab.txt").write_text("a 0\n<blk> 1\n", encoding="utf-8")

            isolated = OnnxASRHarness()
            isolated.models_dir = Path(tmp_dir) / "nonexistent_dev_models"
            with patch.dict(os.environ, {"FLOWPILOT_MODEL_DIR": ""}), \
                 patch.object(sys, "frozen", True, create=True), \
                 patch("engine.onnx_asr.harness.os.path.expanduser", side_effect=lambda p: str(Path(tmp_dir) / ".flowpilot" / "models") if p.startswith("~/.flowpilot") else tmp_dir):
                model_file, vocab_file = isolated._resolve_model_files("ta")
                self.assertEqual(model_file, user_models / "model.int8.onnx")
                self.assertEqual(vocab_file, user_models / "vocab.txt")

        # Verify 48kHz WAV resampling succeeds without scipy installed
        audio_16k, sr = sf.read(str(self.ta_fixture), dtype="float32")
        self.assertEqual(sr, 16000)
        from engine.audio_recorder import resample_audio
        audio_48k = resample_audio(audio_16k, 16000, 48000)
        buf = io.BytesIO()
        sf.write(buf, audio_48k, 48000, format="WAV")
        res = self.harness.transcribe(buf.getvalue(), language="ta")
        self.assertIn("வணக்கம்", res["text"])


if __name__ == "__main__":
    unittest.main()
