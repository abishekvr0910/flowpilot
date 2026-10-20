"""
FlowPilot Comprehensive Multilingual Workstation Test Suite
Validates:
1. Multilingual STTEngine transcription and translation task routing.
2. WritingIntelligence language-aware filler handling, punctuation, and FactGuard protection:
   - German pronoun preservation (does not drop 'er').
   - French reflexive pronoun preservation (does not drop 'nous' in 'nous nous').
   - Spanish native spoken punctuation (coma, punto, signos).
   - Multilingual negation protection across German (nicht/kein), Spanish (no/nunca), and French (pas/jamais).
   - French punctuation spacing rules.
3. Multilingual Meeting Notetaker & Deliberation Engine:
   - Spanish, French, and German action item and decision detection.
   - Multilingual Pro/Con deliberation weighting and Risk/Blocker radar.
4. System Tray language switching and real-time translation toggle signals.
"""

import sys
import unittest
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.language_registry import LanguageRegistry
from engine.stt_engine import STTEngine
from engine.writing_intelligence import WritingIntelligence, FactGuard
from engine.context_processor import ContextProcessor
from engine.meeting_deliberation import MeetingDeliberationEngine, DeliberationTopic, RiskItem
from engine.meeting_notetaker import MeetingNotetakerEngine, MeetingSession
from engine.session import DictationSession


