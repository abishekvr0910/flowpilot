# -*- coding: utf-8 -*-
"""
Tests for FlowPilot Deterministic Phonetic Transliteration Engine
Covers:
- Tamil Unicode independent vowels and ayutha ezhuthu
- Consonants, virama (pulli), and dependent vowel signs
- Intervocalic plosive softening (Caldwell's Law: adhu, ulladhu, migavum, seydhu)
- Nasal + stop voiced clusters (Tolkaappiyam assimilation: thangam, panju, nandri)
- Geminate doubling (akka, pattam, appa)
- Natural Tanglish vowel mappings (velai, polaam, amma)
- Code-switching preservation of English ASCII technical tokens
- Colloquial spoken phrases (vanakkam, neenga eppadi irukkeenga, romba nallaa irukku)
- Dual-mode toggle ("tamil" script vs "tanglish" transliteration)
- UI SettingsDialog integration
- 50-sentence benchmark corpus 100% pass/fail validation
"""

import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.transliteration import (
    is_tamil_script,
    transliterate_tamil_to_tanglish,
    apply_transliteration_if_enabled,
)


def test_is_tamil_script():
    assert is_tamil_script("வணக்கம்") is True
    assert is_tamil_script("Hello world") is False
    assert is_tamil_script("React மற்றும் Python") is True
    assert is_tamil_script("") is False
    assert is_tamil_script(None) is False
    assert is_tamil_script("12345!@#$") is False


def test_independent_vowels():
    # Uyir vowels
    assert transliterate_tamil_to_tanglish("அம்மா") == "amma"
    assert transliterate_tamil_to_tanglish("ஆடு") == "aadu"
    assert transliterate_tamil_to_tanglish("இலை") == "ilai"
    assert transliterate_tamil_to_tanglish("ஈட்டி") == "eetti"
    assert transliterate_tamil_to_tanglish("உண்மை") == "unmai"
    assert transliterate_tamil_to_tanglish("எலி") == "eli"
    assert transliterate_tamil_to_tanglish("ஏணி") == "eni"
    assert transliterate_tamil_to_tanglish("ஐந்து") == "aindhu"
    assert transliterate_tamil_to_tanglish("ஒன்று") == "ondru"


def test_ayutha_ezhuthu():
    # ஃ (akh)
    assert "akh" in transliterate_tamil_to_tanglish("அஃது")


def test_intervocalic_softening_caldwells_law():
    # க between vowels softens to 'g' (e.g. மிகவும் -> migavum, ஆகும் -> aagum, இனிமையாக -> inimaiyaaga)
    assert transliterate_tamil_to_tanglish("மிகவும்") == "migavum"
    assert transliterate_tamil_to_tanglish("ஆகும்") == "aagum"
    assert "inimaiyaaga" in transliterate_tamil_to_tanglish("இனிமையாக")

    # த between vowels softens to 'dh' (e.g. அது -> adhu, உள்ளது -> ulladhu, செய்து -> seydhu, தேதி -> thedhi)
    assert transliterate_tamil_to_tanglish("அது") == "adhu"
    assert transliterate_tamil_to_tanglish("இது") == "idhu"
    assert transliterate_tamil_to_tanglish("உள்ளது") == "ulladhu"
    assert transliterate_tamil_to_tanglish("செய்து") == "seydhu"
    assert transliterate_tamil_to_tanglish("தேதி") == "thedhi"

    # ட between vowels softens to 'd' (e.g. படம் -> padam, ஆடு -> aadu, வீடு -> veedu)
    assert transliterate_tamil_to_tanglish("படம்") == "padam"
    assert transliterate_tamil_to_tanglish("ஆடு") == "aadu"


def test_natural_tanglish_vowels():
    # Long 'e' (ே) maps to 'e' in natural Tanglish, not archaic 'ae' (வேலை -> velai, நேரம் -> neram)
    assert transliterate_tamil_to_tanglish("வேலை") == "velai"
    assert transliterate_tamil_to_tanglish("நேரம்") == "neram"

    # Long 'o' (ோ) maps to 'o' in natural Tanglish, not archaic 'oa' (போலாம் -> polaam, யோசனை -> yosanai)
    assert transliterate_tamil_to_tanglish("போலாம்") == "polaam"
    assert transliterate_tamil_to_tanglish("யோசனை") == "yosanai"

    # Word-final kinship terms (அம்மா -> amma, அப்பா -> appa, அண்ணா -> anna, அக்கா -> akka)
    assert transliterate_tamil_to_tanglish("அம்மா") == "amma"
    assert transliterate_tamil_to_tanglish("அப்பா") == "appa"
    assert transliterate_tamil_to_tanglish("அண்ணா") == "anna"
    assert transliterate_tamil_to_tanglish("அக்கா") == "akka"


