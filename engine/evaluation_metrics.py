"""
FlowPilot Multilingual Evaluation Metrics Engine
Provides rigorous, Unicode-aware evaluation metrics for real-voice speech recognition:
- Word Error Rate (WER) with Indic-aware tokenization
- Character Error Rate (CER) with Unicode combining mark preservation
- Critical Fact & Identifier Error Tracking (numbers, currencies, dates, negations, code tokens)
- Formatted Output Quality Scoring against independent desired-writing references
"""

import re
import unicodedata
from collections import Counter
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

# Unicode script ranges for prioritized Indic languages
INDIC_RANGES = {
    "hi": r"[\u0900-\u097F]",  # Devanagari
    "ta": r"[\u0B80-\u0BFF]",  # Tamil
    "ml": r"[\u0D00-\u0D7F]",  # Malayalam
}

# Punctuation stripped from the edges of a token during tokenization.
# Includes the typographic set so that Spanish inverted marks and curly
# quotes do not stay glued to a word.
EDGE_PUNCTUATION = r"[.,!?;:()\[\]{}\"\'«»„“”‘’‚‛¡¿…‹›]"

# Number words that a recogniser may legitimately render as digits.
# Without this normalisation, a reference that spells out "Veintidos" and a
# hypothesis that returns "22" looked like a dropped number plus a
# hallucinated one, which is the same fact expressed twice.
NUMBER_WORDS = {
    "en": {
        "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
        "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
        "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
        "fourteen": "14", "fifteen": "15", "sixteen": "16",
        "seventeen": "17", "eighteen": "18", "nineteen": "19",
        "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
        "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
    },
    "de": {
        "null": "0", "eins": "1", "zwei": "2", "drei": "3", "vier": "4",
        "fünf": "5", "sechs": "6", "sieben": "7", "acht": "8", "neun": "9",
        "zehn": "10", "elf": "11", "zwölf": "12", "dreizehn": "13",
        "vierzehn": "14", "fünfzehn": "15", "sechzehn": "16",
        "siebzehn": "17", "achtzehn": "18", "neunzehn": "19",
        "zwanzig": "20", "dreißig": "30", "vierzig": "40", "fünfzig": "50",
        "sechzig": "60", "siebzig": "70", "achtzig": "80", "neunzig": "90",
    },
    "es": {
        "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3",
        "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7", "ocho": "8",
        "nueve": "9", "diez": "10", "once": "11", "doce": "12",
        "trece": "13", "catorce": "14", "quince": "15", "dieciséis": "16",
        "diecisiete": "17", "dieciocho": "18", "diecinueve": "19",
        "veinte": "20", "veintiuno": "21", "veintidós": "22",
        "veintitrés": "23", "veinticuatro": "24", "veinticinco": "25",
        "veintiséis": "26", "veintisiete": "27", "veintiocho": "28",
        "veintinueve": "29",
        "treinta": "30", "cuarenta": "40", "cincuenta": "50",
        "sesenta": "60", "setenta": "70", "ochenta": "80", "noventa": "90",
    },
    "fr": {
        "zéro": "0", "un": "1", "une": "1", "deux": "2", "trois": "3",
        "quatre": "4", "cinq": "5", "six": "6", "sept": "7", "huit": "8",
        "neuf": "9", "dix": "10", "onze": "11", "douze": "12",
        "treize": "13", "quatorze": "14", "quinze": "15", "seize": "16",
        "dix-sept": "17", "dix-huit": "18", "dix-neuf": "19",
        "vingt": "20", "trente": "30", "quarante": "40", "cinquante": "50",
        "soixante": "60", "septante": "70", "quatre-vingt": "80",
    },
}

# Negation terms across prioritized languages.
#
# de / es / fr were added 2026-10-22. Without them the critical-entity gate
# silently measured nothing for German and French: `extract_critical_entities`
# fell back to the English list only, so a dropped German "nicht" or French
# "pas" was never detected and the fact-retention gate reported a false pass.
#
# French "plus" is deliberately excluded: it is overwhelmingly "more" in
# modern French ("c'est plus grand"), so including it would flag every
# ordinary sentence as carrying a negation.
NEGATION_DICTIONARY = {
    "en": ["not", "no", "never", "none", "neither", "nor", "don't", "doesn't", "didn't", "won't", "cannot", "can't", "without"],
    "hi": ["नहीं", "न", "ना", "मत", "बगैर", "बिना"],
    "ta": ["இல்லை", "அல்ல", "கூடாது", "வேண்டாம்", "இல்லாமல்"],
    "ml": ["ഇല്ല", "അല്ല", "പാടില്ല", "വേണ്ട", "ഇല്ലാതെ"],
    "de": [
        "nicht", "kein", "keine", "keinen", "keinem", "keiner", "keines",
        "nie", "niemals", "nichts", "niemand", "nirgends", "nirgendwo",
        "ohne", "weder",
    ],
    "es": [
        "no", "nunca", "jamás", "jamas", "nadie", "nada",
        "ninguno", "ninguna", "ningún", "ningun", "sin", "tampoco", "ni",
    ],
    "fr": [
        "ne", "pas", "jamais", "rien", "personne", "aucun", "aucune",
        "sans", "ni", "nul", "nulle",
    ],
}


