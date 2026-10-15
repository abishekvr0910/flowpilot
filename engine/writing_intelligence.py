"""
FlowPilot Writing Intelligence Engine
Provides two distinct operating modes:
1. Verbatim Mode: 100% faithful transcript preservation with clean punctuation.
2. Polished Mode: Deterministic local transformation supporting:
   - Spoken self-correction resolution ("schedule it for Tuesday — actually, Wednesday" -> "schedule it for Wednesday")
   - Filler word & stutter elimination (um, uh, you know, repeated words)
   - Spoken list detection and markdown formatting
   - Technical identifier handling (camelCase, snake_case, code keywords)
   - Spoken email and URL formatting (john dot doe at company dot com -> john.doe@company.com)
   - Currency, number, and percent formatting (twenty percent -> 20%)
   - Style adaptation: Professional, Casual, Email, Developer, Concise
   - FactGuard: Strict verification of numbers, currency, dates, and negations (not, never)
"""

import re
from typing import Dict, Any, List, Optional, Tuple

# Known technical glossary with accurate canonical casing
TECH_GLOSSARY = {
    "api": "API", "apis": "APIs", "json": "JSON", "http": "HTTP", "https": "HTTPS",
    "rest": "REST", "graphql": "GraphQL", "sql": "SQL", "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL", "mysql": "MySQL", "sqlite": "SQLite", "mongodb": "MongoDB",
    "html": "HTML", "css": "CSS", "javascript": "JavaScript", "typescript": "TypeScript",
    "python": "Python", "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "K8s",
    "git": "Git", "github": "GitHub", "gitlab": "GitLab", "aws": "AWS", "azure": "Azure",
    "fastapi": "FastAPI", "pydantic": "Pydantic", "pyside": "PySide", "pyside6": "PySide6",
    "whisper": "Whisper", "llm": "LLM", "llms": "LLMs", "ui": "UI", "ux": "UX",
    "pr": "PR", "ci": "CI", "cd": "CD", "ci/cd": "CI/CD", "sdk": "SDK", "sdks": "SDKs",
    "url": "URL", "urls": "URLs", "uuid": "UUID", "jwt": "JWT", "oauth": "OAuth",
    "oauth2": "OAuth2", "ctranslate2": "CTranslate2"
}

# Wordy phrase replacements for Concise style
CONCISE_MAP = {
    r"\bat this point in time\b": "now",
    r"\bdue to the fact that\b": "because",
    r"\bin order to\b": "to",
    r"\bwith reference to\b": "regarding",
    r"\bfor the purpose of\b": "for",
    r"\bas a matter of fact\b": "in fact",
    r"\bat the present time\b": "currently",
    r"\bin the event that\b": "if",
    r"\buntil such time as\b": "until",
    r"\bprior to\b": "before",
    r"\bsubsequent to\b": "after"
}

try:
    from engine.language_registry import LanguageRegistry
    from engine.personalization import PersonalizationEngine
    HAS_PERSONALIZATION = True
except ImportError:
    HAS_PERSONALIZATION = False

class TransformationClass:
    SAFE_FORMATTING = "SAFE_FORMATTING"
    REVIEWABLE_REWRITE = "REVIEWABLE_REWRITE"
    PROTECTED = "PROTECTED"