def test_nasal_stop_voicing():
    # ங்க -> nga (e.g. தங்கம் -> thangam)
    assert transliterate_tamil_to_tanglish("தங்கம்") == "thangam"
    # ஞ்ச -> nja (e.g. பஞ்சு -> panju, முடிஞ்சது -> mudinjadhu)
    assert transliterate_tamil_to_tanglish("பஞ்சு") == "panju"
    assert transliterate_tamil_to_tanglish("முடிஞ்சது") == "mudinjadhu"
    # ண்ட -> nda (e.g. வண்டு -> vandu)
    assert transliterate_tamil_to_tanglish("வண்டு") == "vandu"
    # ந்த -> ndha (e.g. பந்து -> pandhu)
    assert transliterate_tamil_to_tanglish("பந்து") == "pandhu"
    # ம்ப -> mba (e.g. கம்பு -> kambu, உடம்புக்கு -> udambukku)
    assert transliterate_tamil_to_tanglish("கம்பு") == "kambu"
    assert transliterate_tamil_to_tanglish("உடம்புக்கு") == "udambukku"
    # ன்ற -> ndra (e.g. நன்றி -> nandri)
    assert transliterate_tamil_to_tanglish("நன்றி") == "nandri"


def test_geminates():
    # க்க -> kk (e.g. அக்கா -> akka)
    assert transliterate_tamil_to_tanglish("அக்கா") == "akka"
    # ச்ச -> ch (e.g. பச்சை -> pachai, பிடிச்சிருக்கு -> pidichirukku)
    assert transliterate_tamil_to_tanglish("பிடிச்சிருக்கு") == "pidichirukku"
    # ட்ட -> tt (e.g. பட்டம் -> pattam, திட்டம் -> thittam)
    assert transliterate_tamil_to_tanglish("பட்டம்") == "pattam"
    assert transliterate_tamil_to_tanglish("திட்டம்") == "thittam"
    # த்த -> tth (e.g. பத்து -> patthu, மொத்தம் -> mottham)
    assert transliterate_tamil_to_tanglish("பத்து") == "patthu"
    assert transliterate_tamil_to_tanglish("மொத்தம்") == "mottham"
    # ப்ப -> pp (e.g. அப்பா -> appa, எப்படி -> eppadi)
    assert transliterate_tamil_to_tanglish("அப்பா") == "appa"
    assert transliterate_tamil_to_tanglish("எப்படி") == "eppadi"


def test_conversational_spoken_phrases():
    # வணக்கம், நீங்க எப்படி இருக்கீங்க? -> vanakkam, neenga eppadi irukkeenga?
    res1 = transliterate_tamil_to_tanglish("வணக்கம், நீங்க எப்படி இருக்கீங்க?")
    assert res1 == "vanakkam, neenga eppadi irukkeenga?"

    # இன்னைக்கு வேலை எல்லாம் நல்லபடியா முடிஞ்சது -> innaikku velai ellaam nallabadiyaa mudinjadhu
    res2 = transliterate_tamil_to_tanglish("இன்னைக்கு வேலை எல்லாம் நல்லபடியா முடிஞ்சது.")
    assert res2 == "innaikku velai ellaam nallabadiyaa mudinjadhu."

    # சரி -> sari
    assert transliterate_tamil_to_tanglish("சரி") == "sari"


def test_code_switching_ascii_preservation():
    # Technical English words, commands, and numbers must remain 100% untouched
    mixed = "புது Docker container build பண்ணி deploy பண்ணுங்க."
    tanglish = transliterate_tamil_to_tanglish(mixed)
    assert "Docker" in tanglish
    assert "container" in tanglish
    assert "build" in tanglish
    assert "deploy" in tanglish
    assert transliterate_tamil_to_tanglish("git push origin master") == "git push origin master"
    assert transliterate_tamil_to_tanglish("User id is 4092.") == "User id is 4092."


