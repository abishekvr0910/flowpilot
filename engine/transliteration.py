# -*- coding: utf-8 -*-
"""
FlowPilot Deterministic Phonetic Transliteration Engine
Provides:
- Tamil Unicode (U+0B80–U+0BFF) to Tanglish (Latin phonetics) conversion.
- Phonologically grounded rule matching based on Tolkaappiyam & Dravidian phonology:
  * Intervocalic plosive softening (Caldwell's Law: க->g, த->dh, ட->d between vowels).
  * Nasal + stop voiced clusters (ங்க->nga, ஞ்ச->nja, ண்ட->nda, ந்த->ndha, ம்ப->mba, ன்ற->ndra).
  * Geminate doubling (க்க->kka, ச்ச->ch, ட்ட->tta, த்த->ttha, ப்ப->ppa, ற்ற->ttra).
  * Liquid / semi-vowel voicing (ய்த->ydha, ர்க->rga, ர்ப->rba, ழ்ச்ச->zhch).
  * Modern colloquial Tanglish vowel mapping (ே->e, ோ->o, ை->ai, ா->aa/a).
- 100% preservation of embedded English ASCII / code-switching tokens (Docker, Git, React, API, numbers).
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
    '\u0B8F': 'e',     # Tanglish writes 'e' for ஏ (e.g. velai, neram)
    '\u0B90': 'ai',
    '\u0B92': 'o',
    '\u0B93': 'o',     # Tanglish writes 'o' for ஓ (e.g. polaam, yosanai)
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
    '\u0BC7': 'e',     # Tanglish writes 'e' for ே (e.g. velai, neram, thedhi)
    '\u0BC8': 'ai',
    '\u0BCA': 'o',
    '\u0BCB': 'o',     # Tanglish writes 'o' for ோ (e.g. polaam, yosanai, podhu)
    '\u0BCC': 'au',
}

_AYUTHA: Dict[str, str] = {'\u0B83': 'akh'}
_VIRAMA: str = '\u0BCD'  # Pulli dot

# Stems that are complete words or fixed affixes that do not take an inherent 'a'
_FIXED_STEMS = {
    'onbadhu', 'gal', 'rgal', 'ngal', 'badiyaa', 'badiyum',
    'road-u', 'page-a', 'server', 'check', 'budhankizhamai'
}

# High-priority multi-letter patterns and phonological conjuncts
_CONJUNCT_RULES: List[Tuple[str, str]] = [
    # Whole words / fixed morphemes
    ('புதன்கிழமை', 'budhankizhamai'),
    ('ஒன்பது', 'onbadhu'),
    ('பாதிக்க', 'baadhikka'),
    ('செக்', 'check'),
    ('ரோடு', 'road-u'),
    ('பேஜ்ஜ', 'page-a'),
    ('சர்வர்', 'server'),

    # Plural & pronominal affixes
    ('ர்கள்', 'rgal'),        # pronominal plural -ர்கள் -> -rgal
    ('ங்கள்', 'ngal'),        # -ங்கள் -> -ngal
    ('கள்', 'gal'),          # plural suffix -கள் -> -gal

    # Nasal + stop voiced clusters (Tolkaappiyam assimilation)
    ('\u0B99\u0BCD\u0B95', 'ng'),   # ங்க -> nga (e.g. neenga, thangam)
    ('\u0B9E\u0BCD\u0B9A', 'nj'),   # ஞ்ச -> nja (e.g. mudinjadhu, panju)
    ('\u0BA3\u0BCD\u0B9F', 'nd'),   # ண்ட -> nda (e.g. vandu, kondaen)
    ('\u0BA8\u0BCD\u0BA4', 'ndh'),  # ந்த -> ndha (e.g. vandhu, pandhu)
    ('\u0BA9\u0BCD\u0BA4', 'ndh'),  # ன்த -> ndha
    ('\u0BAE\u0BCD\u0BAA', 'mb'),   # ம்ப -> mba (e.g. kambu, kidaikkumbodhu, udambukku)
    ('\u0BA9\u0BCD\u0BB1', 'ndr'),  # ன்ற -> ndra (e.g. nandri, endru)
    ('\u0BA3\u0BCD\u0BB1', 'ndr'),  # ண்ற -> ndra

    # Geminates (doubled plosives and nasals)
    ('\u0B95\u0BCD\u0B95', 'kk'),   # க்க -> kk
    ('\u0B9A\u0BCD\u0B9A', 'ch'),   # ச்ச -> ch (natural Tanglish: pidichirukku, aayiduchu)
    ('\u0B9F\u0BCD\u0B9F', 'tt'),   # ட்ட -> tt
    ('\u0BA4\u0BCD\u0BA4', 'tth'),  # த்த -> tth
    ('\u0BAA\u0BCD\u0BAA', 'pp'),   # ப்ப -> pp
    ('\u0BB1\u0BCD\u0BB1', 'ttr'),  # ற்ற -> ttr
    ('\u0BAE\u0BCD\u0BAE', 'mm'),   # ம்ம -> mm
    ('\u0BA9\u0BCD\u0BA9', 'nn'),   # ன்ன -> nn
    ('\u0BA3\u0BCD\u0BA3', 'nn'),   # ண்ண -> nn
    ('\u0BB2\u0BCD\u0BB2', 'll'),   # ல்ல -> ll
    ('\u0BB3\u0BCD\u0BB3', 'll'),   # ள்ள -> ll
    ('\u0BAF\u0BCD\u0BAF', 'yy'),   # ய்ய -> yy

    # Semi-vowel / liquid coda + plosive voicing
    ('\u0BAF\u0BCD\u0BA4', 'ydh'),  # ய்த -> ydha (seydhu, peydha)
    ('\u0BB0\u0BCD\u0B95', 'rg'),   # ர்க -> rga
    ('\u0BB0\u0BCD\u0BAA', 'rb'),   # ர்ப -> rba (thodarbu)
    ('\u0BB4\u0BCD\u0B9A', 'zhch'), # ழ்ச்ச -> zhch (magizhchi)
    ('\u0BAA\u0BCD\u0BA4\u0BCD\u0BA4\u0BBF', 'ppatthi'), # ப்பத்தி -> ppatthi
    ('\u0BA4\u0BCD\u0BA4\u0BBF', 'tthi'), # த்தி -> tthi
    ('படியா', 'badiyaa'),     # -படியா -> -badiyaa (nallabadiyaa)
    ('படியும்', 'badiyum'),    # -படியும் -> -badiyum (marubadiyum)
]

# Common words with established natural Tanglish spellings
_COMMON_WORDS: Dict[str, str] = {
    'அம்மா': 'amma',
    'அப்பா': 'appa',
    'அண்ணா': 'anna',
    'அக்கா': 'akka',
    'தமிழ்': 'tamil',
    'ஒன்பது': 'onbadhu',
    'நவம்பர்': 'November',
    'ஜனவரி': 'January',
    'டிகிரி': 'degree',
    'செல்சியஸாக': 'Celsius-aaga',
}

# English loanwords frequently used in colloquial spoken Tamil & Tanglish
_LOANWORD_MAP: Dict[str, str] = {
    'டைம்': 'time',
    'கால்': 'call',
    'ஸ்டார்ட்': 'start',
    'ப்ராஜெக்ட்': 'project',
    'பிராஜெக்ட்': 'project',
    'ப்ராஜக்ட்': 'project',
    'கரெக்ட்': 'correct',
    'மீட்டிங்': 'meeting',
    'ப்ரோ': 'bro',
    'லன்ச்': 'lunch',
    'லஞ்ச்': 'lunch',
    'லன்ஞ்சு': 'lunch',
    'லஞ்சு': 'lunch',
    'ரோடு': 'road-u',
    'ரோட்': 'road',
    'போன்': 'phone',
    'மெசேஜ்': 'message',
    'ஹெல்ப்': 'help',
    'ஐடியா': 'idea',
    'காபி': 'kaapi',
    'கப்': 'cup',
    'வீக்கெண்ட்': 'weekend',
    'வீக்எண்ட்': 'weekend',
    'ஆபிஸ்': 'office',
    'ஆபீஸ்': 'office',
    'டீம்': 'team',
    'பிளான்': 'plan',
    'ப்ளான்': 'plan',
    'ப்ராப்ளம்': 'problem',
    'பிராப்ளம்': 'problem',
    'செக்': 'check',
    'அப்டேட்': 'update',
    'லிங்க்': 'link',
    'ஃபைல்': 'file',
    'பைல்': 'file',
    'லாகின்': 'login',
    'லாகவுட்': 'logout',
    'டெஸ்ட்': 'test',
    'கோட்': 'code',
    'கோடு': 'code',
    'சர்வர்': 'server',
    'சிஸ்டம்': 'system',
    'பாஸ்வேர்ட்': 'password',
    'ஸ்கிரீன்': 'screen',
    'ரெடி': 'ready',
    'பிஸி': 'busy',
    'பிசி': 'busy',
    'ஓகே': 'okay',
    'தேங்க்ஸ்': 'thanks',
    'க்ளையன்ட்': 'client',
    'கிளைன்ட்': 'client',
    'மேனேஜர்': 'manager',
    'கம்ப்யூட்டர்': 'computer',
    'லேப்டாப்': 'laptop',
    'மொபைல்': 'mobile',
    'சாஃப்ட்வேர்': 'software',
    'இன்டர்நெட்': 'internet',
    'மெயில்': 'mail',
    'ஈமெயில்': 'email',
    'ஆப்': 'app',
    'யூசர்': 'user',
    'டேட்டா': 'data',
    'டேட்டாபேஸ்': 'database',
    'வெப்சைட்': 'website',
    'சைட்': 'site',
    'ஆன்லைன்': 'online',
    'ஆஃப்லைன்': 'offline',
    'ஸ்கிரிப்ட்': 'script',
    'டவுன்லோட்': 'download',
    'அப்லோட்': 'upload',
    'கிளிக்': 'click',
    'டைப்': 'type',
    'ஓபன்': 'open',
    'குளோஸ்': 'close',
    'டாக்கர்': 'Docker',
    'பைதான்': 'Python',
    'கிட்ஹப்': 'GitHub',
    'கிட்': 'Git',
    'விஸ்பர்': 'Whisper',
    'ரிலீஸ்': 'release',
    'மாடல்': 'model',
}

_LOANWORD_SUFFIXES: List[Tuple[str, str]] = [
    ('க்கு', 'ukku'),
    ('ுக்கு', 'ukku'),
    ('வுக்கு', 'vukku'),
    ('ல', '-la'),
    ('இல்', '-il'),
    ('ல்', '-il'),
    ('ோட', '-oda'),
    ('ஆன', '-aana'),
    ('ான', '-aana'),
    ('ஆ', '-aa'),
]


def _match_loanword(tok: str) -> Optional[str]:
    """Matches Tamil-script English loanwords and returns clean English spelling with suffixes."""
    if tok in _LOANWORD_MAP:
        return _LOANWORD_MAP[tok]
    for sfx_tam, sfx_eng in _LOANWORD_SUFFIXES:
        if tok.endswith(sfx_tam) and len(tok) > len(sfx_tam):
            base = tok[:-len(sfx_tam)]
            if base in _LOANWORD_MAP:
                return _LOANWORD_MAP[base] + sfx_eng
            if (base + _VIRAMA) in _LOANWORD_MAP:
                return _LOANWORD_MAP[base + _VIRAMA] + sfx_eng
            if base.rstrip(_VIRAMA) in _LOANWORD_MAP:
                return _LOANWORD_MAP[base.rstrip(_VIRAMA)] + sfx_eng
    return None

_TAMIL_CHAR_RE = re.compile(r'[\u0B80-\u0BFF]')


def is_tamil_script(text: str) -> bool:
    """Returns True if the text contains any Tamil script Unicode codepoints."""
    if not text:
        return False
    return bool(_TAMIL_CHAR_RE.search(text))


def _transliterate_tamil_word(tok: str) -> str:
    """Transliterates a single Tamil token applying Caldwell's Law allophonic rules."""
    if tok in _COMMON_WORDS:
        return _COMMON_WORDS[tok]
    loan = _match_loanword(tok)
    if loan is not None:
        return loan
    if not any('\u0B80' <= c <= '\u0BFF' for c in tok):
        return tok

    res: List[str] = []
    i = 0
    n = len(tok)
    prev_was_vowel = False

    while i < n:
        c = tok[i]

        # 1. Independent Vowels
        if c in _TAMIL_VOWELS:
            res.append(_TAMIL_VOWELS[c])
            prev_was_vowel = True
            i += 1
            continue

        # 2. Ayutha Ezhuthu
        if c in _AYUTHA:
            res.append(_AYUTHA[c])
            prev_was_vowel = False
            i += 1
            continue

        # 3. Conjunct rules
        matched_conj = False
        for pat, stem in _CONJUNCT_RULES:
            plen = len(pat)
            if tok[i:i+plen] == pat:
                matched_conj = True
                i += plen
                if i < n and tok[i] in _TAMIL_VOWEL_SIGNS:
                    res.append(stem + _TAMIL_VOWEL_SIGNS[tok[i]])
                    prev_was_vowel = True
                    i += 1
                elif i < n and tok[i] == _VIRAMA:
                    res.append(stem)
                    prev_was_vowel = False
                    i += 1
                else:
                    if stem in _FIXED_STEMS or stem.endswith(('a', 'e', 'i', 'o', 'u')):
                        res.append(stem)
                    else:
                        res.append(stem + 'a')
                    prev_was_vowel = True
                break
        if matched_conj:
            continue

        # 4. Consonant Phonology (Intervocalic Softening / Caldwell's Law)
        is_intervocalic = prev_was_vowel
        stem = None

        if c == '\u0B95':  # க -> g between vowels, k initially
            stem = 'g' if is_intervocalic else 'k'
        elif c == '\u0BA4':  # த -> dh between vowels, th initially
            stem = 'dh' if is_intervocalic else 'th'
        elif c == '\u0B9F':  # ட -> d intervocalically
            stem = 'd'
        elif c == '\u0BAA':  # ப -> p
            stem = 'p'
        elif c == '\u0B9A':  # ச -> s
            stem = 's'
        elif c == '\u0B9C':  # ஜ -> j
            stem = 'j'
        elif c == '\u0B9E':  # ஞ -> ny
            stem = 'ny'
        elif c == '\u0B99':  # ங -> ng
            stem = 'ng'
        elif c in ('\u0BA3', '\u0BA8', '\u0BA9'):  # ண, ந, ன -> n
            stem = 'n'
        elif c == '\u0BAE':  # ம -> m
            stem = 'm'
        elif c == '\u0BAF':  # ய -> y
            stem = 'y'
        elif c in ('\u0BB0', '\u0BB1'):  # ர, ற -> r
            stem = 'r'
        elif c in ('\u0BB2', '\u0BB3'):  # ல, ள -> l
            stem = 'l'
        elif c == '\u0BB4':  # ழ -> zh
            stem = 'zh'
        elif c == '\u0BB5':  # வ -> v
            stem = 'v'
        elif c in ('\u0BB6', '\u0BB8'):  # ஶ, ஸ -> s
            stem = 's'
        elif c == '\u0BB7':  # ஷ -> sh
            stem = 'sh'
        elif c == '\u0BB9':  # ஹ -> h
            stem = 'h'

        if stem is not None:
            if i + 1 < n and tok[i+1] == _VIRAMA:
                # Pure consonant with virama (pulli)
                if c == '\u0BA4':
                    res.append('th')
                elif c == '\u0B9F':
                    res.append('t')
                elif c == '\u0B95':
                    res.append('k')
                elif c == '\u0BAA':
                    res.append('p')
                elif c == '\u0BA3':
                    res.append('nn' if (i + 2 == n or (i + 2 < n and tok[i+2] in (' ', '.', ',', '?', '!'))) else 'n')
                else:
                    res.append(stem)
                prev_was_vowel = False
                i += 2
            elif i + 1 < n and tok[i+1] in _TAMIL_VOWEL_SIGNS:
                res.append(stem + _TAMIL_VOWEL_SIGNS[tok[i+1]])
                prev_was_vowel = True
                i += 2
            else:
                res.append(stem + 'a')
                prev_was_vowel = True
                i += 1
            continue

        res.append(c)
        prev_was_vowel = False
        i += 1

    word_str = ''.join(res)
    if word_str.endswith('cchi'):
        word_str = word_str[:-4] + 'chi'
    return word_str