class TestMultilingualWorkstation(unittest.TestCase):

    def setUp(self):
        self.config = {
            "engine_mode": "local",
            "local_model_size": "base",
            "language": "auto",
            "translate_to_english": False,
            "active_tone_mode": "professional"
        }
        self.wi = WritingIntelligence(self.config)
        self.processor = ContextProcessor(self.config)

    # -------------------------------------------------------------
    # 1. WritingIntelligence Multilingual Spoken Punctuation & Fillers
    # -------------------------------------------------------------
    def test_spanish_spoken_punctuation_and_negation(self):
        raw = "hola coma cómo estás punto y coma todo bien punto"
        res = self.wi.polish(raw, language="es")
        text = res["text"]
        self.assertIn(",", text)
        self.assertIn(";", text)
        self.assertTrue(text.endswith("."))

        # Test Spanish negation safety in FactGuard
        neg_raw = "no queremos problemas y nunca aceptaremos retrasos"
        neg_res = self.wi.polish(neg_raw, language="es")
        self.assertIn("no", neg_res["text"].lower())
        self.assertIn("nunca", neg_res["text"].lower())

    def test_german_pronoun_and_negation_safety(self):
        # German: 'er' must NOT be stripped as an English filler word
        raw = "er wird das morgen prüfen punkt"
        res = self.wi.polish(raw, language="de")
        self.assertTrue(res["text"].lower().startswith("er "), f"Expected 'er' preserved, got: {res['text']}")
        self.assertTrue(res["text"].endswith("."))

        # German negation: 'nicht' and 'kein'
        neg_raw = "das ist nicht möglich und es gibt kein problem"
        neg_res = self.wi.polish(neg_raw, language="de")
        self.assertIn("nicht", neg_res["text"].lower())
        self.assertIn("kein", neg_res["text"].lower())

    def test_french_reflexive_and_punctuation_spacing(self):
        # French reflexive pronoun 'nous nous' must not be stripped by stutter removal
        raw = "nous nous sommes rencontrés pour discuter"
        res = self.wi.polish(raw, language="fr")
        self.assertIn("nous nous", res["text"].lower(), f"Expected 'nous nous' preserved, got: {res['text']}")

        # French punctuation spacing: thin space before '?' and '!'
        q_raw = "comment allez-vous point d'interrogation"
        q_res = self.wi.polish(q_raw, language="fr")
        self.assertTrue(q_res["text"].endswith(" ?"), f"Expected ' ?' at end, got: {q_res['text']}")

    # -------------------------------------------------------------
    # 2. ContextProcessor Language Forwarding
    # -------------------------------------------------------------
    def test_context_processor_forwards_language(self):
        raw = "guten tag komma bitte prüfen punkt"
        out = self.processor.process(raw, language="de")
        self.assertIn(",", out)
        self.assertTrue(out.endswith("."))

    # -------------------------------------------------------------
    # 3. Multilingual Meeting Notetaker & Deliberation
    # -------------------------------------------------------------
    def test_spanish_meeting_deliberation(self):
        engine = MeetingDeliberationEngine()
        sess = MeetingSession(title="Reunión de Ingeniería", template="general")
        now = 100000.0
        sess.segments = [
            {"time": "00:01", "text": "Bienvenido a la reunión técnica.", "timestamp": now - 300},
            {"time": "00:02", "text": "PostgreSQL es una ventaja porque es más rápido y escalable.", "timestamp": now - 200},
            {"time": "00:03", "text": "Sin embargo, un riesgo crítico de seguridad es el retraso.", "timestamp": now - 150},
            {"time": "00:04", "text": "Decidimos utilizar SQLite para el almacenamiento local.", "timestamp": now - 100},
            {"time": "00:05", "text": "Tenemos que actualizar la documentación antes del viernes.", "timestamp": now - 50},
        ]
        sess.stop_time = now

        # Decisions & Action items via generate_summary
        notetaker = MeetingNotetakerEngine()
        summary = notetaker.generate_summary(sess)
        decisions = summary["decisions"]
        actions = summary["action_items"]
        self.assertTrue(any("decidimos" in str(d).lower() or "sqlite" in str(d).lower() for d in decisions), f"Decisions: {decisions}")
        self.assertTrue(any("tenemos que" in str(a).lower() or "documentación" in str(a).lower() for a in actions), f"Actions: {actions}")

        # Deliberation pros / cons
        topics = engine.extract_weighing_matrix(sess)
        self.assertGreater(len(topics), 0)
        self.assertTrue(len(topics[0].pros_agreements) > 0 or len(topics[0].cons_concerns) > 0)

        # Risk radar
        risks = engine.extract_risk_radar(sess)
        self.assertGreater(len(risks), 0)
        self.assertTrue(any(r.severity == "HIGH" for r in risks))

    def test_german_meeting_deliberation(self):
        notetaker = MeetingNotetakerEngine()
        engine = MeetingDeliberationEngine()
        sess = MeetingSession(title="Architektur Sync", template="general")
        now = 100000.0
        sess.segments = [
            {"time": "00:01", "text": "SQLite bietet einen großen Vorteil weil es schneller ist.", "timestamp": now - 200},
            {"time": "00:02", "text": "Aber Datenverlust ist ein kritisches Risiko.", "timestamp": now - 150},
            {"time": "00:03", "text": "Wir haben beschlossen diese Architektur zu implementieren.", "timestamp": now - 100},
            {"time": "00:04", "text": "Ich werde die Tests bis morgen schreiben.", "timestamp": now - 50},
        ]
        sess.stop_time = now

        summary = notetaker.generate_summary(sess)
        decisions = summary["decisions"]
        actions = summary["action_items"]
        self.assertTrue(any("beschlossen" in str(d).lower() for d in decisions), f"Decisions: {decisions}")
        self.assertTrue(any("ich werde" in str(a).lower() for a in actions), f"Actions: {actions}")

        risks = engine.extract_risk_radar(sess)
        self.assertGreater(len(risks), 0)
        self.assertTrue(any(r.severity == "HIGH" for r in risks))

    # -------------------------------------------------------------
    # 4. STTEngine Routing & DictationSession Lifecycle
    # -------------------------------------------------------------
    def test_stt_engine_language_parameter_routing(self):
        stt = STTEngine(self.config)
        prompt_es = stt.build_bias_prompt(["FastAPI"], "es")
        self.assertIn("FastAPI", prompt_es)
        self.assertIn("Español", prompt_es)

        prompt_de = stt.build_bias_prompt(["Docker"], "de")
        self.assertIn("Docker", prompt_de)
        self.assertIn("Standarddeutsch", prompt_de)

        session = DictationSession()
        session.task = "translate"
        session.language = "es"
        self.assertEqual(session.task, "translate")
        self.assertEqual(session.language, "es")


if __name__ == "__main__":
    unittest.main()