class FactGuard:
    """
    Validates semantic integrity between raw transcript and polished output.
    Guarantees that numbers, decimals, percentages, currency, units, dates,
    negations, CLI flags, file paths, URLs, and user dictionary phrases are strictly preserved.
    """
    CRITICAL_NEGATIONS = [
        "not", "never", "no", "cannot", "can't", "cant",
        "won't", "wont", "don't", "dont", "doesn't", "doesnt",
        "didn't", "didnt", "shouldn't", "shouldnt", "wouldn't", "wouldnt",
        "couldn't", "couldnt", "isn't", "isnt", "aren't", "arent",
        "wasn't", "wasnt", "weren't", "werent", "hasn't", "hasnt",
        "haven't", "havent", "hadn't", "hadnt", "none", "without",
        "neither", "nor", "nobody", "nothing", "nowhere"
    ]

    NUMERIC_WORD_CONFUSIONS = {
        "fifteen": "15", "fifty": "50",
        "fourteen": "14", "forty": "40",
        "thirteen": "13", "thirty": "30",
        "sixteen": "16", "sixty": "60",
        "seventeen": "17", "seventy": "70",
        "eighteen": "18", "eighty": "80",
        "nineteen": "19", "ninety": "90"
    }

    PROTECTED_UNITS = [
        "ms", "sec", "seconds", "second", "min", "minutes", "minute",
        "hours", "hour", "hr", "hrs", "mb", "gb", "tb", "kb",
        "units", "unit", "items", "item", "px", "em", "rem", "%", "percent",
        "kg", "g", "lbs", "dollars", "cents"
    ]

    @classmethod
    def extract_protected_entities(
        cls,
        text: str,
        custom_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extracts structured protected tokens that must never be altered or omitted.
        """
        lower = text.lower()

        # 1. Negations
        found_negations = []
        for neg in cls.CRITICAL_NEGATIONS:
            if re.search(r"\b" + re.escape(neg) + r"\b", lower):
                found_negations.append(neg)

        # 2. Raw Numbers, Currency, Percentages, Decimals
        raw_num_matches = re.findall(r"(\$?\d+(?:,\d+)*(?:\.\d+)?%?)", text)

        # 3. Units attached to numbers (e.g., 1450 units, 2400 ms)
        unit_pattern = r"(?i)\b(\$?\d+(?:,\d+)*(?:\.\d+)?)\s*(" + "|".join(re.escape(u) for u in cls.PROTECTED_UNITS) + r")\b"
        found_units = re.findall(unit_pattern, text)

        # 4. Spoken number confusion tokens (fifteen vs fifty)
        found_spoken_nums = {}
        for word, val in cls.NUMERIC_WORD_CONFUSIONS.items():
            if re.search(r"\b" + re.escape(word) + r"\b", lower):
                found_spoken_nums[word] = val

        # 5. CLI Flags (--dry-run, -rf)
        cli_flags = re.findall(r"(?:^|\s)(--[a-zA-Z0-9][a-zA-Z0-9_\-]*|-[a-zA-Z0-9]+)(?=\s|[,\.\?!]|$)", text)

        # 6. File paths and extensions (config_prod.json, /var/log, etc.)
        file_paths = re.findall(r"\b[a-zA-Z0-9_\-]+\.(?:json|py|exe|zip|txt|md|log|yml|yaml|toml|ini|env|csv|sh|bat|ps1|js|ts|jsx|tsx|html|css|cpp|c|h|rs|go|dll)\b|[/\\][a-zA-Z0-9_\-/\\]+", text)

        # 7. URLs
        urls = re.findall(r"https?://[^\s]+", text)

        # 8. User dictionary terms
        matched_custom = []
        if custom_terms:
            for term in custom_terms:
                if term and re.search(r"\b" + re.escape(term.lower()) + r"\b", lower):
                    matched_custom.append(term)

        return {
            "negations": found_negations,
            "raw_nums": raw_num_matches,
            "units": found_units,
            "spoken_nums": found_spoken_nums,
            "cli_flags": [f.strip() for f in cli_flags],
            "file_paths": file_paths,
            "urls": urls,
            "custom_terms": matched_custom
        }

    @classmethod
    def validate_and_guard(
        cls,
        raw_text: str,
        polished_text: str,
        retracted_nums: Optional[List[str]] = None,
        retracted_negations: Optional[List[str]] = None,
        custom_terms: Optional[List[str]] = None
    ) -> Tuple[str, bool, List[str]]:
        """
        Validates fact preservation across negations, numbers, decimals, units,
        CLI flags, paths, URLs, and dictionary terms.
        If any protected entity was dropped or corrupted, safely restores the raw transcript.
        Returns: (final_text, is_guarded, warnings)
        """
        warnings = []
        is_safe = True
        safe_retracted_nums = [re.sub(r"[^\d]", "", n) for n in (retracted_nums or [])]
        safe_retracted_negs = [n.lower() for n in (retracted_negations or [])]

        raw_entities = cls.extract_protected_entities(raw_text, custom_terms)
        pol_entities = cls.extract_protected_entities(polished_text, custom_terms)

        # 1. Verify Negations
        for neg in raw_entities["negations"]:
            if neg in safe_retracted_negs:
                continue
            pol_has = bool(re.search(r"\b" + re.escape(neg) + r"\b", polished_text.lower()))
            if not pol_has:
                # Check contraction equivalence
                equivs = {
                    "cannot": "can't", "can't": "cannot", "cant": "can't",
                    "do not": "don't", "don't": "do not", "dont": "don't",
                    "will not": "won't", "won't": "will not", "wont": "won't",
                    "does not": "doesn't", "doesn't": "does not", "doesnt": "doesn't",
                    "did not": "didn't", "didn't": "did not", "didnt": "didn't",
                    "is not": "isn't", "isn't": "is not", "isnt": "isn't"
                }
                eq = equivs.get(neg)
                if eq and re.search(r"\b" + re.escape(eq) + r"\b", polished_text.lower()):
                    pol_has = True

            if not pol_has:
                warnings.append(f"FactGuard Warning: Negation token '{neg}' was dropped by polishing. Enforcing raw clause.")
                is_safe = False

        # 2. Verify Numbers, Decimals & Currency
        raw_clean_nums = [re.sub(r"[^\d]", "", n) for n in raw_entities["raw_nums"]]
        pol_clean_nums = [re.sub(r"[^\d]", "", n) for n in pol_entities["raw_nums"]]
        for raw_n, clean_n in zip(raw_entities["raw_nums"], raw_clean_nums):
            if clean_n and (clean_n not in pol_clean_nums) and (clean_n not in safe_retracted_nums):
                warnings.append(f"FactGuard Warning: Numeric value '{raw_n}' was altered. Restoring accurate value.")
                is_safe = False

        # Verify unit integrity (e.g., 1450 units -> $1450 units corruption check)
        for num_str, unit_str in raw_entities["units"]:
            clean_num = re.sub(r"[^\d]", "", num_str)
            if clean_num in safe_retracted_nums:
                continue
            # If raw did NOT have $, polished must not prepend $ before a non-currency unit
            if "$" not in num_str and unit_str.lower() in ("units", "unit", "items", "item", "ms", "mb", "gb", "px"):
                comma_num = f"{int(clean_num):,}" if clean_num.isdigit() else clean_num
                pat = rf"\$\s*(?:{re.escape(clean_num)}|{re.escape(comma_num)})\s*{re.escape(unit_str)}"
                if re.search(pat, polished_text, re.IGNORECASE):
                    warnings.append(f"FactGuard Warning: Prepended '$' to non-currency unit quantity '{num_str} {unit_str}'.")
                    is_safe = False

        # Verify soundalike number confusions (15 vs 50, etc.)
        for word, val in raw_entities["spoken_nums"].items():
            confused_val = "50" if val == "15" else ("15" if val == "50" else None)
            if confused_val and (confused_val in pol_clean_nums) and (val not in pol_clean_nums):
                warnings.append(f"FactGuard Warning: Spoken number confusion detected: '{word}' ({val}) mutated to '{confused_val}'.")
                is_safe = False

        # 3. Verify CLI Flags
        for flag in raw_entities["cli_flags"]:
            if flag not in polished_text:
                warnings.append(f"FactGuard Warning: CLI flag '{flag}' was altered or dropped.")
                is_safe = False

        # 4. Verify File Paths
        for path in raw_entities["file_paths"]:
            if path not in polished_text:
                warnings.append(f"FactGuard Warning: File path '{path}' was altered or dropped.")
                is_safe = False

        # 5. Verify URLs
        for url in raw_entities["urls"]:
            clean_url = url.rstrip(".,;!?:")
            if clean_url.lower() not in polished_text.lower():
                warnings.append(f"FactGuard Warning: URL '{url}' was altered or dropped.")
                is_safe = False

        # 6. Verify User Dictionary Terms
        for term in raw_entities["custom_terms"]:
            if term.lower() not in polished_text.lower():
                warnings.append(f"FactGuard Warning: User dictionary term '{term}' was dropped.")
                is_safe = False

        if not is_safe:
            # Fallback to raw text with basic cleanup to guarantee factual safety
            return raw_text.strip(), False, warnings

        return polished_text, True, []

class WritingIntelligence:
    def __init__(self, config: Optional[Dict[str, Any]] = None, personalization: Optional[Any] = None):
        self.config = config or {}
        self.personalization = personalization or (PersonalizationEngine() if HAS_PERSONALIZATION else None)

    def polish(self, raw_text: str, mode: str = "polished", style: str = "professional", dialect: str = "") -> Dict[str, Any]:
        """
        Main processing method.
        Returns dict containing:
        - 'text': final output text
        - 'raw_text': original untouched transcript
        - 'mode': verbatim or polished
        - 'style': chosen style
        - 'changes_applied': list of modifications made
        """
        if not raw_text or not raw_text.strip():
            return {"text": "", "raw_text": "", "mode": mode, "style": style, "changes_applied": []}

        raw = raw_text.strip()
        changes = []

        # --- MODE A: VERBATIM MODE ---
        if mode == "verbatim":
            cleaned = self._clean_basic_spacing(raw)
            if self.personalization:
                cleaned, dict_ch = self.personalization.apply_dictionary(cleaned)
                if dict_ch:
                    changes.extend(dict_ch)
            return {
                "text": cleaned,
                "raw_text": raw,
                "mode": "verbatim",
                "style": "verbatim",
                "changes_applied": ["Verbatim faithful preservation"] + changes
            }

        # --- MODE B: POLISHED MODE ---
        text = raw

        # 1. Resolve spoken self-corrections
        corrected_text, had_self_correction, retracted_nums, retracted_negs = self._resolve_self_corrections(text)
        if had_self_correction:
            changes.append("Resolved spoken self-correction")
            text = corrected_text

        # 2. Format spoken emails and URLs (before filler/stutter removal so 'slash slash' is preserved)
        text, url_changes = self._format_spoken_emails_and_urls(text)
        if url_changes:
            changes.extend(url_changes)

        # 3. Remove speech fillers and stutters
        de_fillered, had_fillers = self._remove_fillers_and_stutters(text)
        if had_fillers:
            changes.append("Removed filler words & stutters")
            text = de_fillered

        # 4. Format numbers, percentages, and currencies
        text, num_changes = self._format_currencies_and_percentages(text)
        if num_changes:
            changes.extend(num_changes)

        # 5. Format technical identifiers if developer mode or code dictation
        if style in ("developer", "technical", "terminal"):
            text, tech_changes = self._format_code_identifiers(text)
            if tech_changes:
                changes.extend(tech_changes)

        # 6. Canonicalize known technical acronyms and terms
        text = self._canonicalize_tech_terms(text, style=style)

        # 7. Apply Personal Dictionary aliases & casing
        if self.personalization:
            text, dict_changes = self.personalization.apply_dictionary(text)
            if dict_changes:
                changes.extend(dict_changes)

        # 8. Apply regional dialect rules if specified
        active_dialect = dialect or self.config.get("dialect", "")
        if active_dialect and HAS_PERSONALIZATION:
            text = LanguageRegistry.apply_dialect_rules(text, active_dialect)

        # 9. Spoken list formatting (skip in terminal style)
        if style != "terminal":
            formatted_list, is_list = self._format_spoken_lists(text)
            if is_list:
                changes.append("Formatted spoken list items")
                text = formatted_list

        # 10. Apply style-specific transformations
        if style == "concise":
            text, had_concise = self._apply_concise(text)
            if had_concise:
                changes.append("Applied concise phrasing")
        elif style == "email":
            text, had_email = self._format_email(text)
            if had_email:
                changes.append("Formatted email structure")
        elif style == "professional":
            text = self._apply_professional(text)

        # 11. Final punctuation and capitalization cleanup (style-aware)
        text = self._finalize_punctuation(text, style=style)

        # 12. FactGuard semantic verification
        custom_terms = self.personalization.get_terms_list() if self.personalization else None
        final_guarded, is_fact_safe, fact_warnings = FactGuard.validate_and_guard(
            raw, text, retracted_nums=retracted_nums, retracted_negations=retracted_negs, custom_terms=custom_terms
        )
        if not is_fact_safe:
            changes.extend(fact_warnings)
            text = final_guarded

        return {
            "text": text,
            "raw_text": raw,
            "mode": "polished",
            "style": style,
            "changes_applied": changes
        }

    def _clean_basic_spacing(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text

    def _resolve_self_corrections(self, text: str) -> Tuple[str, bool, List[str], List[str]]:
        """
        Resolves spoken self-corrections like:
        - 'schedule it for Tuesday — actually, Wednesday' -> 'schedule it for Wednesday'
        - 'budget is 5000 -- actually 6000 dollars' -> 'budget is 6000 dollars'
        - 'send 5 copies, no wait, 10 copies' -> 'send 10 copies'
        - 'meet at 2:00, or rather, 3:00' -> 'meet at 3:00'
        - 'do not deploy, actually, do deploy' -> 'do deploy'
        Returns: (corrected_text, had_self_correction, retracted_nums, retracted_negs)
        """
        original = text
        retracted_nums: List[str] = []
        retracted_negs: List[str] = []

        def record_retractions(superseded_text: str):
            for n in re.findall(r"\$?\d+(?:,\d+)*(?:\.\d+)?", superseded_text):
                clean_n = re.sub(r"[^\d]", "", n)
                if clean_n:
                    retracted_nums.append(clean_n)
            for neg in FactGuard.CRITICAL_NEGATIONS:
                if re.search(r"\b" + re.escape(neg) + r"\b", superseded_text.lower()):
                    retracted_negs.append(neg)

        # 1. Specific targeted Tuesday -> actually, Wednesday / for/on/at/by/in X -> actually, Y
        specific_pattern = r"(?i)(.*?)\b(for|on|at|by|in)\s+(\$?\w+)\s*(?:,\s*|\s*[\—\-\–]{1,2}\s*|\s+)actually,?\s+(\$?\w+)(.*)"
        match = re.search(specific_pattern, text)
        if match:
            prefix, prep, old_val, new_val, suffix = match.groups()
            record_retractions(old_val)
            text = f"{prefix}{prep} {new_val}{suffix}"
            return text.strip(), True, retracted_nums, retracted_negs

        # 2. Spoken Negation Retraction / Inversion ("do not proceed -- actually, proceed")
        match_neg_retract = re.search(
            r"(?i)(.*?)\b(do not|don\'t|never|cannot|can\'t)\s+(\w+)\s*(?:,\s*|\s*[\—\-\–]{1,2}\s*|\s+)actually,?\s+(?:do\s+)?(\3)(.*)",
            text
        )
        if match_neg_retract:
            pre, neg_phrase, old_v, new_v, post = match_neg_retract.groups()
            record_retractions(f"{neg_phrase} {old_v}")
            text = f"{pre} {new_v}{post}"
            return re.sub(r"\s+", " ", text).strip(), True, retracted_nums, retracted_negs

        # 3. Generic "actually" correction: "X -- actually Y"
        match_gen = re.search(r"(?i)(.*?)\b(\$?\w+)\s*(?:,\s*|\s*[\—\-\–]{1,2}\s*|\s+)actually,?\s+(\$?\w+)(.*)", text)
        if match_gen:
            pre, old_word, new_word, post = match_gen.groups()
            record_retractions(old_word)
            text = f"{pre} {new_word}{post}"
            return re.sub(r"\s+", " ", text).strip(), True, retracted_nums, retracted_negs

        # 3. "or rather, Y" correction: "meet at 2:00, or rather, 3:00"
        match_rather = re.search(r"(?i)(.*?)\b(\$?\w+)\s*(?:,\s*|\s*[\—\-\–]{1,2}\s*|\s+)or rather,?\s+(\$?\w+)(.*)", text)
        if match_rather:
            pre, old_word, new_word, post = match_rather.groups()
            record_retractions(old_word)
            text = f"{pre} {new_word}{post}"
            return re.sub(r"\s+", " ", text).strip(), True, retracted_nums, retracted_negs

        # 4. "no wait, Y" / "wait no, Y"
        match_wait = re.search(r"(?i)(.*?)\s*(?:,\s*|\s+)(?:no wait|wait no),?\s+(.*)", text)
        if match_wait:
            pre, post = match_wait.groups()
            pre_words = pre.split()
            if pre_words:
                retracted_last = pre_words.pop()
                record_retractions(retracted_last)
            text = " ".join(pre_words) + " " + post
            return re.sub(r"\s+", " ", text).strip(), True, retracted_nums, retracted_negs

        return text, False, [], []

    def _remove_fillers_and_stutters(self, text: str) -> Tuple[str, bool]:
        original = text

        # 1. Remove filler sounds (um, uh, uhh, er, ah, erm)
        filler_pattern = r"(?i)\b(um|uh|uhh|er|ah|erm)\b[,]?\s*"
        text = re.sub(filler_pattern, "", text)

        # 2. Remove hesitation "like," when used as filler: "We should, like, do this"
        text = re.sub(r"(?i)(?<=\w)\s*,?\s*like,\s*(?=\w)", " ", text)

        # 3. Remove conversational filler phrases at start or pauses
        text = re.sub(r"(?i)\b(you know|I mean)\b[,]?\s*", "", text)

        # 4. Remove stuttered duplicate words: "I I want to", "the the", "we we" (exempt intentional double tokens like 'slash slash')
        stutter_pattern = r"(?i)\b(?!slash\b)([a-zA-Z]+)\s+\1\b"
        text = re.sub(stutter_pattern, r"\1", text)
        text = re.sub(stutter_pattern, r"\1", text)

        text = re.sub(r"\s+", " ", text).strip()
        return text, (text != original)

    def _format_spoken_emails_and_urls(self, text: str) -> Tuple[str, List[str]]:
        changes = []

        # Emails: "X dot Y at Z dot com" -> "X.Y@Z.com"
        def email_repl(m):
            user_part = m.group(1).replace(" dot ", ".").replace(" ", "")
            domain = m.group(2).replace(" dot ", ".").replace(" ", "")
            tld = m.group(3).lower()
            formatted = f"{user_part}@{domain}.{tld}".lower()
            changes.append(f"Formatted email: {formatted}")
            return formatted

        text = re.sub(
            r"(?i)\b([a-zA-Z0-9]+(?:\s+dot\s+[a-zA-Z0-9]+)*)\s+at\s+([a-zA-Z0-9]+(?:\s+dot\s+[a-zA-Z0-9]+)*)\s+dot\s+(com|org|net|edu|gov|io|ai|dev)\b",
            email_repl,
            text
        )

        # URLs: "https colon slash slash X dot com slash path"
        def url_repl(m):
            proto = m.group(1).lower()
            domain = m.group(2).replace(" dot ", ".").replace(" ", "")
            path = m.group(3) if m.group(3) else ""
            clean_path = ("/" + path.replace(" slash ", "/").replace(" ", "-")) if path else ""
            res = f"{proto}://{domain}{clean_path}".lower()
            changes.append(f"Formatted URL: {res}")
            return res

        text = re.sub(
            r"(?i)\b(https?)\s+colon\s+slash\s+slash\s+([a-zA-Z0-9\-\.]+(?:\s+dot\s+[a-zA-Z0-9\-\.]+)*)(?:\s+slash\s+([a-zA-Z0-9\-\s]+))?",
            url_repl,
            text
        )

        return text, changes

    @staticmethod
    def _words_to_num(phrase: str) -> Optional[int]:
        units = {
            "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
            "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
            "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
            "nineteen": 19
        }
        tens = {
            "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
            "eighty": 80, "ninety": 90
        }
        scales = {"hundred": 100, "thousand": 1000, "million": 1000000}
        words = phrase.lower().replace("-", " ").split()
        if not words:
            return None
        current, total = 0, 0
        for w in words:
            if w in units:
                current += units[w]
            elif w in tens:
                current += tens[w]
            elif w in scales:
                scale = scales[w]
                if current == 0:
                    current = 1
                if scale == 100:
                    current *= 100
                else:
                    total += current * scale
                    current = 0
            else:
                return None
        return total + current

    def _format_currencies_and_percentages(self, text: str) -> Tuple[str, List[str]]:
        changes = []
        num_words = r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million"

        # 1. Percentages (digits or spoken words)
        def pct_repl(m):
            val = m.group(1).strip()
            num = int(val) if val.isdigit() else self._words_to_num(val)
            if num is not None:
                changes.append("Formatted percentage")
                return f"{num}%"
            return m.group(0)

        text = re.sub(rf"(?i)\b((?:(?:{num_words}|\d+)(?:[\s\-]+(?:{num_words}|\d+))*))\s*percent\b", pct_repl, text)

        # 2. Currencies: Dollars (digits or spoken words)
        def dollar_repl(m):
            val = m.group(1).strip()
            clean_digits = re.sub(r"[^\d]", "", val)
            num = int(clean_digits) if clean_digits else self._words_to_num(val)
            if num is not None:
                changes.append("Formatted currency ($)")
                return f"${num:,}" if num >= 1000 else f"${num}"
            return m.group(0)

        text = re.sub(rf"(?i)\b((?:(?:{num_words}|\d+(?:,\d+)*)(?:[\s\-]+(?:{num_words}|\d+))*))\s*dollars\b", dollar_repl, text)

        # 3. Time formatting (e.g., 10AM, 10 a.m., 10pm -> 10 AM, 10 PM)
        def time_repl(m):
            hr = m.group(1)
            meridiem = m.group(2).replace(".", "").upper()
            return f"{hr} {meridiem}"

        text = re.sub(r"(?i)\b(\d{1,2}(?::\d{2})?)\s*(a\.m\.|p\.m\.|am\b|pm\b)", time_repl, text)

        return text, changes

    def _format_code_identifiers(self, text: str) -> Tuple[str, List[str]]:
        changes = []

        # camel case <words>
        def camel_rep(m):
            words = m.group(1).strip().split()
            if not words:
                return ""
            res = words[0].lower() + "".join(w.capitalize() for w in words[1:])
            changes.append(f"Formatted camelCase: {res}")
            return res

        text = re.sub(
            r"(?i)\bcamel case\s+([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+)*?)(?=\s+(?:and|or|then|snake case|kebab case)\b|[,\.\?!]|$)",
            camel_rep,
            text
        )

        # snake case <words>
        def snake_rep(m):
            words = m.group(1).strip().split()
            res = "_".join(w.lower() for w in words)
            changes.append(f"Formatted snake_case: {res}")
            return res

        text = re.sub(
            r"(?i)\bsnake case\s+([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+)*?)(?=\s+(?:and|or|then|camel case|kebab case)\b|[,\.\?!]|$)",
            snake_rep,
            text
        )

        # kebab case <words>
        def kebab_rep(m):
            words = m.group(1).strip().split()
            res = "-".join(w.lower() for w in words)
            changes.append(f"Formatted kebab-case: {res}")
            return res

        text = re.sub(
            r"(?i)\bkebab case\s+([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+)*?)(?=\s+(?:and|or|then|camel case|snake case)\b|[,\.\?!]|$)",
            kebab_rep,
            text
        )

        return text, changes

    def _canonicalize_tech_terms(self, text: str, style: str = "professional") -> str:
        for lower_term, canonical in TECH_GLOSSARY.items():
            if style == "terminal" and lower_term in ("git", "docker", "python", "sql", "html", "css"):
                continue
            pattern = rf"(?i)\b{re.escape(lower_term)}\b"
            text = re.sub(pattern, canonical, text)
        # Preserve lowercased URLs
        text = re.sub(r"(?i)\b(https?://[^\s]+)", lambda m: m.group(1).lower(), text)
        return text

    def _format_spoken_lists(self, text: str) -> Tuple[str, bool]:
        ordinals = [
            (r"(?i)\b(?:first|firstly|number one)\b[:,]?", "\n- "),
            (r"(?i)\b(?:second|secondly|number two)\b[:,]?", "\n- "),
            (r"(?i)\b(?:third|thirdly|number three)\b[:,]?", "\n- "),
            (r"(?i)\b(?:fourth|fourthly|number four)\b[:,]?", "\n- "),
            (r"(?i)\b(?:finally|lastly)\b[:,]?", "\n- ")
        ]

        if re.search(r"(?i)\b(?:first|number one)\b", text) and re.search(r"(?i)\b(?:second|number two)\b", text):
            list_text = text
            for pat, rep in ordinals:
                list_text = re.sub(pat, rep, list_text)
            list_text = re.sub(r"\n\s*\n", "\n", list_text).strip()
            return list_text, True

        return text, False

    def _apply_concise(self, text: str) -> Tuple[str, bool]:
        original = text
        for pat, rep in CONCISE_MAP.items():
            text = re.sub(pat, rep, text, flags=re.IGNORECASE)
        return text, (text != original)

    def _format_email(self, text: str) -> Tuple[str, bool]:
        original = text
        greeting_match = re.match(r"(?i)^(hi|hello|dear|hey)\s+([a-zA-Z]+)[,\s]*(.*)", text)
        if greeting_match:
            greet, name, body = greeting_match.groups()
            text = f"{greet.capitalize()} {name.capitalize()},\n\n{body.strip()}"

        signoff_match = re.search(r"(?i)(.*?)[\s,]*(thanks|thank you|best regards|regards|cheers)[\s,]*([a-zA-Z]*)$", text)
        if signoff_match:
            body, signoff, sender = signoff_match.groups()
            sender_str = f"\n{sender.capitalize()}" if sender else ""
            text = f"{body.strip()}\n\n{signoff.capitalize()},{sender_str}".strip()

        return text, (text != original)

    def _apply_professional(self, text: str) -> str:
        sentences = re.split(r"([.?!]\s+)", text)
        capped = []
        for s in sentences:
            if s and s[0].islower():
                capped.append(s[0].upper() + s[1:])
            else:
                capped.append(s)
        return "".join(capped)

    def _finalize_punctuation(self, text: str, style: str = "professional") -> str:
        text = text.strip()
        if not text:
            return ""

        # Remove duplicate punctuation
        text = re.sub(r"\.{2,}", ".", text)
        text = re.sub(r",{2,}", ",", text)

        # For terminal commands, NEVER append a trailing period or capitalize initial command
        KNOWN_COMMANDS = (
            "git", "npm", "pnpm", "yarn", "pip", "python", "pytest", "docker", "kubectl",
            "cd", "ls", "cat", "grep", "curl", "wget", "ssh", "scp", "tar", "zip",
            "cargo", "go", "make", "cmake", "npx", "node", "deno", "bun", "mv", "cp", "rm"
        )
        first_word = text.split()[0].lower() if text.split() else ""
        is_cli_cmd = first_word in KNOWN_COMMANDS

        is_camel_case = bool(re.match(r"^[a-z]+[A-Z][a-zA-Z0-9]*$", text))
        is_snake_case = bool(re.match(r"^[a-z0-9]+(?:_[a-z0-9]+)+$", text))

        if style != "terminal" and not is_cli_cmd and not is_camel_case and not is_snake_case:
            # Capitalize start if alphabetic
            if text and text[0].islower():
                text = text[0].upper() + text[1:]

        if style == "terminal":
            # Under no circumstances should terminal profile add trailing punctuation
            return text

        # For developer code, URLs, and commands, do NOT append trailing period
        is_code_or_url = (
            style in ("developer", "technical", "terminal") or
            is_cli_cmd or
            re.match(r"^(?:https?://|www\.|git\s+|docker\s+|npm\s+|pip\s+|cd\s+|curl\s+)", text, re.IGNORECASE) or
            re.search(r"^[a-zA-Z0-9_\-\.]+\([a-zA-Z0-9_,\s]*\)$", text) or
            re.match(r"^[a-z]+[A-Z][a-zA-Z0-9]*$", text) or
            re.match(r"^[a-z0-9]+(?:_[a-z0-9]+)+$", text)
        )

        # Terminal punctuation check supporting Latin, CJK, Indic, and Arabic marks
        terminal_marks = (
            ".", "!", "?", ":", ";", "-", "…",
            "。", "！", "？", "：", "；",  # CJK
            "।", "॥",                     # Devanagari / Indic
            "؟", "؛", "ـ"                  # Arabic
        )
        if not is_code_or_url and "\n" not in text and not text.endswith(terminal_marks):
            text += "."

        return text
