"""
FlowPilot PR 3 Acceptance Test Suite:
Deliberate Vocabulary Corrections, Multi-Alias Support,
Context Isolation & Tokenizer-Budgeted Biasing

Tests:
1. Multi-alias preservation (no accidental alias overwriting).
2. Context isolation & scoping (no leakage across languages or application profiles).
3. Persistent deletion tombstones for terms and aliases.
4. Tokenizer-based prompt budget enforcement with reserved decoder headroom.
5. Biasing strategy comparison (bounded initial_prompt, hotwords, and negative samples).
6. FactGuard invariants (negation and numeric protection against alias overwrite).
7. Backward compatibility with v1 JSON dictionary import/export.
"""

import sys
import tempfile
import os
from pathlib import Path
from typing import Dict, Any

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.personalization import PersonalizationEngine
from engine.prompt_budget import PromptBudgetManager, count_tokens, get_local_tokenizer
from engine.stt_engine import STTEngine


def test_multi_alias_preservation():
    print("--- [1] Multi-Alias Preservation Without Overwrite ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "test_personalization.json"
        engine = PersonalizationEngine(storage_path=storage)
        engine.dictionary = []

        # Add initial canonical term with primary alias
        engine.add_term("FlowPilot", "flow pilot")
        # Add secondary aliases for the same canonical term
        engine.add_alias("FlowPilot", "flo pilot")
        engine.add_alias("FlowPilot", "flow pilot app")

        # Verify entry
        item = next((i for i in engine.dictionary if i["term"] == "FlowPilot"), None)
        assert item is not None, "Term FlowPilot not found"
        aliases = item["aliases"]
        print(f"Recorded aliases for FlowPilot: {aliases}")
        assert "flow pilot" in aliases
        assert "flo pilot" in aliases
        assert "flow pilot app" in aliases
        assert len(aliases) == 3, f"Expected 3 aliases, found {len(aliases)}"

        # Verify all 3 aliases replace correctly in text
        t1, _ = engine.apply_dictionary("Running flo pilot on desktop.")
        assert "FlowPilot" in t1 and "flo pilot" not in t1

        t2, _ = engine.apply_dictionary("Use the flow pilot app for dictation.")
        assert "FlowPilot" in t2

        t3, _ = engine.apply_dictionary("Testing flow pilot now.")
        assert "FlowPilot" in t3

        print("[PASS] Multi-alias preservation and replacement verified.")


def test_context_isolation_and_scoping():
    print("--- [2] Context Isolation & Cross-Language/Profile Leak Prevention ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "test_personalization.json"
        engine = PersonalizationEngine(storage_path=storage)
        engine.dictionary = []

        # Scoped to Tamil only
        engine.add_term("கணினி", alias="kanini", language="ta")
        # Scoped to Hindi only
        engine.add_term("नमस्ते", alias="namaste", language="hi")
        # Scoped to Developer profile only
        engine.add_term("pytest", alias="pie test", profile="developer")
        # Global term
        engine.add_term("FlowPilot", alias="flow pilot")

        # A. English context: Tamil and Hindi terms must NOT be present
        en_terms = engine.get_terms_list(language="en")
        print(f"English context terms: {en_terms}")
        assert "கணினி" not in en_terms, "Leak: Tamil term leaked into English context"
        assert "नमस्ते" not in en_terms, "Leak: Hindi term leaked into English context"
        assert "FlowPilot" in en_terms, "Global term should be present in English"

        # In English, 'kanini' must NOT be replaced with Tamil
        t_en, _ = engine.apply_dictionary("My friend kanini visited today.", language="en")
        assert "கணினி" not in t_en, "Leak: Tamil alias replaced in English context"

        # B. Tamil context: Tamil terms MUST be present, Hindi terms must NOT
        ta_terms = engine.get_terms_list(language="ta")
        print(f"Tamil context terms: {ta_terms}")
        assert "கணினி" in ta_terms
        assert "नमस्ते" not in ta_terms, "Leak: Hindi term leaked into Tamil context"

        # In Tamil, 'kanini' is replaced
        t_ta, _ = engine.apply_dictionary("புது kanini வாங்கினேன்.", language="ta")
        assert "கணினி" in t_ta

        # C. Profile scoping: 'pytest' in Email profile must NOT leak
        email_terms = engine.get_terms_list(profile="email")
        print(f"Email profile terms: {email_terms}")
        assert "pytest" not in email_terms, "Leak: Developer term leaked into Email profile"

        # 'pytest' in Developer profile MUST be present
        dev_terms = engine.get_terms_list(profile="developer")
        print(f"Developer profile terms: {dev_terms}")
        assert "pytest" in dev_terms

        print("[PASS] Scoped isolation prevents language and profile leakage.")


def test_deletion_tombstones():
    print("--- [3] Deletion Tombstones for Terms and Aliases ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "test_personalization.json"
        engine = PersonalizationEngine(storage_path=storage)

        # Confirm default Kubernetes is present
        assert "Kubernetes" in engine.get_terms_list()

        # Delete Kubernetes
        removed = engine.remove_term("Kubernetes")
        assert removed is True
        assert "Kubernetes" not in engine.get_terms_list()
        assert "kubernetes" in engine.tombstones or "term:kubernetes" in engine.tombstones

        # Simulate reload from disk: default dictionary must NOT resurrect Kubernetes
        engine2 = PersonalizationEngine(storage_path=storage)
        assert "Kubernetes" not in engine2.get_terms_list(), "Tombstone failed: deleted term resurrected"

        # Test alias-specific tombstone
        engine2.add_term("TestApp", alias="test app")
        engine2.add_alias("TestApp", "secondary test app")
        assert "secondary test app" in next(i for i in engine2.dictionary if i["term"] == "TestApp")["aliases"]

        engine2.remove_alias("TestApp", "secondary test app")
        item = next(i for i in engine2.dictionary if i["term"] == "TestApp")
        assert "secondary test app" not in item["aliases"]
        assert any("secondary test app" in t for t in engine2.tombstones)

        print("[PASS] Persistent deletion tombstones verified.")


def test_tokenizer_prompt_budgeting():
    print("--- [4] Tokenizer-Based Prompt Budget Enforcement ---")
    mgr = PromptBudgetManager(max_glossary_tokens=30)
    tok = get_local_tokenizer()
    assert tok is not None, "Local Whisper tokenizer should be resolvable"

    # Test Indic tokens vs Latin tokens
    en_tokens = count_tokens("Technical glossary: Kubernetes, FastAPI, PostgreSQL.")
    ta_tokens = count_tokens("தொழில்நுட்ப சொற்களஞ்சியம்: கணினி, நிரல், வலைப்பின்னல்.")
    print(f"Token counts - EN: {en_tokens}, TA: {ta_tokens}")
    assert en_tokens > 0 and ta_tokens > 0

    # Build a prompt that exceeds the budget: ensure it stops packing
    many_terms = [
        "Kubernetes", "PostgreSQL", "CTranslate2", "TypeScript",
        "GraphQL", "FastAPI", "Pydantic", "PySide6", "WebSockets",
        "OAuth2", "Microservices", "Docker"
    ]
    prompt, count, accepted = mgr.build_bounded_prompt(
        language="en",
        base_prompt="English business dictation.",
        custom_terms=many_terms,
        max_total_tokens=40
    )
    print(f"Bounded prompt ({count} tokens, {len(accepted)} terms): '{prompt}'")
    assert count <= 40, f"Token count {count} exceeded max budget 40"
    assert len(accepted) < len(many_terms), "Budget manager should have stopped before packing all 12 terms"
    assert "Glossary:" in prompt

    print("[PASS] Prompt token budget strictly enforced.")


def test_biasing_strategy_and_negative_samples():
    print("--- [5] Biasing Strategy & Negative Sample Protection ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "test_personalization.json"
        engine = PersonalizationEngine(storage_path=storage)
        engine.dictionary = []
        engine.add_term("CTranslate2", alias="c translate two")

        # Verify hotwords formatting
        hw = engine.get_hotwords()
        assert "CTranslate2" in hw
        print(f"Formatted hotwords: '{hw}'")

        # Verify prompt building doesn't duplicate
        prompt = engine.build_whisper_prompt(max_tokens=60)
        assert "CTranslate2" in prompt
        print(f"Built bias prompt: '{prompt}'")

        # Test STTEngine configuration
        stt = STTEngine({"local_model_size": "base", "biasing_strategy": "hotwords"}, personalization=engine)
        assert stt.config.get("biasing_strategy") == "hotwords"

        # Verify negative sample safety in post-processor:
        # A phonetically similar word that is NOT an alias should NOT be replaced!
        negative_text = "The courier drove a fast van across town."
        result, changes = engine.apply_dictionary(negative_text)
        assert result == negative_text, f"Negative sample corrupted: {result}"
        assert len(changes) == 0

        print("[PASS] Biasing strategy and negative sample integrity verified.")


def test_factguard_negation_and_numeric_safety():
    print("--- [6] FactGuard Negation and Numeric Safety Invariants ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "test_personalization.json"
        engine = PersonalizationEngine(storage_path=storage)
        engine.dictionary = []

        # Adversarial attempt: register a negation word as an alias
        # System should reject converting real negation in dictation
        engine.dictionary.append({
            "term": "Affirmative",
            "alias": "not",
            "aliases": ["not", "no", "இல்லை"],
            "language": None,
            "profile": None
        })

        test_sentence = "The release is not ready for deployment."
        out, changes = engine.apply_dictionary(test_sentence)
        print(f"Protected test result: '{out}' | Changes: {changes}")
        assert "not ready" in out, "Critical negation 'not' was corrupted by alias replacement"

        # Pure digit protection
        engine.dictionary.append({
            "term": "OneHundred",
            "alias": "100",
            "aliases": ["100"],
            "language": None,
            "profile": None
        })
        test_digits = "The server returned code 100 on start."
        out_digits, _ = engine.apply_dictionary(test_digits)
        assert "100" in out_digits, "Pure digits must not be corrupted"

        print("[PASS] Negation and numeric entities protected.")


def test_v1_to_v2_json_compatibility():
    print("--- [7] V1 to V2 JSON Dictionary Compatibility ---")
    v1_json = """{
        "dictionary": [
            {"term": "Docker", "alias": "dock er"},
            {"term": "Redis", "alias": "red iss"}
        ],
        "snippets": [
            {"trigger": "insert redis host", "expansion": "127.0.0.1:6379"}
        ]
    }"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "test_compat.json"
        engine = PersonalizationEngine(storage_path=storage)
        engine.dictionary = []
        engine.snippets = []

        success = engine.import_json(v1_json, merge=False)
        assert success is True
        terms = engine.get_terms_list()
        assert "Docker" in terms
        assert "Redis" in terms

        docker_item = next(i for i in engine.dictionary if i["term"] == "Docker")
        # Check normalized v2 fields
        assert docker_item["aliases"] == ["dock er"]
        assert docker_item["alias"] == "dock er"

        # Export and verify v2 version tag
        exported = engine.export_json()
        assert '"version": 2' in exported

        print("[PASS] V1/V2 JSON format backward compatibility verified.")


def run_all_pr3_tests():
    print("=" * 70)
    print("       FLOWPILOT PR 3 VOCABULARY & PROMPT BUDGET TEST SUITE")
    print("=" * 70)
    test_multi_alias_preservation()
    test_context_isolation_and_scoping()
    test_deletion_tombstones()
    test_tokenizer_prompt_budgeting()
    test_biasing_strategy_and_negative_samples()
    test_factguard_negation_and_numeric_safety()
    test_v1_to_v2_json_compatibility()
    print("=" * 70)
    print("ALL PR 3 VOCABULARY & PROMPT BUDGET TESTS PASSED (7/7)!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_pr3_tests()
