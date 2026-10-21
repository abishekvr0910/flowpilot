import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.personalization import PersonalizationEngine

def test_personalization():
    print("=" * 60)
    print("TEST: PERSONALIZATION ENGINE (DICTIONARY & SNIPPETS)")
    print("=" * 60)

    # Use a temporary file for isolated test execution
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        engine = PersonalizationEngine(storage_path=tmp_path)

        # 1. Test Dictionary Addition & Retrieval
        engine.add_term("FlowPilot", "flow pilot")
        engine.add_term("FastAPI", "fast api")
        engine.add_term("PostgreSQL", "postgres")
        terms = engine.get_terms_list()
        print(f"Dictionary terms: {terms}")
        assert "FlowPilot" in terms
        assert "FastAPI" in terms
        assert "PostgreSQL" in terms

        # 2. Test Alias Replacement & Casing Normalization
        raw_text = "I am using flow pilot with fast api and postgres to build the backend."
        transformed, changes = engine.apply_dictionary(raw_text, language="en", profile="developer")
        print(f"Applied Dictionary:\n  Raw:         '{raw_text}'\n  Transformed: '{transformed}'\n  Changes:     {changes}")
        assert "FlowPilot" in transformed
        assert "FastAPI" in transformed
        assert "PostgreSQL" in transformed

        # 3. Test Case Normalization for mis-cased terms
        raw_miscased = "Check the fastapi docs and flowpilot settings."
        cased_text, cased_changes = engine.apply_dictionary(raw_miscased, language="en", profile="developer")
        print(f"Applied Casing:\n  Raw:         '{raw_miscased}'\n  Transformed: '{cased_text}'")
        assert "FastAPI" in cased_text
        assert "FlowPilot" in cased_text

        # 4. Test Voice Snippet Expansion
        engine.add_snippet("insert my calendly", "https://calendly.com/demo/user")
        spoken_command = "Please schedule a time via insert my calendly so we can talk."
        expanded, trigger = engine.expand_snippets(spoken_command)
        print(f"Snippet Expansion:\n  Spoken:   '{spoken_command}'\n  Expanded: '{expanded}'\n  Trigger:  '{trigger}'")
        assert trigger == "insert my calendly"
        assert "https://calendly.com/demo/user" in expanded

        # 5. Test Whisper Bias Prompt Generation
        whisper_prompt = engine.build_whisper_prompt()
        print(f"Whisper Bias Prompt: '{whisper_prompt}'")
        assert "Glossary:" in whisper_prompt
        assert "FlowPilot" in whisper_prompt

        # 6. Test JSON Export and Import Round-Trip
        json_export = engine.export_json()
        assert len(json_export) > 50

        # Import into fresh engine
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp2:
            tmp2_path = Path(tmp2.name)
        
        try:
            engine2 = PersonalizationEngine(storage_path=tmp2_path)
            success = engine2.import_json(json_export)
            assert success is True
            assert "FlowPilot" in engine2.get_terms_list()
            print("Export / Import round-trip verified.")
        finally:
            if tmp2_path.exists():
                tmp2_path.unlink()

        print("\n[RESULT] PersonalizationEngine tests PASSED.")
        return True

    finally:
        if tmp_path.exists():
            tmp_path.unlink()

if __name__ == "__main__":
    success = test_personalization()
    sys.exit(0 if success else 1)
