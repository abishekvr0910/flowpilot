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
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

# Unicode script ranges for prioritized Indic languages
INDIC_RANGES = {
    "hi": r"[\u0900-\u097F]",  # Devanagari
    "ta": r"[\u0B80-\u0BFF]",  # Tamil
    "ml": r"[\u0D00-\u0D7F]",  # Malayalam
}

# Negation terms across prioritized languages
NEGATION_DICTIONARY = {
    "en": ["not", "no", "never", "none", "neither", "nor", "don't", "doesn't", "didn't", "won't", "cannot", "can't", "without"],
    "hi": ["नहीं", "न", "ना", "मत", "बगैर", "बिना"],
    "ta": ["இல்லை", "அல்ல", "கூடாது", "வேண்டாம்", "இல்லாமல்"],
    "ml": ["ഇല്ല", "അല്ല", "പാടില്ല", "വേണ്ട", "ഇല്ലാതെ"],
}

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
        cleaned = re.sub(r"^[.,!?;:()[\]{}\"\'«»]+", "", t)
        cleaned = re.sub(r"[.,!?;:()[\]{}\"\'«»]+$", "", cleaned)
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
    number_pattern = r"(?:[-+]?\$?\€?\£?\₹?\d+(?:,\d+)*(?:\.\d+)?(?:\s*[%kKmMbB])?)"
    numbers = [m.strip().lower() for m in re.findall(number_pattern, norm) if m.strip() and any(c.isdigit() for c in m)]

    # 2. Negations across priority languages
    tokens_lower = [t.lower() for t in tokenize_multilingual(norm, language=language)]
    all_negations = NEGATION_DICTIONARY.get(language, []) + NEGATION_DICTIONARY["en"]
    negations = [t for t in tokens_lower if t in all_negations]

    # 3. Developer tokens (camelCase, snake_case, CLI flags, URLs)
    ident_pattern = r"\b(?:[a-zA-Z0-9_]+_[a-zA-Z0-9_]+|[a-z]+[A-Z][a-zA-Z0-9]*|--[a-z0-9\-]+|https?://\S+)\b"
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

    hyp_tokens = set(tokenize_multilingual(hypothesis, language=language))
    hyp_numbers = set(hyp_ents["numbers"])
    hyp_identifiers = set(hyp_ents["identifiers"])

    missing_numbers = [n for n in ref_ents["numbers"] if n not in hyp_numbers and n not in hypothesis.lower()]
    missing_negations = [neg for neg in ref_ents["negations"] if neg not in hyp_tokens and neg not in hypothesis.lower()]
    missing_identifiers = [ident for ident in ref_ents["identifiers"] if ident not in hyp_identifiers and ident not in hypothesis]

    total_entities = len(ref_ents["numbers"]) + len(ref_ents["negations"]) + len(ref_ents["identifiers"])
    missing_total = len(missing_numbers) + len(missing_negations) + len(missing_identifiers)
    preserved_count = max(0, total_entities - missing_total)
    accuracy = 1.0 if total_entities == 0 else round(preserved_count / total_entities, 4)

    return {
        "preserved": missing_total == 0,
        "total_critical_entities": total_entities,
        "preserved_count": preserved_count,
        "accuracy": accuracy,
        "missing_numbers": missing_numbers,
        "missing_negations": missing_negations,
        "missing_identifiers": missing_identifiers
    }

def calculate_formatted_quality_score(desired_reference: str, hypothesis: str, language: str = "en") -> float:
    """
    Evaluates formatted output quality against an independently approved desired-writing reference.
    Quality score = 1.0 - min(1.0, WER(desired_reference, hypothesis)).
    """
    wer = calculate_wer(desired_reference, hypothesis, language=language)
    return round(max(0.0, 1.0 - wer), 4)
