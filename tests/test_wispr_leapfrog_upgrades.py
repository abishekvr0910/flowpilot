"""
Suite 68: Wispr-Flow-Class Competitive Leapfrog Upgrades Verification.

Covers:
  1. Adaptive 0.85s speech-onset pre-roll vs. 0.35s quiet-room floor
  2. 95-tap Blackman-windowed sinc 48kHz -> 16kHz anti-aliasing attenuation (>50 dB stopband)
  3. Exact CTC prefix beam search path recombination over greedy argmax
  4. Pause-anchored streaming prefix checkpointing & fast tail finalization
  5. Active-window context symbol harvesting (with password/incognito privacy refusal)
     + spoken CamelCase symbol restoration + English/Polish self-correction with FactGuard
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Stage isolated test environment before importing engine modules
_TMP_ENV = tempfile.TemporaryDirectory(prefix="flowpilot-leapfrog-test-")
os.environ.setdefault("FLOWPILOT_CONFIG_DIR", _TMP_ENV.name)
os.environ.setdefault("FLOWPILOT_CONFIG_FILE", str(Path(_TMP_ENV.name) / "config.json"))
os.environ.setdefault("FLOWPILOT_HEADLESS", "1")

import numpy as np

from engine.audio_recorder import AudioRecorder, resample_audio
from engine.context_processor import ContextProcessor
from engine.onnx_asr.harness import OnnxASRHarness
from engine.stt_engine import STTEngine
from engine.window_inspector import WindowInspector


class _DummyHotStream:
    active = True

    def abort(self):
        pass

    def close(self):
        pass


class TestWisprLeapfrogUpgrades(unittest.TestCase):
    def test_adaptive_preroll_quiet_vs_early_speech(self):
        chunk = 320  # 20ms @ 16kHz
        rng = np.random.default_rng(7)

        # Case A: 850ms of quiet room floor -> only trailing ~0.35s retained on start_recording()
        rec_quiet = AudioRecorder(sample_rate=16000, channels=1)
        rec_quiet.stream = _DummyHotStream()
        rec_quiet._last_callback_at = time.monotonic()
        quiet_idle = (rng.normal(0.0, 0.001, size=int(0.85 * 16000))).astype(np.float32)
        for pos in range(0, len(quiet_idle), chunk):
            frame = quiet_idle[pos : pos + chunk].reshape(-1, 1)
            rec_quiet._audio_callback(frame, len(frame), None, None)

        rec_quiet.start_recording()
        quiet_samples = sum(len(f) for f in rec_quiet.audio_frames)
        self.assertLessEqual(quiet_samples, int(0.42 * 16000))
        self.assertGreaterEqual(quiet_samples, int(0.30 * 16000))

        # Case B: 200ms quiet + 650ms early spoken words BEFORE hotkey -> full speech onset preserved
        rec_early = AudioRecorder(sample_rate=16000, channels=1)
        rec_early.stream = _DummyHotStream()
        rec_early._last_callback_at = time.monotonic()
        t = np.arange(int(0.65 * 16000), dtype=np.float32) / 16000.0
        early_voice = (0.12 * np.sin(2.0 * np.pi * 220.0 * t)).astype(np.float32)
        pre_stream = np.concatenate([quiet_idle[: int(0.20 * 16000)], early_voice])
        for pos in range(0, len(pre_stream), chunk):
            frame = pre_stream[pos : pos + chunk].reshape(-1, 1)
            rec_early._audio_callback(frame, len(frame), None, None)

        rec_early.start_recording()
        early_samples = sum(len(f) for f in rec_early.audio_frames)
        self.assertGreaterEqual(early_samples, int(0.75 * 16000))

        # Verify live non-destructive snapshot works while recording is active
        snap = rec_early.get_active_recording_snapshot()
        self.assertIsNotNone(snap)
        self.assertEqual(len(snap), early_samples)

    def test_windowed_sinc_48khz_antialiasing_attenuation(self):
        sr_in, sr_out = 48000, 16000
        t = np.arange(sr_in, dtype=np.float32) / float(sr_in)

        # In-band 1 kHz speech fundamental must pass unattenuated
        inband = np.sin(2.0 * np.pi * 1000.0 * t).astype(np.float32)
        out_inband = resample_audio(inband, sr_in, sr_out)
        # Skip 10ms filter group delay at edges when checking steady-state RMS
        rms_in = float(np.sqrt(np.mean(inband[1000:-1000] ** 2)))
        rms_out_inband = float(np.sqrt(np.mean(out_inband[400:-400] ** 2)))
        self.assertAlmostEqual(rms_out_inband / rms_in, 1.0, delta=0.03)

        # Out-of-band 14.2 kHz ultrasonic/HF preamp tone must NOT fold into 1.8 kHz (>50 dB suppression)
        outband = np.sin(2.0 * np.pi * 14200.0 * t).astype(np.float32)
        out_aliased = resample_audio(outband, sr_in, sr_out)
        rms_alias = float(np.sqrt(np.mean(out_aliased[400:-400] ** 2)))
        self.assertLess(rms_alias, 0.0025, f"Expected >50 dB stopband rejection, got RMS={rms_alias}")

    def test_ctc_prefix_beam_search_recombination_beats_greedy(self):
        # 2 frames, vocab: {0: 'க', 1: 'த', 2: '<blk>'}
        # Frame 0: P('க')=0.40, P('த')=0.15, P(<blk>)=0.45  -> Greedy picks <blk>
        # Frame 1: P('க')=0.40, P('த')=0.15, P(<blk>)=0.45  -> Greedy picks <blk> -> Greedy output: []
        # True CTC marginal P("க") = 0.40*0.40 + 0.40*0.45 + 0.45*0.40 = 0.52 > P("") = 0.45*0.45 = 0.2025!
        probs = np.array(
            [
                [0.40, 0.15, 0.45],
                [0.40, 0.15, 0.45],
            ],
            dtype=np.float32,
        )
        logprobs = np.log(probs)
        vocab = {0: "க", 1: "த", 2: "<blk>"}
        greedy = [int(x) for x in np.argmax(logprobs, axis=-1) if x != 2]
        self.assertEqual(greedy, [])

        beam_out = OnnxASRHarness._ctc_prefix_beam_search(logprobs, vocab=vocab, blank_id=2, beam_size=4)
        self.assertEqual(beam_out, [0])

    def test_pause_split_and_checkpoint_fast_tail(self):
        sr = 16000
        t1 = np.arange(int(2.6 * sr), dtype=np.float32) / sr
        clause1 = (0.10 * np.sin(2.0 * np.pi * 200.0 * t1)).astype(np.float32)
        pause = np.zeros(int(0.30 * sr), dtype=np.float32)
        t2 = np.arange(int(0.8 * sr), dtype=np.float32) / sr
        clause2 = (0.10 * np.sin(2.0 * np.pi * 260.0 * t2)).astype(np.float32)

        combined = np.concatenate([clause1, pause, clause2])
        split = STTEngine.find_pause_split_sample(combined)
        self.assertIsNotNone(split)
        # Split must fall squarely inside the silent pause [2.6s .. 2.9s]
        self.assertGreaterEqual(split, int(2.6 * sr))
        self.assertLessEqual(split, int(2.9 * sr))

        class _StubSTT(STTEngine):
            def __init__(self):
                self.config = {"language": "en"}
                self.calls = 0

            def transcribe(self, audio_data, **kwargs):
                self.calls += 1
                return {
                    "text": f"clause_{self.calls}",
                    "detected_language": "en",
                    "engine": "stub",
                }

        stub = _StubSTT()
        cp = stub.build_pause_prefix_checkpoint(combined, language="en")
        self.assertEqual(cp["prefix_text"], "clause_1")

        # Active tail decodes only clause 2 and joins cleanly
        res_active = stub.transcribe_with_checkpoint(combined, checkpoint=cp, language="en")
        self.assertEqual(res_active["text"], "clause_1 clause_2")
        self.assertTrue(res_active["used_prefix_checkpoint"])

        # Silent tail after checkpoint returns immediately with 0 extra STT calls
        calls_before = stub.calls
        silent_tail_audio = np.concatenate([combined[: cp["split_sample"]], np.zeros(1600, dtype=np.float32)])
        res_fast = stub.transcribe_with_checkpoint(silent_tail_audio, checkpoint=cp, language="en")
        self.assertEqual(res_fast["text"], "clause_1")
        self.assertEqual(stub.calls, calls_before)

    def test_context_symbol_harvesting_privacy_and_multilingual_correction(self):
        # 1. Privacy refusal on password managers & private browsing
        pw_vocab = WindowInspector.extract_context_vocabulary(
            {"title": "Bitwarden - Master Password Vault", "process_name": "bitwarden.exe"},
            "SecretApiKeyToken = 123",
        )
        self.assertEqual(pw_vocab, [])
        incog_vocab = WindowInspector.extract_context_vocabulary(
            {"title": "Sign In - Google Chrome (Incognito)", "process_name": "chrome.exe"},
            "class OAuthSessionManager:",
        )
        self.assertEqual(incog_vocab, [])

        # 2. Developer window symbol harvesting + spoken CamelCase restoration
        win = {"title": "harness.py - flowpilot - Visual Studio Code", "process_name": "code.exe", "category": "developer"}
        surr = "from engine.onnx_asr.harness import OnnxASRHarness\nfrom engine.selection_rewriter import SelectionRewriter\n"
        vocab = WindowInspector.extract_context_vocabulary(win, surr)
        self.assertIn("OnnxASRHarness", vocab)
        self.assertIn("SelectionRewriter", vocab)

        proc = ContextProcessor({"active_tone_mode": "developer"})
        out_sym = proc.process(
            "update onnx asr harness and call selection rewriter",
            win,
            session_mode="developer",
            language="en",
            preceding_text=surr,
        )
        self.assertIn("OnnxASRHarness", out_sym)
        self.assertIn("SelectionRewriter", out_sym)

        # Prose noun phrases ("the access token") must NOT be mangled into snake_case
        out_prose = proc.process(
            "we must never expose the access token",
            {"title": "security.py - Visual Studio Code", "process_name": "code.exe", "category": "developer"},
            session_mode="developer",
            language="en",
            preceding_text="def verify_access_token(access_token: str):\n",
        )
        self.assertIn("never expose the access token", out_prose.lower())

        # 3. English "scratch that" value slot correction + FactGuard
        out_scratch = proc.process(
            "deploy on port 8080 scratch that port 8765",
            win,
            session_mode="developer",
            language="en",
        )
        self.assertNotIn("8080", out_scratch)
        self.assertIn("8765", out_scratch)

        # 4. Polish "nie czekaj" + "przepraszam" self-corrections + FactGuard
        out_pl_day = proc.process(
            "spotkajmy się we wtorek nie czekaj w środę",
            {"title": "Notatnik", "process_name": "notepad.exe"},
            session_mode="professional",
            language="pl",
        )
        self.assertNotIn("wtorek", out_pl_day.lower())
        self.assertIn("w środę", out_pl_day.lower())

        out_pl_num = proc.process(
            "wyślij 5 kopii przepraszam 10 kopii",
            {"title": "Outlook", "process_name": "outlook.exe"},
            session_mode="professional",
            language="pl",
        )
        self.assertNotIn("5 ", out_pl_num)
        self.assertIn("10 kopii", out_pl_num.lower())

    def test_user_transforms_and_clipboard_privacy(self):
        # 1. User-scriptable transform integration in ~/.flowpilot/transforms.py
        from engine.config import get_config_dir
        from engine.user_transforms import UserTransformManager
        UserTransformManager._instance = None

        transforms_file = get_config_dir() / "transforms.py"
        script = (
            "def transform_jira_issue(text, context=None):\n"
            "    import re\n"
            "    return re.sub(r'\\bissue\\s+(\\d+)\\b', r'FLOW-\\1', text, flags=re.IGNORECASE)\n"
        )
        transforms_file.write_text(script, encoding="utf-8")

        proc = ContextProcessor({"active_tone_mode": "general"})
        res = proc.process("please review issue 4099 immediately", {"title": "Slack", "process_name": "slack.exe"})
        self.assertIn("FLOW-4099", res)

        # Clean up transforms file so it doesn't affect subsequent tests
        try:
            transforms_file.unlink(missing_ok=True)
            UserTransformManager._instance = None
        except Exception:
            pass

        # 2. Windows clipboard exclusion flags for privacy (zero history/cloud retention)
        from engine.text_injector import TextInjector
        # Must execute cleanly on Windows without raising exceptions
        TextInjector._exclude_clipboard_from_history_and_cloud()


if __name__ == "__main__":
    unittest.main()
