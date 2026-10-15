"""
FlowPilot Advanced Personalization Module
Provides:
1. Personal Custom Dictionary:
   - User-defined domain vocabulary, technical terms, company names, and acronyms.
   - Phonetic alias mappings (e.g., "flow pilot" -> "FlowPilot", "post gres" -> "PostgreSQL").
   - Generates initial_prompt biasing tokens for Whisper decoding.
   - Deterministic casing and spelling enforcement.
   - JSON import and export for team synchronization.
2. Voice Snippets:
   - Voice-activated snippet expansion (e.g., "insert my calendly" -> "https://calendly.com/user/demo").
   - Multi-line templates for email signatures, markdown scaffolds, and boilerplate code.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PERSONALIZATION_FILE = Path.home() / ".flowpilot" / "personalization.json"

DEFAULT_DICTIONARY: List[Dict[str, str]] = [
    {"term": "FlowPilot", "alias": "flow pilot"},
    {"term": "FastAPI", "alias": "fast api"},
    {"term": "Pydantic", "alias": "pie dantic"},
    {"term": "PostgreSQL", "alias": "postgres"},
    {"term": "Kubernetes", "alias": "k eight s"},
    {"term": "GraphQL", "alias": "graph ql"},
    {"term": "TypeScript", "alias": "type script"},
    {"term": "PySide6", "alias": "pie side six"},
    {"term": "CTranslate2", "alias": "c translate two"},
    {"term": "OAuth2", "alias": "o auth two"},
    {"term": "Calendly", "alias": "michael endley"},
    {"term": "Calendly", "alias": "michael endly"},
    {"term": "Calendly", "alias": "micolendly"}
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

class PersonalizationEngine:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or PERSONALIZATION_FILE
        self.dictionary: List[Dict[str, str]] = []
        self.snippets: List[Dict[str, str]] = []
        self.load()

    def load(self) -> None:
        """Loads dictionary and snippets from JSON file, initializing defaults if absent."""
        if not self.storage_path.exists() or self.storage_path.stat().st_size == 0:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.dictionary = list(DEFAULT_DICTIONARY)
            self.snippets = list(DEFAULT_SNIPPETS)
            self.save()
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                loaded_dict = data.get("dictionary", [])
                loaded_snips = data.get("snippets", [])

                existing_aliases = {(item.get("term", "").lower(), item.get("alias", "").lower()) for item in loaded_dict}
                for d in DEFAULT_DICTIONARY:
                    if (d["term"].lower(), d["alias"].lower()) not in existing_aliases:
                        loaded_dict.append(dict(d))

                existing_triggers = {item.get("trigger", "").lower() for item in loaded_snips}
                for s in DEFAULT_SNIPPETS:
                    if s["trigger"].lower() not in existing_triggers:
                        loaded_snips.append(dict(s))

                self.dictionary = loaded_dict
                self.snippets = loaded_snips
        except Exception as e:
            print(f"[Personalization] Error loading personalization config: {e}. Falling back to defaults.")
            self.dictionary = list(DEFAULT_DICTIONARY)
            self.snippets = list(DEFAULT_SNIPPETS)

    def save(self) -> None:
        """Persists dictionary and snippets to JSON file."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "dictionary": self.dictionary,
                    "snippets": self.snippets
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Personalization] Error saving config: {e}")

    # --- DICTIONARY OPERATIONS ---

    def add_term(self, term: str, alias: str = "") -> None:
        """Adds or updates a dictionary term with optional phonetic alias."""
        term = term.strip()
        alias = alias.strip().lower()
        if not term:
            return

        for item in self.dictionary:
            if item.get("term", "").lower() == term.lower():
                item["term"] = term
                if alias:
                    item["alias"] = alias
                self.save()
                return

        self.dictionary.append({"term": term, "alias": alias})
        self.save()

    def remove_term(self, term: str) -> bool:
        """Removes a term from the dictionary."""
        initial_len = len(self.dictionary)
        self.dictionary = [item for item in self.dictionary if item.get("term", "").lower() != term.lower()]
        if len(self.dictionary) != initial_len:
            self.save()
            return True
        return False

    def get_terms_list(self) -> List[str]:
        """Returns list of plain term strings for biasing."""
        return [item.get("term", "") for item in self.dictionary if item.get("term")]

    def build_whisper_prompt(self, max_terms: int = 50) -> str:
        """
        Builds initial_prompt token string for Whisper decoder biasing.
        Format: 'Glossary: Term1, Term2, Term3.'
        """
        terms = self.get_terms_list()[:max_terms]
        if not terms:
            return ""
        return "Glossary: " + ", ".join(terms) + "."

    def apply_dictionary(self, text: str) -> Tuple[str, List[str]]:
        """
        Applies exact alias replacements and canonical casing:
        - If an alias is present (e.g. 'flow pilot'), replaces with 'FlowPilot'.
        - If the term is present with wrong casing (e.g. 'fastapi'), replaces with 'FastAPI'.
        """
        if not text:
            return text, []

        changes = []
        result = text

        for item in self.dictionary:
            term = item.get("term", "")
            alias = item.get("alias", "")
            if not term:
                continue

            # 1. Alias replacement
            if alias:
                pattern = r"(?i)\b" + re.escape(alias) + r"\b"
                if re.search(pattern, result):
                    result = re.sub(pattern, term, result)
                    changes.append(f"Alias '{alias}' -> '{term}'")

            # 2. Case normalization (replace mis-cased occurrences)
            term_pattern = r"(?i)\b" + re.escape(term) + r"\b"
            matches = list(re.finditer(term_pattern, result))
            for m in matches:
                matched_str = m.group(0)
                if matched_str != term:
                    result = result[:m.start()] + term + result[m.end():]
                    changes.append(f"Cased '{matched_str}' -> '{term}'")

        return result, changes

    # --- SNIPPET OPERATIONS ---

    def add_snippet(self, trigger: str, expansion: str) -> Dict[str, Any]:
        """
        Adds or updates a voice snippet trigger.
        Performs conflict detection and enforces static literal templates.
        """
        trigger = trigger.strip().lower()
        if not trigger or not expansion:
            return {"status": "error", "message": "Trigger and expansion cannot be empty"}

        warnings = []
        # Check for conflicting or overlapping triggers
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
        """Removes a voice snippet by its trigger phrase."""
        initial_len = len(self.snippets)
        self.snippets = [s for s in self.snippets if s.get("trigger", "").lower() != trigger.lower()]
        if len(self.snippets) != initial_len:
            self.save()
            return True
        return False

    def expand_snippets(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Checks if text contains or matches a voice snippet trigger.
        Replaces the spoken trigger phrase with its expanded snippet.
        Matches longer triggers first to resolve overlapping phrases.
        Uses literal replacement to guarantee zero command/template injection.
        """
        if not text:
            return text, None

        # Sort snippets by trigger length descending so specific longer triggers take precedence
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

            # Check for case-insensitive whole-word trigger phrase
            pattern = r"(?i)(?<!\w)" + re.escape(trigger) + r"(?!\w)"
            if re.search(pattern, text):
                # Lambda replacement ensures literal string injection without regex backreference parsing
                expanded_text = re.sub(pattern, lambda m: expansion, text).strip()
                return expanded_text, trigger

        return text, None

    # --- IMPORT / EXPORT ---

    def export_json(self) -> str:
        """Exports dictionary and snippets to formatted JSON string."""
        return json.dumps({
            "dictionary": self.dictionary,
            "snippets": self.snippets
        }, indent=2, ensure_ascii=False)

    def import_json(self, json_str: str, merge: bool = True) -> bool:
        """Imports dictionary and snippets from JSON string."""
        try:
            data = json.loads(json_str)
            incoming_dict = data.get("dictionary", [])
            incoming_snippets = data.get("snippets", [])

            if merge:
                for item in incoming_dict:
                    t = item.get("term")
                    a = item.get("alias", "")
                    if t:
                        self.add_term(t, a)
                for item in incoming_snippets:
                    tr = item.get("trigger")
                    ex = item.get("expansion")
                    if tr and ex:
                        self.add_snippet(tr, ex)
            else:
                self.dictionary = incoming_dict
                self.snippets = incoming_snippets
                self.save()
            return True
        except Exception as e:
            print(f"[Personalization] Import failed: {e}")
            return False