def _number_word_map(language: str) -> Dict[str, str]:
    """Number-word to digit map for a language, tolerating locale codes."""
    lang = (language or "en").lower().replace("_", "-")
    table = NUMBER_WORDS.get(lang)
    if table is None:
        table = NUMBER_WORDS.get(lang.split("-")[0], {})
    return table or {}


def _negation_terms(language: str) -> List[str]:
    """Negation terms for a language, tolerating locale codes like ``de-DE``."""
    lang = (language or "en").lower().replace("_", "-")
    terms = list(NEGATION_DICTIONARY.get(lang, []))
    base = lang.split("-")[0]
    if base != lang:
        terms.extend(NEGATION_DICTIONARY.get(base, []))
    # Preserve order, drop duplicates.
    seen = set()
    ordered = []
    for term in terms:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            ordered.append(term)
    return ordered


def normalize_unicode(text: str, form: str = "NFC") -> str:
    """Normalizes Unicode encoding without stripping native combining diacritics."""
    if not text:
        return ""
    normalized = unicodedata.normalize(form, text)
    # Replace non-breaking spaces and clean whitespace
    normalized = normalized.replace("\u00a0", " ").replace("\ufeff", "")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()

def tokenize_multilingual(text: str, language: str = "en") -> List[str]:
    """
    Tokenizes text into word-level units while:
    1. Preserving Indic combining marks (virama/halant, vowel matras).
    2. Preserving developer tokens (camelCase, snake_case, URLs, CLI flags).
    3. Normalizing punctuation boundaries cleanly.
    """
    if not text:
        return []
    norm = normalize_unicode(text)

    # Clean leading/trailing boundary punctuation while retaining code identifiers and symbols
    # Split by whitespace first
    raw_tokens = norm.split()
    tokens = []

    for t in raw_tokens:
        # Strip outer sentence punctuation like .,!?;:()[]{}""''
        # Includes typographic punctuation: Spanish inverted marks (¡ ¿) and
        # curly quotes („ “ ” ‘ ’) were previously left attached, which
        # silently suppressed critical-entity detection for any sentence
        # starting with an inverted mark or wrapped in curly quotes.
        cleaned = re.sub(r"^" + EDGE_PUNCTUATION + r"+", "", t)
        cleaned = re.sub(EDGE_PUNCTUATION + r"+$", "", cleaned)
        if cleaned:
            # Lowercase Latin characters while preserving Indic codepoints untouched
            tokens.append(cleaned.lower())

    return tokens

def compute_levenshtein(seq1: List[Any], seq2: List[Any]) -> int:
    """Computes standard dynamic-programming Levenshtein edit distance between two sequences."""
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = np.zeros((size_x, size_y), dtype=int)
    for x in range(size_x):
        matrix[x, 0] = x
    for y in range(size_y):
        matrix[0, y] = y

    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x - 1] == seq2[y - 1]:
                matrix[x, y] = matrix[x - 1, y - 1]
            else:
                matrix[x, y] = min(
                    matrix[x - 1, y] + 1,      # deletion
                    matrix[x - 1, y - 1] + 1,  # substitution
                    matrix[x, y - 1] + 1       # insertion
                )
    return int(matrix[size_x - 1, size_y - 1])

def calculate_wer(reference: str, hypothesis: str, language: str = "en") -> float:
    """
    Calculates Word Error Rate (WER) using language-aware tokenization.
    WER = (S + D + I) / N
    """
    ref_tokens = tokenize_multilingual(reference, language=language)
    hyp_tokens = tokenize_multilingual(hypothesis, language=language)

    if not ref_tokens:
        return 0.0 if not hyp_tokens else 1.0

    dist = compute_levenshtein(ref_tokens, hyp_tokens)
    return round(float(dist) / len(ref_tokens), 4)

