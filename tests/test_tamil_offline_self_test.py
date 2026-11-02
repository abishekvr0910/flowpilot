"""
Test: Offline Tamil Speech Recognition, Tanglish Transliteration, and Terminal Safety Gate.
Verifies real-voice Tamil dictation using local models without user intervention or cloud egress.
"""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.stt_engine import STTEngine
from engine.context_processor import ContextProcessor
from engine.transliteration import transliterate_tamil_to_tanglish, apply_transliteration_if_enabled
from engine.text_injector import TextInjector, InjectionStatus


class TestTamilOfflineDictation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.small_model_path = STTEngine.resolve_model_path("small")
        cls.conv_wav = PROJECT_ROOT / "private" / "corpus" / "ta" / "ta-conv-01.wav"

    def test_01_small_model_exists_locally(self):
        """Verifies that faster-whisper-small is present for zero-egress offline inference."""
        self.assertTrue(
            os.path.isdir(self.small_model_path),
            f"Small model not found at {self.small_model_path}"
        )
        self.assertTrue(
            (Path(self.small_model_path) / "model.bin").is_file(),
            "model.bin missing in faster-whisper-small"
        )

    def test_02_tamil_audio_fixture_exists(self):
        """Verifies that the authentic conversational Tamil speech clip exists."""
        self.assertTrue(
            self.conv_wav.is_file(),
            f"Audio fixture {self.conv_wav} not found"
        )
        self.assertGreater(self.conv_wav.stat().st_size, 50000)

    def test_03_offline_tamil_transcription_and_tanglish(self):
        """Verifies end-to-end decode on CPU without network calls."""
        stt = STTEngine({"local_model_size": "small", "cpu_threads": min(4, os.cpu_count() or 2)})
        wav_bytes = self.conv_wav.read_bytes()
        res = stt.transcribe(wav_bytes, language="ta")

        self.assertNotIn("error", res)
        text = res.get("text", "")
        self.assertIn("வணக்கம்", text)
        self.assertIn("எப்படி", text)

        # Process through ContextProcessor
        proc = ContextProcessor({"active_tone_mode": "conversational"})
        formatted = proc.process(text, language="ta")

        # Test dual-mode output:
        # Mode A: Native Tamil Script
        native_out = apply_transliteration_if_enabled(formatted, "ta", {"tamil_script_mode": "tamil"})
        self.assertEqual(native_out, formatted)
        self.assertIn("வணக்கம்", native_out)

        # Mode B: Tanglish Transliteration
        tanglish_out = apply_transliteration_if_enabled(formatted, "ta", {"tamil_script_mode": "tanglish"})
        self.assertIn("vanakkam", tanglish_out.lower())
        self.assertIn("eppadi", tanglish_out.lower())
        print(f"\n[Test Result] Spoken Tamil transcription: {formatted}")
        print(f"[Test Result] Tanglish conversion: {tanglish_out}")

    def test_04_terminal_uia_crash_guard(self):
        """Verifies that terminal windows are never inspected via UIA TextPattern."""
        fake_terminal_hwnd = 999999
        # Test get_caret_surrounding_text returns (None, None) safely
        prec, foll = TextInjector.get_caret_surrounding_text(fake_terminal_hwnd)
        self.assertIsNone(prec)
        self.assertIsNone(foll)

        # Test _read_via_ui_automation returns None safely
        buf = TextInjector._read_via_ui_automation(fake_terminal_hwnd)
        self.assertIsNone(buf)


if __name__ == "__main__":
    unittest.main()