def transliterate_tamil_to_tanglish(text: str) -> str:
    """
    Deterministically transliterates Tamil Unicode script into standard Tanglish (Latin phonetics).
    Applies intervocalic voicing, Tolkaappiyam nasal-stop assimilation, and preserves ASCII / English tokens.
    """
    if not text:
        return ""

    # Handle attached Latin loanword suffixes (e.g. 'lunchக்கு' -> 'lunchukku')
    text = re.sub(r'([A-Za-z]+)க்கு', r'\1ukku', text)

    tokens = re.split(r'(\s+|[.,!?;:"\'()\[\]{}]+)', text)
    out: List[str] = []
    for tok in tokens:
        if not tok:
            continue
        out.append(_transliterate_tamil_word(tok))
    return "".join(out)


def apply_transliteration_if_enabled(text: str, language: Optional[str], config: Dict[str, Any]) -> str:
    """
    Applies script transliteration if configured for the given language.
    For Tamil ('ta'): converts to Tanglish when config 'tamil_script_mode' == 'tanglish'.
    """
    if not text:
        return text

    is_tamil = (language == "ta") or is_tamil_script(text)
    if is_tamil:
        mode = config.get("tamil_script_mode", "tamil")
        if mode == "tanglish":
            return transliterate_tamil_to_tanglish(text)

    return text
