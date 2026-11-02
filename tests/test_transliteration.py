# -*- coding: utf-8 -*-
"""
Tests for FlowPilot Deterministic Phonetic Transliteration Engine
Covers:
- Tamil Unicode independent vowels and ayutha ezhuthu
- Consonants, virama (pulli), and dependent vowel signs
- Nasal + stop voiced clusters (Tolkaappiyam assimilation)
- Geminate doubling
- Code-switching preservation of English ASCII technical tokens
- Colloquial phrases (vanakkam, nandri, eppadi irukkeenga)
- Mode toggling ("tamil" script vs "tanglish" transliteration)
"""

import sys
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
    # Uyir vowels: அ (a), ஆ (aa), இ (i), ஈ (ee), உ (u), ஊ (oo), எ (e), ஏ (ae), ஐ (ai), ஒ (o), ஓ (oa), ஔ (au)
    assert transliterate_tamil_to_tanglish("அம்மா") == "ammaa"
    assert transliterate_tamil_to_tanglish("ஆடு") == "aadu"
    assert transliterate_tamil_to_tanglish("இலை") == "ilai"
    assert transliterate_tamil_to_tanglish("ஈட்டி") == "eetti"
    assert transliterate_tamil_to_tanglish("உண்மை") == "unmai"
    assert transliterate_tamil_to_tanglish("எலி") == "eli"
    assert transliterate_tamil_to_tanglish("ஏணி") == "aeni"
    assert transliterate_tamil_to_tanglish("ஐந்து") == "aindhu"
    assert transliterate_tamil_to_tanglish("ஒன்று") == "ondru"


def test_ayutha_ezhuthu():
    # ஃ (akh)
    assert "akh" in transliterate_tamil_to_tanglish("அஃது")


def test_nasal_stop_voicing():
    # ங்க -> nga (e.g. தங்கம் -> thangam)
    assert transliterate_tamil_to_tanglish("தங்கம்") == "thangam"
    # ஞ்ச -> nja (e.g. பஞ்சு -> panju)
    assert transliterate_tamil_to_tanglish("பஞ்சு") == "panju"
    # ண்ட -> nda (e.g. வண்டு -> vandu)
    assert transliterate_tamil_to_tanglish("வண்டு") == "vandu"
    # ந்த -> ndha (e.g. பந்து -> pandhu)
    assert transliterate_tamil_to_tanglish("பந்து") == "pandhu"
    # ம்ப -> mba (e.g. கம்பு -> kambu)
    assert transliterate_tamil_to_tanglish("கம்பு") == "kambu"
    # ன்ற -> ndra (e.g. நன்றி -> nandri)
    assert transliterate_tamil_to_tanglish("நன்றி") == "nandri"


def test_geminates():
    # க்க -> kka (e.g. அக்கா -> akkaa)
    assert transliterate_tamil_to_tanglish("அக்கா") == "akkaa"
    # ச்ச -> ccha (e.g. பச்சை -> pacchai)
    assert transliterate_tamil_to_tanglish("பச்சை") == "pacchai"
    # ட்ட -> tta (e.g. பட்டம் -> pattam)
    assert transliterate_tamil_to_tanglish("பட்டம்") == "pattam"
    # த்த -> ttha (e.g. பத்து -> patthu)
    assert transliterate_tamil_to_tanglish("பத்து") == "patthu"
    # ப்ப -> ppa (e.g. அப்பா -> appaa)
    assert transliterate_tamil_to_tanglish("அப்பா") == "appaa"


def test_conversational_phrases():
    # வணக்கம் -> vanakkam
    assert transliterate_tamil_to_tanglish("வணக்கம்") == "vanakkam"
    # எப்படி இருக்கீங்க -> eppadi irukkeenga
    res_eppadi = transliterate_tamil_to_tanglish("எப்படி இருக்கீங்க")
    assert "eppadi" in res_eppadi
    assert "irukkeenga" in res_eppadi
    # சரி -> sari
    assert transliterate_tamil_to_tanglish("சரி") == "sari"


def test_code_switching_ascii_preservation():
    # Technical English words, commands, and numbers must remain 100% untouched
    mixed = "தயவுசெய்து Docker container ஐ restart செய்யவும்."
    tanglish = transliterate_tamil_to_tanglish(mixed)
    assert "Docker" in tanglish
    assert "container" in tanglish
    assert "restart" in tanglish
    # Non-Tamil text alone returns unchanged
    assert transliterate_tamil_to_tanglish("git push origin master") == "git push origin master"
    assert transliterate_tamil_to_tanglish("User id is 4092.") == "User id is 4092."


def test_apply_transliteration_modes():
    tamil_text = "வணக்கம் நண்பா"

    # 1. Config set to "tanglish": transforms to Latin phonetics
    cfg_tanglish = {"tamil_script_mode": "tanglish"}
    res_tanglish = apply_transliteration_if_enabled(tamil_text, "ta", cfg_tanglish)
    assert "vanakkam" in res_tanglish
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

    test_nasal_stop_voicing()
    print("✓ Nasal-stop voiced clusters verified (Tolkaappiyam rules).")

    test_geminates()
    print("✓ Consonant geminates doubling verified.")

    test_conversational_phrases()
    print("✓ Common conversational phrases verified (vanakkam, nandri, eppadi irukkeenga).")

    test_code_switching_ascii_preservation()
    print("✓ Code-switching & ASCII technical token preservation verified.")

    test_apply_transliteration_modes()
    print("✓ apply_transliteration_if_enabled dual-mode toggling verified.")

    test_ui_settings_integration()
    print("✓ UI SettingsDialog Tamil Output Format integration verified.")

    print("\n[RESULT] All Transliteration Engine tests PASSED successfully.")


if __name__ == "__main__":
    run_all()
    sys.exit(0)