def calculate_cer(reference: str, hypothesis: str, language: str = "en") -> float:
    """
    Calculates Character Error Rate (CER) with full Unicode awareness.
    Preserves Indic vowel signs, viramas, and diacritics (never strips them).
    """
    ref_norm = normalize_unicode(reference).lower()
    hyp_norm = normalize_unicode(hypothesis).lower()

    # Remove only whitespace characters
    ref_chars = [c for c in ref_norm if not c.isspace()]
    hyp_chars = [c for c in hyp_norm if not c.isspace()]

    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0

    dist = compute_levenshtein(ref_chars, hyp_chars)
    return round(float(dist) / len(ref_chars), 4)

def extract_critical_entities(text: str, language: str = "en") -> Dict[str, List[str]]:
    """Extracts numbers, quantities, dates, negations, and code identifiers from text."""
    norm = normalize_unicode(text)
    
    # 1. Numbers, percentages, currency
    number_pattern = r"(?<!\w)[-+]?[$€£₹]?\d+(?:,\d+)*(?:\.\d+)?(?:%|[kKmMbB](?!\w))?(?!\w)"
    numbers = [m.strip().lower() for m in re.findall(number_pattern, norm) if m.strip() and any(c.isdigit() for c in m)]
    # Spell out a number word the reference may have used so that "Veintidos"
    # and "22" compare equal instead of counting as a loss plus a hallucination.
    number_words = _number_word_map(language)
    if number_words:
        spelled = []
        for token in re.findall(r"\b[\w'’-]+\b", norm.lower()):
            digit = number_words.get(token)
            if digit is not None:
                spelled.append(digit)
        numbers.extend(spelled)

    # 2. Negations across priority languages
    tokens_lower = [t.lower() for t in tokenize_multilingual(norm, language=language)]
    all_negations = _negation_terms(language) + NEGATION_DICTIONARY["en"]
    negations = [t for t in tokens_lower if t in all_negations]

    # 3. Developer tokens (camelCase, snake_case, CLI flags, URLs)
    ident_pattern = r"(?<!\w)(?:--[a-zA-Z0-9][a-zA-Z0-9\-]*(?:=[^\s]+)?|https?://\S+|[a-zA-Z0-9_]+_[a-zA-Z0-9_]+|[a-z]+[A-Z][a-zA-Z0-9]*)(?!\w)"
    identifiers = [m.strip() for m in re.findall(ident_pattern, norm)]

    return {
        "numbers": numbers,
        "negations": negations,
        "identifiers": identifiers
    }

def verify_critical_facts(reference: str, hypothesis: str, language: str = "en") -> Dict[str, Any]:
    """
    Strictly verifies that numbers, quantities, negations, and code tokens from reference
    are preserved in hypothesis. Set membership alone is insufficient.
    """
    ref_ents = extract_critical_entities(reference, language=language)
    hyp_ents = extract_critical_entities(hypothesis, language=language)

    # Exact extracted tokens, including multiplicity and order. This is an
    # entity check, not proof that the sentence's entire meaning is unchanged.
    missing = {key: list((Counter(ref_ents[key]) - Counter(hyp_ents[key])).elements()) for key in ref_ents}
    added = {key: list((Counter(hyp_ents[key]) - Counter(ref_ents[key])).elements()) for key in ref_ents}
    total_entities = sum(map(len, ref_ents.values()))
    hypothesis_entities = sum(map(len, hyp_ents.values()))
    missing_total = sum(map(len, missing.values()))
    preserved_count = max(0, total_entities - missing_total)
    denominator = max(total_entities, hypothesis_entities)
    accuracy = round(preserved_count / denominator, 4) if denominator else 1.0

    return {
        "preserved": ref_ents == hyp_ents,
        "total_critical_entities": total_entities,
        "preserved_count": preserved_count,
        "accuracy": accuracy,
        "missing_numbers": missing["numbers"],
        "missing_negations": missing["negations"],
        "missing_identifiers": missing["identifiers"],
        "added_entities": added,
        "entity_order_changed": any(ref_ents[k] != hyp_ents[k] and not missing[k] and not added[k] for k in ref_ents)
    }

def calculate_formatted_quality_score(desired_reference: str, hypothesis: str, language: str = "en") -> float:
    """
    Evaluates formatted output quality against an independently approved desired-writing reference.
    Quality score = 1.0 - min(1.0, WER(desired_reference, hypothesis)).
    """
    wer = calculate_wer(desired_reference, hypothesis, language=language)
    return round(max(0.0, 1.0 - wer), 4)
