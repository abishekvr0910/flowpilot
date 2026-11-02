# -*- coding: utf-8 -*-
"""
FlowPilot Deterministic Phonetic Transliteration Engine
Provides:
- Tamil Unicode (U+0B80–U+0BFF) to Tanglish (Latin transliteration) conversion.
- Phonologically grounded rule matching (nasal + stop voicing: ங்க->nga, ண்ட->nda, ன்ற->ndra; geminates: க்க->kka, ட்ட->tta, ப்ப->ppa).
- Seamless preservation of embedded English ASCII / code-switching tokens (e.g. Docker, GitHub, API).
"""

import re
from typing import Dict, List, Tuple, Any, Optional

# Independent Uyir Vowels
_TAMIL_VOWELS: Dict[str, str] = {
    '\u0B85': 'a',
    '\u0B86': 'aa',
    '\u0B87': 'i',
    '\u0B88': 'ee',
    '\u0B89': 'u',
    '\u0B8A': 'oo',
    '\u0B8E': 'e',
    '\u0B8F': 'ae',
    '\u0B90': 'ai',
    '\u0B92': 'o',
    '\u0B93': 'oa',
    '\u0B94': 'au',
}

# Dependent Combining Vowel Signs
_TAMIL_VOWEL_SIGNS: Dict[str, str] = {
    '\u0BBE': 'aa',
    '\u0BBF': 'i',
    '\u0BC0': 'ee',
    '\u0BC1': 'u',
    '\u0BC2': 'oo',
    '\u0BC6': 'e',
    '\u0BC7': 'ae',
    '\u0BC8': 'ai',
    '\u0BCA': 'o',
    '\u0BCB': 'oa',
    '\u0BCC': 'au',
}

_AYUTHA: Dict[str, str] = {'\u0B83': 'akh'}
_VIRAMA: str = '\u0BCD'  # Pulli dot

# High-priority multi-character conjuncts and assimilations
_CONJUNCT_RULES: List[Tuple[str, str]] = [
    # Nasal + stop voiced clusters
    ('\u0B99\u0BCD\u0B95', 'ng'),   # ங்க -> nga
    ('\u0B9E\u0BCD\u0B9A', 'nj'),   # ஞ்ச -> nja
    ('\u0BA3\u0BCD\u0B9F', 'nd'),   # ண்ட -> nda
    ('\u0BA8\u0BCD\u0BA4', 'ndh'),  # ந்த -> ndha
    ('\u0BA9\u0BCD\u0BA4', 'ndh'),  # ன்த -> ndha
    ('\u0BAE\u0BCD\u0BAA', 'mb'),   # ம்ப -> mba
    ('\u0BA9\u0BCD\u0BB1', 'ndr'),  # ன்ற -> ndra (e.g. நன்றி -> nandri)
    ('\u0BA3\u0BCD\u0BB1', 'ndr'),  # ண்ற -> ndra

    # Geminates (doubled consonants)
    ('\u0B95\u0BCD\u0B95', 'kk'),   # க்க
    ('\u0B9A\u0BCD\u0B9A', 'cch'),  # ச்ச
    ('\u0B9F\u0BCD\u0B9F', 'tt'),   # ட்ட
    ('\u0BA4\u0BCD\u0BA4', 'tth'),  # த்த
    ('\u0BAA\u0BCD\u0BAA', 'pp'),   # ப்ப
    ('\u0BB1\u0BCD\u0BB1', 'ttr'),  # ற்ற
]

# Base Consonants (stem)
_CONSONANTS: Dict[str, str] = {
    '\u0B95': 'k',
    '\u0B99': 'ng',
    '\u0B9A': 's',
    '\u0B9C': 'j',
    '\u0B9E': 'ny',
    '\u0B9F': 'd',    # Standard Tanglish default for single intervocalic ட is 'd'
    '\u0BA3': 'n',
    '\u0BA4': 'th',
    '\u0BA8': 'n',
    '\u0BA9': 'n',
    '\u0BAA': 'p',
    '\u0BAE': 'm',
    '\u0BAF': 'y',
    '\u0BB0': 'r',
    '\u0BB1': 'r',
    '\u0BB2': 'l',
    '\u0BB3': 'l',
    '\u0BB4': 'zh',
    '\u0BB5': 'v',
    '\u0BB6': 's',
    '\u0BB7': 'sh',
    '\u0BB8': 's',
    '\u0BB9': 'h',
}

_TAMIL_CHAR_RE = re.compile(r'[\u0B80-\u0BFF]')


def is_tamil_script(text: str) -> bool:
    """Returns True if the text contains any Tamil script Unicode codepoints."""
    if not text:
        return False
    return bool(_TAMIL_CHAR_RE.search(text))


def transliterate_tamil_to_tanglish(text: str) -> str:
    """
    Deterministically transliterates Tamil Unicode script into standard Tanglish (Latin phonetics).
    Preserves existing ASCII, English technical tokens, numbers, and punctuation.
    """
    if not text:
        return ""

    result: List[str] = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # 1. Independent vowels
        if ch in _TAMIL_VOWELS:
            result.append(_TAMIL_VOWELS[ch])
            i += 1
            continue

        # 2. Ayutha ezhuthu
        if ch in _AYUTHA:
            result.append(_AYUTHA[ch])
            i += 1
            continue

        # 3. Check for multi-letter conjunct rules
        matched_conjunct = False
        for pattern, stem in _CONJUNCT_RULES:
            pat_len = len(pattern)
            if text[i:i+pat_len] == pattern:
                matched_conjunct = True
                i += pat_len
                if i < n and text[i] in _TAMIL_VOWEL_SIGNS:
                    result.append(stem + _TAMIL_VOWEL_SIGNS[text[i]])
                    i += 1
                elif i < n and text[i] == _VIRAMA:
                    result.append(stem)
                    i += 1
                else:
                    result.append(stem + 'a')
                break
        if matched_conjunct:
            continue

        # 4. Single consonants
        if ch in _CONSONANTS:
            stem = _CONSONANTS[ch]
            if i + 1 < n and text[i + 1] == _VIRAMA:
                # Pure consonant with virama
                if ch == '\u0B9F':
                    result.append('t')
                else:
                    result.append(stem)
                i += 2
            elif i + 1 < n and text[i + 1] in _TAMIL_VOWEL_SIGNS:
                v_val = _TAMIL_VOWEL_SIGNS[text[i + 1]]
                result.append(stem + v_val)
                i += 2
            else:
                result.append(stem + 'a')
                i += 1
            continue

        # 5. Non-Tamil characters (ASCII, Latin words, code tokens, punctuation)
        result.append(ch)
        i += 1

    return "".join(result)


def apply_transliteration_if_enabled(text: str, language: Optional[str], config: Dict[str, Any]) -> str:
    """
    Applies script transliteration if configured for the given language.
    For Tamil ('ta'): converts to Tanglish when config 'tamil_script_mode' == 'tanglish'.
    """
    if not text:
        return text

    # Check if Tamil script is detected or configured
    is_tamil = (language == "ta") or is_tamil_script(text)
    if is_tamil:
        mode = config.get("tamil_script_mode", "tamil")
        if mode == "tanglish":
            return transliterate_tamil_to_tanglish(text)

    return text
