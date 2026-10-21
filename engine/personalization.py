"""
FlowPilot Advanced Personalization Module (PR 3)
Provides:
1. Personal Custom Dictionary & Deliberate Vocabulary Corrections:
   - User-defined domain vocabulary, technical identifiers, company names, and native/romanized terms.
   - Multi-alias phonetic mappings per canonical term (e.g., "FlowPilot" <- ["flow pilot", "flo pilot", "flow pilot app"]).
   - Multi-alias support without accidental overwriting.
   - Scoped terms: optional language (e.g. "ta", "hi", "ml", "en") and application/profile scope (e.g. "developer", "terminal").
   - Leak-proof context isolation (Tamil terms do not leak to English, developer terms do not leak to general email).
   - Bounded tokenizer prompt budgeting with reserved room for decoder control tokens.
   - Persistent deletion tombstones for terms and aliases.
   - FactGuard-safe post-processing (negation and number preservation, no mid-word corruption).
2. Voice Snippets:
   - Voice-activated snippet expansion (e.g., "insert my calendly" -> "https://calendly.com/user/demo").
   - Multi-line templates for email signatures, markdown scaffolds, and boilerplate code.
   - Whole-word regex boundaries and longest-match precedence.
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable, Set

from engine.prompt_budget import PromptBudgetManager

PERSONALIZATION_FILE = Path.home() / ".flowpilot" / "personalization.json"

DEFAULT_DICTIONARY: List[Dict[str, Any]] = [
    {
        "term": "FlowPilot",
        "alias": "flow pilot",
        "aliases": ["flow pilot", "flo pilot"],
        "language": None,
        "profile": None
    },
    {
        "term": "FastAPI",
        "alias": "fast api",
        "aliases": ["fast api"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "Pydantic",
        "alias": "pie dantic",
        "aliases": ["pie dantic", "pi dantic"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "PostgreSQL",
        "alias": "postgres",
        "aliases": ["postgres", "post gres"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "Kubernetes",
        "alias": "k eight s",
        "aliases": ["k eight s", "k8s"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "GraphQL",
        "alias": "graph ql",
        "aliases": ["graph ql"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "TypeScript",
        "alias": "type script",
        "aliases": ["type script"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "PySide6",
        "alias": "pie side six",
        "aliases": ["pie side six", "py side six"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "CTranslate2",
        "alias": "c translate two",
        "aliases": ["c translate two"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "OAuth2",
        "alias": "o auth two",
        "aliases": ["o auth two"],
        "language": None,
        "profile": "developer"
    },
    {
        "term": "Calendly",
        "alias": "calendly",
        "aliases": ["michael endley", "michael endly", "micolendly"],
        "language": None,
        "profile": None
    }
]

DEFAULT_SNIPPETS: List[Dict[str, str]] = [
    {
        "trigger": "insert my calendly",
        "expansion": "https://calendly.com/flowpilot-demo/15min"
    },
    {
        "trigger": "insert calendly",
        "expansion": "https://calendly.com/flowpilot-demo/15min"
    },
    {
        "trigger": "insert my zoom link",
        "expansion": "https://zoom.us/j/9876543210"
    },
    {
        "trigger": "insert email signature",
        "expansion": "Best regards,\nMohamed\nFlowPilot Engineering Team"
    },
    {
        "trigger": "insert bug report template",
        "expansion": "### Bug Description\n- **Steps to reproduce:**\n- **Expected behavior:**\n- **Actual behavior:**\n- **Environment:** Windows 11 / FlowPilot v2.1"
    }
]

# Protected critical tokens that must never be converted by alias replacement
PROTECTED_NEGATION_AND_FACT_TOKENS: Set[str] = {
    # English negations
    "not", "no", "never", "none", "neither", "nor", "cannot", "can't", "won't", "don't", "didn't",
    # Tamil negations
    "இல்லை", "அல்ல", "வேண்டாம்", "கூடாது",
    # Hindi negations
    "नहीं", "मत", "ना",
    # Malayalam negations
    "അല്ല", "ഇല്ല", "വേണ്ട", "പാടില്ല"
}


class PersonalizationEngine:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or PERSONALIZATION_FILE
        self.dictionary: List[Dict[str, Any]] = []
        self.snippets: List[Dict[str, str]] = []
        self.tombstones: List[str] = []
        self._change_listeners: List[Callable[[], None]] = []
        self.budget_manager = PromptBudgetManager()
        self.load()

    def add_change_listener(self, callback: Callable[[], None]) -> None:
        """Registers a callback to be invoked immediately whenever dictionary or snippets change."""
        if callback not in self._change_listeners:
            self._change_listeners.append(callback)

    def remove_change_listener(self, callback: Callable[[], None]) -> None:
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)

    def _notify_listeners(self) -> None:
        for cb in list(self._change_listeners):
            try:
                cb()
            except Exception as e:
                print(f"[Personalization] Change listener exception: {e}")

    def _normalize_entry(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures consistent dictionary item structure with term, aliases, language, and profile."""
        term = raw.get("term", "").strip()
        primary_alias = raw.get("alias", "").strip().lower()
        aliases_list = raw.get("aliases")

        if aliases_list is None:
            aliases = [primary_alias] if primary_alias else []
        else:
            aliases = [str(a).strip().lower() for a in aliases_list if str(a).strip()]
            if primary_alias and primary_alias not in aliases:
                aliases.insert(0, primary_alias)

        primary = aliases[0] if aliases else primary_alias

        return {
            "term": term,
            "alias": primary,
            "aliases": aliases,
            "language": raw.get("language") or None,
            "profile": raw.get("profile") or None,
            "created_at": raw.get("created_at") or time.time(),
            "updated_at": raw.get("updated_at") or time.time()
        }

    def load(self) -> None:
        """Loads dictionary and snippets from JSON file, initializing defaults if absent and honoring deletion tombstones."""
        if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.dictionary = [self._normalize_entry(d) for d in DEFAULT_DICTIONARY]
            self.snippets = list(DEFAULT_SNIPPETS)
            self.tombstones = []
            self.save()
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                loaded_dict = [self._normalize_entry(d) for d in data.get("dictionary", [])]
                loaded_snips = data.get("snippets", [])
                self.tombstones = [t.lower() for t in data.get("tombstones", [])]

                existing_terms = {item.get("term", "").lower() for item in loaded_dict}
                for d in DEFAULT_DICTIONARY:
                    term_l = d["term"].lower()
                    if term_l in self.tombstones or f"term:{term_l}" in self.tombstones:
                        continue
                    if term_l not in existing_terms:
                        loaded_dict.append(self._normalize_entry(d))
                        existing_terms.add(term_l)

                existing_triggers = {item.get("trigger", "").lower() for item in loaded_snips}
                for s in DEFAULT_SNIPPETS:
                    trig_l = s["trigger"].lower()
                    if trig_l in self.tombstones or f"snippet:{trig_l}" in self.tombstones:
                        continue
                    if trig_l not in existing_triggers:
                        loaded_snips.append(dict(s))
                        existing_triggers.add(trig_l)

                self.dictionary = loaded_dict
                self.snippets = loaded_snips
        except Exception as e:
            print(f"[Personalization] Error loading personalization config: {e}. Falling back to defaults.")
            self.dictionary = [self._normalize_entry(d) for d in DEFAULT_DICTIONARY]
            self.snippets = list(DEFAULT_SNIPPETS)
            self.tombstones = []

    def save(self) -> None:
        """Persists dictionary, snippets, and deletion tombstones to JSON file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "version": 2,
                    "dictionary": self.dictionary,
                    "snippets": self.snippets,
                    "tombstones": self.tombstones
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Personalization] Error saving config: {e}")
        self._notify_listeners()

    # --- DICTIONARY OPERATIONS ---

    def add_term(
        self,
        term: str,
        alias: str = "",
        language: Optional[str] = None,
        profile: Optional[str] = None,
        aliases: Optional[List[str]] = None
    ) -> None:
        """
        Adds or updates a dictionary term with multi-alias support.
        Preserves existing aliases without accidental overwriting.
        Supports language and app/profile scoping.
        """
        term = term.strip()
        if not term:
            return

        term_l = term.lower()
        alias_clean = alias.strip().lower()

        # Collect incoming aliases
        incoming_aliases: List[str] = []
        if aliases:
            incoming_aliases.extend([str(a).strip().lower() for a in aliases if str(a).strip()])
        if alias_clean and alias_clean not in incoming_aliases:
            incoming_aliases.append(alias_clean)

        # Remove resurrecting tombstones
        if term_l in self.tombstones:
            self.tombstones.remove(term_l)
        if f"term:{term_l}" in self.tombstones:
            self.tombstones.remove(f"term:{term_l}")

        for item in self.dictionary:
            if item.get("term", "").lower() == term_l:
                # Update canonical display casing
                item["term"] = term
                existing_aliases: List[str] = item.get("aliases", [])
                for new_a in incoming_aliases:
                    if new_a not in existing_aliases:
                        existing_aliases.append(new_a)
                item["aliases"] = existing_aliases
                item["alias"] = existing_aliases[0] if existing_aliases else ""

                if language is not None:
                    item["language"] = language.strip().lower() if language else None
                if profile is not None:
                    item["profile"] = profile.strip().lower() if profile else None

                item["updated_at"] = time.time()
                self.save()
                return

        # New term insertion
        new_entry = {
            "term": term,
            "alias": incoming_aliases[0] if incoming_aliases else "",
            "aliases": incoming_aliases,
            "language": language.strip().lower() if language else None,
            "profile": profile.strip().lower() if profile else None,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        self.dictionary.append(new_entry)
        self.save()

    def add_alias(self, term: str, alias: str) -> bool:
        """Convenience method to register an additional phonetic alias for an existing term."""
        term_l = term.strip().lower()
        alias_clean = alias.strip().lower()
        if not term_l or not alias_clean:
            return False

        for item in self.dictionary:
            if item.get("term", "").lower() == term_l:
                aliases: List[str] = item.setdefault("aliases", [])
                if alias_clean not in aliases:
                    aliases.append(alias_clean)
                    item["alias"] = aliases[0]
                    item["updated_at"] = time.time()
                    self.save()
                return True

        # If term doesn't exist, create it with this alias
        self.add_term(term, alias=alias_clean)
        return True

    def remove_term(self, term: str) -> bool:
        """Removes a canonical term from the dictionary and records a tombstone."""
        term_l = term.strip().lower()
        initial_len = len(self.dictionary)
        self.dictionary = [item for item in self.dictionary if item.get("term", "").lower() != term_l]
        if len(self.dictionary) != initial_len:
            if term_l not in self.tombstones:
                self.tombstones.append(term_l)
            tombstone_key = f"term:{term_l}"
            if tombstone_key not in self.tombstones:
                self.tombstones.append(tombstone_key)
            self.save()
            return True
        return False

    def remove_alias(self, term: str, alias: str) -> bool:
        """Removes a specific alias from a canonical term and records an alias tombstone."""
        term_l = term.strip().lower()
        alias_l = alias.strip().lower()
        for item in self.dictionary:
            if item.get("term", "").lower() == term_l:
                aliases: List[str] = item.get("aliases", [])
                if alias_l in aliases:
                    aliases.remove(alias_l)
                    item["alias"] = aliases[0] if aliases else ""
                    item["updated_at"] = time.time()
                    alias_tomb = f"alias:{term_l}:{alias_l}"
                    if alias_tomb not in self.tombstones:
                        self.tombstones.append(alias_tomb)
                    self.save()
                    return True
        return False

    def get_scoped_entries(
        self,
        language: Optional[str] = None,
        profile: Optional[str] = None,
        process_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves dictionary items scoped to the active language and application context.
        Guarantees isolation:
        - Scoped language terms do NOT leak into unrelated languages.
        - Scoped profile terms do NOT leak into unrelated apps.
        - Global terms (language=None and profile=None) match everywhere.
        - When language or profile is unspecified (None), all terms apply.
        """
        results = []
        lang_norm = language.strip().lower() if language and language != "auto" else None
        prof_norm = profile.strip().lower() if profile else None
        proc_norm = process_name.strip().lower() if process_name else None

        for item in self.dictionary:
            item_lang = item.get("language")
            item_prof = item.get("profile")

            # 1. Language Scoping Check: filter if language is specified and term is language-restricted
            if lang_norm is not None and item_lang is not None:
                item_lang_l = item_lang.lower()
                if item_lang_l != lang_norm and not lang_norm.startswith(item_lang_l):
                    continue

            # 2. Profile & Process Scoping Check: filter if profile/process is specified and term is profile-restricted
            if (prof_norm is not None or proc_norm is not None) and item_prof is not None:
                item_prof_l = item_prof.lower()
                profile_match = prof_norm and (item_prof_l == prof_norm)
                process_match = proc_norm and (item_prof_l in proc_norm or proc_norm.endswith(item_prof_l))
                if not profile_match and not process_match:
                    continue

            results.append(item)

        return results

    def get_terms_list(
        self,
        language: Optional[str] = None,
        profile: Optional[str] = None,
        process_name: Optional[str] = None
    ) -> List[str]:
        """
        Returns list of canonical term strings.
        If language or profile is provided, filters to context-scoped terms.
        If no arguments provided, returns all dictionary terms for backward compatibility.
        """
        if language is None and profile is None and process_name is None:
            return [item.get("term", "") for item in self.dictionary if item.get("term")]

        scoped = self.get_scoped_entries(language=language, profile=profile, process_name=process_name)
        return [item.get("term", "") for item in scoped if item.get("term")]

    def build_whisper_prompt(
        self,
        language: Optional[str] = None,
        profile: Optional[str] = None,
        max_terms: int = 50,
        max_tokens: int = 120
    ) -> str:
        """
        Builds a tokenizer-bounded initial_prompt string for Whisper decoder biasing.
        Enforces token budget and bounds context window.
        Format: 'Technical glossary: Term1, Term2, Term3.'
        """
        terms = self.get_terms_list(language=language, profile=profile)[:max_terms]
        if not terms:
            return ""

        prompt, _, _ = self.budget_manager.build_bounded_prompt(
            language=language or "en",
            base_prompt="",
            custom_terms=terms,
            max_total_tokens=max_tokens
        )
        return prompt

    def get_hotwords(
        self,
        language: Optional[str] = None,
        profile: Optional[str] = None,
        max_terms: int = 30
    ) -> str:
        """
        Returns a comma-separated string of hotwords for CTranslate2 / faster-whisper.
        """
        terms = self.get_terms_list(language=language, profile=profile)
        return PromptBudgetManager.format_hotwords(terms, max_terms=max_terms)

    def apply_dictionary(
        self,
        text: str,
        language: Optional[str] = None,
        profile: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """
        Applies exact alias replacements and canonical casing:
        - Scoped to active language and profile (prevents cross-language leakage).
        - Whole-word regex boundaries preserving Indic combining marks and Latin words.
        - FactGuard invariants: protects critical negations and numbers from accidental overwrite.
        - Longer aliases match first to prevent substring shadowing.
        """
        if not text:
            return text, []

        changes = []
        result = text
        scoped_entries = self.get_scoped_entries(language=language, profile=profile)

        # Build list of all active (alias, term) pairs
        alias_pairs: List[Tuple[str, str]] = []
        casing_terms: List[str] = []

        for item in scoped_entries:
            term = item.get("term", "")
            if not term:
                continue
            casing_terms.append(term)
            aliases = item.get("aliases") or ([item["alias"]] if item.get("alias") else [])
            for a in aliases:
                a_clean = a.strip()
                if a_clean and a_clean.lower() != term.lower():
                    # FactGuard protection: Do not allow replacement if alias is a pure negation
                    if a_clean.lower() in PROTECTED_NEGATION_AND_FACT_TOKENS:
                        continue
                    # Protect pure numbers from becoming words
                    if a_clean.isdigit():
                        continue
                    alias_pairs.append((a_clean, term))

        # Sort alias pairs by length descending to match longest phrases first
        alias_pairs.sort(key=lambda pair: len(pair[0]), reverse=True)

        # 1. Alias replacements
        for alias, term in alias_pairs:
            # Word boundary regex that works with both Latin and Indic Unicode codepoints
            pattern = r"(?i)(?<![\w\u0900-\u0D7F])" + re.escape(alias) + r"(?![\w\u0900-\u0D7F])"
            if re.search(pattern, result):
                result = re.sub(pattern, term, result)
                changes.append(f"Alias '{alias}' -> '{term}'")

        # 2. Case normalization (for exact terms with incorrect casing)
        casing_terms.sort(key=lambda t: len(t), reverse=True)
        for term in casing_terms:
            pattern = r"(?i)(?<![\w\u0900-\u0D7F])" + re.escape(term) + r"(?![\w\u0900-\u0D7F])"
            matches = list(re.finditer(pattern, result))
            for m in reversed(matches):
                matched_str = m.group(0)
                if matched_str != term:
                    result = result[:m.start()] + term + result[m.end():]
                    changes.append(f"Cased '{matched_str}' -> '{term}'")

        return result, changes

    # --- SNIPPET OPERATIONS ---

    RESERVED_KEYWORD_TRIGGERS = {
        "paste last", "copy last", "re-inject", "re-copy",
        "new line", "newline", "new paragraph", "tab",
        "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"
    }

    def add_snippet(self, trigger: str, expansion: str) -> Dict[str, Any]:
        """
        Adds or updates a voice snippet trigger.
        Performs conflict detection and enforces static literal templates.
        """
        trigger = trigger.strip().lower()
        if not trigger or not expansion:
            return {"status": "error", "message": "Trigger and expansion cannot be empty"}

        warnings = []
        if trigger in self.RESERVED_KEYWORD_TRIGGERS:
            warnings.append(f"Notice: Trigger '{trigger}' matches a reserved command or key name. Default actions take precedence.")

        if trigger in self.tombstones:
            self.tombstones.remove(trigger)
        if f"snippet:{trigger}" in self.tombstones:
            self.tombstones.remove(f"snippet:{trigger}")

        for item in self.snippets:
            existing_tr = item.get("trigger", "").lower()
            if existing_tr == trigger:
                item["expansion"] = expansion
                self.save()
                return {"status": "updated", "warnings": warnings}
            elif existing_tr in trigger:
                warnings.append(f"Notice: Trigger '{trigger}' contains existing sub-trigger '{existing_tr}'. Longest match precedence will apply.")
            elif trigger in existing_tr:
                warnings.append(f"Notice: Existing trigger '{existing_tr}' contains new trigger '{trigger}'. Longest match precedence will apply.")

        self.snippets.append({"trigger": trigger, "expansion": expansion})
        self.save()
        return {"status": "added", "warnings": warnings}

    def remove_snippet(self, trigger: str) -> bool:
        """Removes a voice snippet by its trigger phrase and records a tombstone."""
        trig_l = trigger.strip().lower()
        initial_len = len(self.snippets)
        self.snippets = [s for s in self.snippets if s.get("trigger", "").lower() != trig_l]
        if len(self.snippets) != initial_len:
            if trig_l not in self.tombstones:
                self.tombstones.append(trig_l)
            snippet_tomb = f"snippet:{trig_l}"
            if snippet_tomb not in self.tombstones:
                self.tombstones.append(snippet_tomb)
            self.save()
            return True
        return False

    def expand_snippets(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Checks if text contains or matches a voice snippet trigger.
        Replaces the spoken trigger phrase with its expanded snippet.
        Matches longer triggers first to resolve overlapping phrases.
        Uses literal lambda replacement to guarantee zero command/template injection.
        """
        if not text:
            return text, None

        sorted_snippets = sorted(
            self.snippets,
            key=lambda item: len(item.get("trigger", "")),
            reverse=True
        )

        for item in sorted_snippets:
            trigger = item.get("trigger", "").strip()
            expansion = item.get("expansion", "")
            if not trigger or not expansion:
                continue

            pattern = r"(?i)(?<![\w\u0900-\u0D7F])" + re.escape(trigger) + r"(?![\w\u0900-\u0D7F])"
            if re.search(pattern, text):
                expanded_text = re.sub(pattern, lambda m: expansion, text).strip()
                return expanded_text, trigger

        return text, None

    # --- IMPORT / EXPORT ---

    def export_json(self) -> str:
        """Exports dictionary and snippets to formatted JSON string."""
        return json.dumps({
            "version": 2,
            "dictionary": self.dictionary,
            "snippets": self.snippets,
            "tombstones": self.tombstones
        }, indent=2, ensure_ascii=False)

    def import_json(self, json_str: str, merge: bool = True) -> bool:
        """Imports dictionary and snippets from JSON string with v1/v2 schema compatibility."""
        try:
            data = json.loads(json_str)
            incoming_dict = data.get("dictionary", [])
            incoming_snippets = data.get("snippets", [])

            if merge:
                for raw_item in incoming_dict:
                    normalized = self._normalize_entry(raw_item)
                    t = normalized.get("term")
                    if t:
                        self.add_term(
                            term=t,
                            alias=normalized.get("alias", ""),
                            language=normalized.get("language"),
                            profile=normalized.get("profile"),
                            aliases=normalized.get("aliases")
                        )
                for item in incoming_snippets:
                    tr = item.get("trigger")
                    ex = item.get("expansion")
                    if tr and ex:
                        self.add_snippet(tr, ex)
            else:
                self.dictionary = [self._normalize_entry(d) for d in incoming_dict]
                self.snippets = incoming_snippets
                self.save()
            return True
        except Exception as e:
            print(f"[Personalization] Import failed: {e}")
            return False


_shared_personalization: Optional[PersonalizationEngine] = None


def get_shared_personalization() -> PersonalizationEngine:
    """Returns the shared application-wide PersonalizationEngine singleton."""
    global _shared_personalization
    if _shared_personalization is None:
        _shared_personalization = PersonalizationEngine()
    return _shared_personalization