def test_apply_transliteration_modes():
    tamil_text = "வணக்கம், நீங்க எப்படி இருக்கீங்க?"

    # 1. Config set to "tanglish": transforms to Latin phonetics
    cfg_tanglish = {"tamil_script_mode": "tanglish"}
    res_tanglish = apply_transliteration_if_enabled(tamil_text, "ta", cfg_tanglish)
    assert "vanakkam, neenga eppadi irukkeenga?" in res_tanglish
    assert not is_tamil_script(res_tanglish)

    # 2. Config set to "tamil": keeps native script untouched
    cfg_tamil = {"tamil_script_mode": "tamil"}
    res_tamil = apply_transliteration_if_enabled(tamil_text, "ta", cfg_tamil)
    assert res_tamil == tamil_text

    # 3. Non-Tamil language: untouched even if mode is tanglish
    cfg_default = {"tamil_script_mode": "tanglish"}
    eng_text = "Hello friend"
    assert apply_transliteration_if_enabled(eng_text, "en", cfg_default) == eng_text


def test_ui_settings_integration():
    """Verify that settings dialog properly initializes combo_tamil_mode and persists config."""
    import os
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    from engine.hotkey_service import Win32HotkeyService

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from ui.settings_dialog import SettingsDialog

    test_config = {
        "language": "ta",
        "tamil_script_mode": "tanglish",
        "hotkey": "Ctrl+Shift+Space",
        "active_tone_mode": "developer",
        "audio_device_index": None,
        "ui_theme": "dark_modern",
        "local_model_size": "base",
    }

    dialog = SettingsDialog(parent=None, config=test_config, on_save=lambda c: True)
    dialog.show()
    try:
        assert hasattr(dialog, "combo_tamil_mode"), "SettingsDialog must have combo_tamil_mode"
        assert hasattr(dialog, "lbl_tamil_mode"), "SettingsDialog must have lbl_tamil_mode"

        # Should be visible for Tamil language
        assert dialog.combo_tamil_mode.isVisible() is True
        # Current data should match config "tanglish"
        assert dialog.combo_tamil_mode.currentData() == "tanglish"

        # Switch to English in combo_lang -> Tamil options should hide
        for i in range(dialog.combo_lang.count()):
            if dialog.combo_lang.itemData(i) == "en":
                dialog.combo_lang.setCurrentIndex(i)
                break
        assert dialog.combo_tamil_mode.isVisible() is False

        # Switch back to Tamil -> Tamil options should re-appear
        for i in range(dialog.combo_lang.count()):
            if dialog.combo_lang.itemData(i) == "ta":
                dialog.combo_lang.setCurrentIndex(i)
                break
        assert dialog.combo_tamil_mode.isVisible() is True

        # Change to "tamil" script and save
        dialog.combo_tamil_mode.setCurrentIndex(0)  # "tamil"
        with patch.object(Win32HotkeyService, "test_hotkey_availability", return_value=(True, "Available")):
            with patch.object(QMessageBox, "information"):
                with patch.object(QMessageBox, "warning"):
                    dialog._save_settings()
        assert dialog.config["tamil_script_mode"] == "tamil"
    finally:
        dialog.close()


def test_english_loanwords_in_tanglish():
    """Verifies that common English loanwords written in Tamil script restore proper English spelling in Tanglish."""
    # Isolated loanwords
    assert transliterate_tamil_to_tanglish("டைம்") == "time"
    assert transliterate_tamil_to_tanglish("மீட்டிங்") == "meeting"
    assert transliterate_tamil_to_tanglish("ஸ்டார்ட்") == "start"
    assert transliterate_tamil_to_tanglish("ப்ராஜெக்ட்") == "project"
    assert transliterate_tamil_to_tanglish("ப்ரோ") == "bro"
    assert transliterate_tamil_to_tanglish("ஆபிஸ்") == "office"
    assert transliterate_tamil_to_tanglish("ரோடு") == "road-u"
    assert transliterate_tamil_to_tanglish("கோட்") == "code"

    # Context-aware disambiguation for கால் (call vs leg/quarter)
    assert transliterate_tamil_to_tanglish("கால் பண்ணுங்க") == "call pannunga"
    assert transliterate_tamil_to_tanglish("கால் பண்றேன்") == "call pandren"
    assert transliterate_tamil_to_tanglish("போன் கால்") == "phone call"
    assert transliterate_tamil_to_tanglish("கால் கிலோ") == "kaal kilo"
    assert transliterate_tamil_to_tanglish("கால் வலிக்குது") == "kaal valikkudhu"
    assert transliterate_tamil_to_tanglish("கால்") == "kaal"

    # Preserving native Tamil words like கோடு (line) vs English கோட் (code)
    assert transliterate_tamil_to_tanglish("ஒரு கோடு போடு") == "oru kodu podu"
    assert transliterate_tamil_to_tanglish("கோட்") == "code"

    # Loanwords with Tamil grammatical suffixes
    assert transliterate_tamil_to_tanglish("டைம்ல") == "time-la"
    assert transliterate_tamil_to_tanglish("கரெக்டான") == "correct-aana"
    assert transliterate_tamil_to_tanglish("மீட்டிங்ல") == "meeting-la"
    assert transliterate_tamil_to_tanglish("ப்ராஜெக்ட்ல") == "project-la"
    assert transliterate_tamil_to_tanglish("லஞ்சுக்கு") == "lunchukku"
    assert transliterate_tamil_to_tanglish("ஆபீஸ்ல") == "office-la"
    assert transliterate_tamil_to_tanglish("ரோட்ல") == "road-la"


