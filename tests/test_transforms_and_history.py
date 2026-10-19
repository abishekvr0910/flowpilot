"""
Unit tests for FlowPilot Selected-Text Transforms & Dictation History Vault
"""

import sys
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.transforms_engine import TransformsEngine, PRESET_TRANSFORMS
from engine.history_vault import HistoryVaultEngine
from engine.orchestrator import FlowOrchestrator
from engine.session import DictationSession


class TestTransformsAndHistory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="fp_test_trans_hist_"))
        self.transforms = TransformsEngine()
        self.vault = HistoryVaultEngine(storage_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_presets_exist(self):
        self.assertIn("make_concise", PRESET_TRANSFORMS)
        self.assertIn("fix_grammar", PRESET_TRANSFORMS)
        self.assertIn("bullet_points", PRESET_TRANSFORMS)
        self.assertIn("professional", PRESET_TRANSFORMS)
        self.assertIn("casual", PRESET_TRANSFORMS)
        self.assertIn("translate_en", PRESET_TRANSFORMS)

    def test_concise_transform_strips_filler(self):
        raw = "I just wanted to let you know that basically we kind of sort of need to deploy the update."
        out, fg_ok = self.transforms.transform_text(raw, "make_concise")
        self.assertTrue(fg_ok)
        self.assertNotIn("basically", out.lower())
        self.assertNotIn("sort of", out.lower())
        self.assertIn("deploy", out.lower())

    def test_grammar_transform_fixes_typos(self):
        raw = "teh quick brown fox cant jump untill tomorrow"
        out, fg_ok = self.transforms.transform_text(raw, "fix_grammar")
        self.assertTrue(fg_ok)
        self.assertIn("The", out)
        self.assertIn("can't", out)
        self.assertIn("until", out)
        self.assertTrue(out.endswith("."))

    def test_bullet_points_transform(self):
        raw = "First we meet with design; next we write API endpoints; finally we run tests."
        out, fg_ok = self.transforms.transform_text(raw, "bullet_points")
        self.assertTrue(fg_ok)
        lines = [l for l in out.split("\n") if l.strip()]
        self.assertGreaterEqual(len(lines), 3)
        for line in lines:
            self.assertTrue(line.startswith("- "))

    def test_professional_tone_transform(self):
        raw = "yeah gonna fix this ASAP, thx bye"
        out, fg_ok = self.transforms.transform_text(raw, "professional")
        self.assertTrue(fg_ok)
        self.assertIn("yes", out.lower())
        self.assertIn("going to", out.lower())
        self.assertIn("as soon as possible", out.lower())

    def test_casual_tone_transform(self):
        raw = "Please be advised that in accordance with our agreement, I am writing to inform you that we are ready."
        out, fg_ok = self.transforms.transform_text(raw, "casual")
        self.assertTrue(fg_ok)
        self.assertIn("heads up", out.lower())

    def test_factguard_invariant_check_preserves_numbers(self):
        raw = "The final invoice is $4,500 due on November 12th."
        out, fg_ok = self.transforms.transform_text(raw, "make_concise")
        self.assertTrue(fg_ok)
        self.assertIn("4,500", out)

    def test_history_vault_record_and_search(self):
        entry = self.vault.record_dictation(
            formatted_text="Deploying FlowPilot 3.1 to production servers.",
            raw_text="deploying flow pilot three point one to production servers",
            target_app="terminal.exe",
            duration_sec=3.5,
            audio_bytes=b"RIFF_FAKE_WAV_BYTES_DATA",
            language="en"
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry["word_count"], 6)
        self.assertIsNotNone(entry["audio_file"])


        # Search matching
        results = self.vault.list_entries(query="FlowPilot")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["target_app"], "terminal.exe")

        # Search non-matching
        no_res = self.vault.list_entries(query="NonExistentTermXYZ")
        self.assertEqual(len(no_res), 0)

    def test_empty_history_vault_does_not_create_files(self):
        untouched_dir = self.temp_dir / "untouched"
        vault = HistoryVaultEngine(storage_dir=untouched_dir)
        self.assertEqual(vault.list_entries(), [])
        self.assertFalse(untouched_dir.exists())

    def test_never_store_bypasses_all_dictation_persistence(self):
        orchestrator = object.__new__(FlowOrchestrator)
        orchestrator.config = {"save_history_text": False, "history": [], "telemetry_enabled": True}
        orchestrator._record_telemetry = Mock()
        session = DictationSession(target_window_info={"process_name": "code.exe"})

        with patch("engine.history_vault.get_history_vault") as vault_factory, \
             patch("engine.insights_engine.get_insights_engine") as insights_factory, \
             patch("engine.orchestrator.save_config") as save_config_mock:
            orchestrator._persist_completed_dictation(
                enabled=False,
                history_entry={"id": 1, "raw_text": "", "formatted_text": ""},
                raw_text="private speech", formatted_text="Private speech.",
                wav_bytes=b"RIFF_PRIVATE_AUDIO", duration_sec=1.0,
                language="en", session=session, telemetry_event={"char_count": 15},
            )

        vault_factory.assert_not_called()
        insights_factory.assert_not_called()
        save_config_mock.assert_not_called()
        orchestrator._record_telemetry.assert_not_called()
        self.assertEqual(orchestrator.config["history"], [])
        self.assertFalse((self.temp_dir / "history_vault.json").exists())
        self.assertFalse((self.temp_dir / "audio").exists())

    def test_explicit_history_opt_in_persists_audio(self):
        orchestrator = object.__new__(FlowOrchestrator)
        orchestrator.config = {"save_history_text": True, "history": [], "telemetry_enabled": False}
        orchestrator._record_telemetry = Mock()
        session = DictationSession(target_window_info={"process_name": "code.exe"})
        entry = {"id": 1, "raw_text": "test", "formatted_text": "Test."}

        with patch("engine.history_vault.get_history_vault", return_value=self.vault), \
             patch("engine.insights_engine.get_insights_engine") as insights_factory, \
             patch("engine.orchestrator.save_config") as save_config_mock:
            orchestrator._persist_completed_dictation(
                enabled=True, history_entry=entry, raw_text="test",
                formatted_text="Test.", wav_bytes=b"RIFF_TEST_AUDIO",
                duration_sec=1.0, language="en", session=session,
                telemetry_event={"char_count": 5},
            )

        insights_factory.return_value.record_dictation.assert_called_once()
        save_config_mock.assert_called_once()
        self.assertEqual(orchestrator.config["history"], [entry])
        self.assertTrue((self.temp_dir / "history_vault.json").exists())
        self.assertTrue((self.temp_dir / "audio" / f"{session.session_id}.wav").exists())

    def test_history_vault_bookmark_and_delete(self):
        entry = self.vault.record_dictation("Note 1", target_app="code.exe")
        entry2 = self.vault.record_dictation("Note 2", target_app="slack.exe")

        eid = entry["id"]
        # Toggle bookmark
        is_bm = self.vault.toggle_bookmark(eid)
        self.assertTrue(is_bm)

        bm_list = self.vault.list_entries(bookmark_only=True)
        self.assertEqual(len(bm_list), 1)
        self.assertEqual(bm_list[0]["id"], eid)

        # Delete entry2
        del_ok = self.vault.delete_entry(entry2["id"])
        self.assertTrue(del_ok)
        self.assertEqual(len(self.vault.list_entries()), 1)

    def test_history_vault_clear_keeps_bookmarks(self):
        e1 = self.vault.record_dictation("Unstarred dictation")
        e2 = self.vault.record_dictation("Starred dictation")
        self.vault.toggle_bookmark(e2["id"])

        cleared = self.vault.clear_all(keep_bookmarks=True)
        self.assertEqual(cleared, 1)

        remaining = self.vault.list_entries()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], e2["id"])

    def test_local_llm_provider_security_rejects_external_urls(self):
        from engine.local_llm import LocalLLMProvider
        provider = LocalLLMProvider(base_url="http://api.openai.com")
        self.assertFalse(provider.is_available())

    def test_local_llm_clean_output(self):
        from engine.local_llm import LocalLLMProvider
        provider = LocalLLMProvider()
        raw_llm = 'Here is the rewritten text:\n```\nThis is the clean text.\n```'
        cleaned = provider._clean_llm_output(raw_llm)
        self.assertEqual(cleaned, "This is the clean text.")

    def test_custom_transform_fallback_when_no_llm(self):
        out, fg_ok = self.transforms.transform_text("First item; Second item", "custom", "format as bullet points")
        self.assertTrue(fg_ok)
        self.assertTrue(out.startswith("- "))


if __name__ == "__main__":
    unittest.main()
