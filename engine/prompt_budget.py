"""
FlowPilot Prompt Budget & Decoder Context Manager (PR 3)
Enforces strict, tokenizer-measured token budgets for Whisper initial_prompt
and hotwords biasing.

Prevents prompt overflow, decoder degradation, and token truncation across
multilingual contexts (especially Indic scripts where UTF-8 byte sequences expand tokens).

Whisper Architecture Constraints:
- Max decoder context: 448 tokens.
- Max prefix conditioning window: 224 tokens.
- Decoder control tokens (SOT, language, task, timestamps): ~8-12 tokens.
- Reserved base language prompt: ~20-50 tokens.
- Safe custom glossary prompt budget: ~120 tokens.
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Any

# Cached tokenizer singleton
_CACHED_TOKENIZER: Optional[Any] = None
_CACHED_TOKENIZER_PATH: Optional[str] = None


def resolve_local_tokenizer_path() -> Optional[Path]:
    """Finds the local tokenizer.json in configured model directories."""
    project_root = Path(__file__).resolve().parent.parent
    candidate_dirs = [
        project_root / "models" / "faster-whisper-base",
        project_root / "models" / "faster-whisper-small",
        project_root / "models" / "base",
        project_root / "models" / "small",
    ]
    for c in candidate_dirs:
        p = c / "tokenizer.json"
        if p.is_file():
            return p
    return None


def get_local_tokenizer() -> Optional[Any]:
    """Loads and caches the Hugging Face Tokenizer from local model files without cloud egress."""
    global _CACHED_TOKENIZER, _CACHED_TOKENIZER_PATH
    if _CACHED_TOKENIZER is not None:
        return _CACHED_TOKENIZER

    path = resolve_local_tokenizer_path()
    if path and path.is_file():
        try:
            from tokenizers import Tokenizer
            _CACHED_TOKENIZER = Tokenizer.from_file(str(path))
            _CACHED_TOKENIZER_PATH = str(path)
            return _CACHED_TOKENIZER
        except Exception as e:
            # Tokenizers library or format error; fallback to conservative estimation
            return None
    return None


def estimate_tokens(text: str, language: Optional[str] = None) -> int:
    """
    UTF-8 byte upper bound for Whisper byte-BPE when no tokenizer is available.
    Deliberately conservative; this is not a measured tokenizer count.
    """
    if not text:
        return 0

    return len(text.encode("utf-8"))


def count_tokens(text: str, tokenizer: Optional[Any] = None, language: Optional[str] = None) -> int:
    """
    Counts exact tokens using local Hugging Face Tokenizer if available,
    falling back to conservative language-aware estimation.
    """
    if not text:
        return 0

    tok = tokenizer or get_local_tokenizer()
    if tok is not None:
        try:
            # Tokenizer.encode returns an Encoding object with .ids
            encoding = tok.encode(text, add_special_tokens=False)
            return len(encoding.ids)
        except Exception:
            pass

    return estimate_tokens(text, language=language)


class PromptBudgetManager:
    """
    Manages prompt token budgets and formats bounded initial_prompt and hotwords strings.
    """

    # Conservative safe defaults preserving room for decoder control tokens
    DEFAULT_GLOSSARY_BUDGET: int = 120
    DEFAULT_MAX_PREFIX_TOKENS: int = 200

    def __init__(self, max_glossary_tokens: int = DEFAULT_GLOSSARY_BUDGET, tokenizer: Optional[Any] = None):
        self.max_glossary_tokens = max_glossary_tokens
        self.tokenizer = tokenizer or get_local_tokenizer()

    def count(self, text: str, language: Optional[str] = None) -> int:
        return count_tokens(text, tokenizer=self.tokenizer, language=language)

    def build_bounded_prompt(
        self,
        language: str,
        base_prompt: str,
        custom_terms: List[str],
        max_total_tokens: Optional[int] = None
    ) -> Tuple[str, int, List[str]]:
        """
        Packs terms within token budget.
        Returns:
            (final_prompt_string, total_token_count, accepted_terms_list)
        """
        budget_limit = self.DEFAULT_MAX_PREFIX_TOKENS if max_total_tokens is None else max(0, max_total_tokens)
        base = (base_prompt or "").strip()
        base_tokens = self.count(base, language=language) if base else 0

        # Never send an oversized base through the guarded path.
        if base_tokens > budget_limit:
            return "", 0, []
        if base_tokens == budget_limit:
            return base, base_tokens, []

        remaining_budget = budget_limit - base_tokens
        glossary_budget = min(remaining_budget, self.max_glossary_tokens)

        accepted_terms: List[str] = []
        if not custom_terms:
            return base, base_tokens, []

        # Greedily pack unique terms
        seen = set()
        for term in custom_terms:
            t = term.strip()
            if not t or t.lower() in seen:
                continue

            test_terms = accepted_terms + [t]
            candidate_glossary = f"Glossary: {', '.join(test_terms)}."
            glossary_tokens = self.count(candidate_glossary, language=language)

            combined = f"{base} {candidate_glossary}".strip()
            if glossary_tokens <= glossary_budget and self.count(combined, language=language) <= budget_limit:
                accepted_terms.append(t)
                seen.add(t.lower())
            else:
                # A shorter later term may still fit.
                continue

        if accepted_terms:
            glossary_str = f"Glossary: {', '.join(accepted_terms)}."
            if base:
                final_prompt = f"{base} {glossary_str}"
            else:
                final_prompt = glossary_str
        else:
            final_prompt = base

        total_tokens = self.count(final_prompt, language=language)
        return final_prompt, total_tokens, accepted_terms

    @staticmethod
    def format_hotwords(terms: List[str], max_terms: int = 30, max_tokens: int = 120,
                       tokenizer: Optional[Any] = None) -> str:
        """
        Formats terms into a clean, comma-separated hotwords string for CTranslate2.
        Avoids duplicate words and bounds term count.
        """
        clean_terms = []
        seen = set()
        for t in terms:
            cleaned = t.strip()
            if (max_terms > 0 and cleaned and cleaned.lower() not in seen and
                    count_tokens(", ".join(clean_terms + [cleaned]), tokenizer=tokenizer) <= max_tokens):
                clean_terms.append(cleaned)
                seen.add(cleaned.lower())
            if len(clean_terms) >= max_terms:
                break
        return ", ".join(clean_terms)