def test_full_benchmark_corpus_pass_fail():
    """
    Evaluates transliterate_tamil_to_tanglish against all 50 Tamil items in the benchmark corpus.
    Every sentence must match its reference 100%.
    """
    corpus_file = PROJECT_ROOT / "docs" / "evaluation" / "TAMIL_POLISH_BENCHMARK_CORPUS.json"
    assert corpus_file.exists(), f"Benchmark corpus not found at {corpus_file}"

    with open(corpus_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    ta_items = [it for it in items if it.get("language") == "ta"]
    assert len(ta_items) == 50, f"Expected 50 Tamil items, found {len(ta_items)}"

    failures = []
    for it in ta_items:
        spoken = it["spoken_reference"]
        ref = it.get("tanglish_reference", "")
        gen = transliterate_tamil_to_tanglish(spoken)
        if gen.strip().lower() != ref.strip().lower():
            failures.append((it["item_id"], spoken, gen, ref))

    if failures:
        print(f"\n[FAIL] {len(failures)} corpus items failed transliteration match:")
        for fid, tam, gen, ref in failures:
            print(f"  [{fid}]")
            print(f"    TAM: {tam}")
            print(f"    GEN: {gen}")
            print(f"    REF: {ref}")
        assert len(failures) == 0, f"{len(failures)} Tamil benchmark items failed Tanglish match!"

    print(f"✓ All 50 Tamil benchmark items matched Tanglish references 100% (50/50).")


def run_all():
    print("=" * 60)
    print("TEST: TAMIL & TANGLISH PHONETIC TRANSLITERATION ENGINE")
    print("=" * 60)

    test_is_tamil_script()
    print("✓ is_tamil_script detection verified.")

    test_independent_vowels()
    print("✓ Independent vowels transliteration verified.")

    test_ayutha_ezhuthu()
    print("✓ Ayutha ezhuthu transliteration verified.")

    test_intervocalic_softening_caldwells_law()
    print("✓ Intervocalic plosive softening verified (Caldwell's Law: migavum, adhu, ulladhu).")

    test_natural_tanglish_vowels()
    print("✓ Natural Tanglish vowel mappings verified (velai, polaam, amma).")

    test_nasal_stop_voicing()
    print("✓ Nasal-stop voiced clusters verified (Tolkaappiyam rules).")

    test_geminates()
    print("✓ Consonant geminates doubling verified.")

    test_conversational_spoken_phrases()
    print("✓ Common conversational spoken phrases verified (vanakkam, neenga eppadi irukkeenga).")

    test_code_switching_ascii_preservation()
    print("✓ Code-switching & ASCII technical token preservation verified.")

    test_apply_transliteration_modes()
    print("✓ apply_transliteration_if_enabled dual-mode toggling verified.")

    test_ui_settings_integration()
    print("✓ UI SettingsDialog Tamil Output Format integration verified.")

    test_english_loanwords_in_tanglish()
    print("✓ English loanwords restoration in Tanglish verified (time, call, meeting, lunchukku, project).")

    test_full_benchmark_corpus_pass_fail()
    print("✓ 50-sentence benchmark corpus pass/fail suite PASSED 100%.")

    print("\n[RESULT] All Transliteration Engine tests PASSED successfully.")


if __name__ == "__main__":
    run_all()
    sys.exit(0)
