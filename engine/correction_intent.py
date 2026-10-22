"""
FlowPilot Correction Intent Engine
=================================
Deterministic resolution of spoken self-corrections, applied before text injection.

Why this module exists
----------------------
The previous implementation (a set of ordered regexes inside
``WritingIntelligence._resolve_self_corrections``) had four measurable defects:

1. It destroyed meaning on intensifier usage.
   ``"I actually enjoyed the movie"`` became ``"Enjoyed the movie."``
   and ``"we were actually going to leave early"`` became
   ``"We going to leave early."``
2. It resolved only the FIRST correction in an utterance, and mangled the
   sentence when it did: ``"bring 5 laptops actually 3 laptops"`` became
   ``"bring 5 3 laptops"``.
3. It had no trigger vocabulary beyond ``actually`` / ``or rather`` /
   ``no wait`` / ``wait no``. Spoken corrections such as ``sorry Jane``,
   ``never mind``, ``I mean`` and a bare ``wait`` were never resolved.
4. Trigger phrases that contain a protected token (``no`` in ``no wait``,
   ``never`` in ``never mind``) were misread by ``FactGuard`` as semantic
   negations, which silently reverted the *entire* correction.

Design rules
------------
* **Never destroy meaning.** An intensifier marker (``actually``) is only
  treated as a correction marker when the superseded span is a *replaceable
  value* (number, temporal, or proper noun) or is bound by a preposition.
  Function words (pronouns, determiners, auxiliaries) can never be
  superseded values.
* **Span-aware.** ``"send 5 copies, no wait, 10 copies"`` replaces the whole
  quantity phrase (``5 copies`` -> ``10 copies``), not a single token.
* **Multiple corrections per utterance.** Every trigger in the utterance is
  resolved, not just the first.
* **Triggers are consumed whole.** Protected tokens inside a trigger phrase
  are reported back to ``FactGuard`` as intentional retractions so they are
  not mistaken for dropped semantic negations.
* **FactGuard invariants are preserved.** Superseded numbers and negations
  are returned to the caller so the semantic guard can still distinguish an
  intentional retraction from an accidental loss.

No network access, no model inference, no cloud egress.
"""

import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Trigger vocabulary
# ---------------------------------------------------------------------------
# Each spec is (name, regex, is_explicit, requires_value_neighbours).
#
#   is_explicit
#       True  - the speaker is *announcing* a correction. These may supersede
#               common nouns as well as numbers and proper nouns.
#       False - intensifier-style markers ("actually"). Frequently NOT a
#               correction marker at all, so they only fire against
#               replaceable values.
#
#   requires_value_neighbours
#       True  - the trigger only counts when a value-like token sits on both
#               sides. Keeps an ordinary "please wait for the server" from
#               being read as a correction.
EXPLICIT_TRIGGERS: List[Tuple[str, str, bool]] = [
    ("no_wait", r"no\s+wait", False),
    ("wait_no", r"wait\s+no", False),
    ("wait", r"wait", True),
    ("never_mind", r"never\s*mind", False),
    ("i_mean", r"i\s+mean(?:t|s)?\b", False),
    ("sorry", r"sorry", True),
    ("correction", r"correction", False),
    ("or_rather", r"or\s+rather", False),
    ("rather", r"rather\b", True),
]

INTENSIFIER_TRIGGERS: List[Tuple[str, str, bool]] = [
    ("actually", r"actually\b", False),
]

# Multilingual triggers, keyed by ISO-639-1 prefix.
MULTILINGUAL_TRIGGERS: Dict[str, List[Tuple[str, str, bool]]] = {
    "de": [
        ("eigentlich", r"eigentlich\b", False),
        ("entschuldigung", r"entschuldigung\b", True),
        ("nein_warte", r"nein\s+warte\b", False),
        ("warte", r"warte\b", True),
        ("lieber", r"lieber\b", True),
    ],
    "fr": [
        ("en_fait", r"en\s+fait\b", False),
        ("pardon", r"pardon\b", True),
        ("non_attends", r"non\s+attends\b", False),
        ("attends", r"attends\b", True),
        ("plutot", r"plut[oô]t\b", True),
        ("laisse_tombe", r"laisse\s+tombe\b", False),
    ],
    "es": [
        ("en_realidad", r"en\s+realidad\b", False),
        ("perdona", r"perdona\b", True),
        ("espera", r"espera\b", True),
        ("mejor", r"mejor\b", True),
        ("da_igual", r"da\s+igual\b", False),
    ],
}

# ---------------------------------------------------------------------------
# Closed-class lexical resources
# ---------------------------------------------------------------------------
NUMBER_WORDS = {
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "billion",
}

# Function words can never be a superseded *value*. Pronouns, determiners,
# prepositions, conjunctions, auxiliaries and particles.
FUNCTION_WORDS = {
    # pronouns / determiners
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself",
    "he", "him", "his", "himself", "she", "her", "hers", "herself", "it",
    "its", "itself", "we", "us", "our", "ours", "ourselves", "they", "them",
    "their", "theirs", "themselves", "this", "that", "these", "those",
    "who", "whom", "whose", "what", "which", "someone", "somebody",
    "something", "anyone", "anybody", "anything", "everyone", "everybody",
    "everything", "nobody", "nothing",
    "a", "an", "the", "some", "any", "each", "every", "both", "either",
    "neither", "much", "many", "few", "several", "all", "no", "none",
    "other", "another", "such", "same", "please", "okay", "ok",
    # prepositions
    "about", "above", "across", "after", "against", "along", "among",
    "around", "at", "before", "behind", "below", "beneath", "beside",
    "between", "beyond", "by", "concerning", "despite", "down", "during",
    "except", "for", "from", "in", "inside", "into", "like", "near", "of",
    "off", "on", "onto", "out", "outside", "over", "past", "per",
    "regarding", "since", "through", "throughout", "to", "toward",
    "towards", "under", "until", "up", "upon", "via", "with", "within",
    "without",
    # conjunctions / subordinators
    "and", "but", "or", "nor", "so", "yet", "if", "then", "else", "because",
    "while", "although", "though", "unless", "whether", "as", "than",
    "once", "whereas",
    # auxiliaries / copulas / particles
    "am", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "having", "do", "does", "did", "doing", "will", "would", "shall",
    "should", "can", "could", "may", "might", "must", "there", "here",
    "not", "now", "just", "very",
}

# Prepositions that bind a following noun into a replaceable value.
BINDING_PREPOSITIONS = {
    "for", "on", "at", "by", "in", "to", "from", "until", "about", "with",
    "into", "onto", "over", "under", "after", "before", "between",
}

# Modifiers that may precede a temporal value ("next Tuesday").
VALUE_MODIFIERS = {
    "next", "this", "that", "last", "first", "second", "third", "fourth",
    "fifth", "every", "each",
}

# Temporal proper nouns: recognized regardless of sentence position.
TEMPORAL_PROPER_WORDS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday", "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "today", "tomorrow", "tonight", "yesterday",
}

# Verb stems used to recognise verb inflections ("tastes", "enjoyed", "going").
VERB_STEMS = {
    "be", "have", "do", "go", "get", "make", "take", "come", "see", "know",
    "think", "want", "say", "tell", "give", "find", "feel", "look", "seem",
    "help", "need", "use", "work", "call", "send", "leave", "put", "mean",
    "taste", "sound", "love", "like", "keep", "let", "run", "try", "ask",
    "turn", "start", "stop", "show", "hear", "hold", "bring", "write",
    "read", "pay", "buy", "meet", "move", "live", "believe", "happen",
    "provide", "sit", "stand", "lose", "include", "continue", "set", "learn",
    "change", "lead", "understand", "watch", "follow", "create", "speak",
    "allow", "add", "spend", "grow", "open", "walk", "win", "offer",
    "remember", "consider", "appear", "wait", "serve", "expect", "build",
    "stay", "fall", "cut", "reach", "remain", "suggest", "raise", "pass",
    "sell", "require", "report", "decide", "pull", "return", "explain",
    "hope", "develop", "carry", "break", "receive", "agree", "support",
    "hit", "produce", "eat", "cover", "catch", "draw", "choose", "cause",
    "point", "listen", "realize", "place", "close", "involve", "increase",
    "describe", "join", "reduce", "enjoy", "accept", "become", "begin",
    "belong", "contain", "depend", "determine", "discover", "enforce",
    "ensure", "exist", "expand", "fail", "finish", "force", "identify",
    "ignore", "improve", "introduce", "maintain", "occur", "perform",
    "prefer", "prevent", "publish", "recognize", "repeat", "replace",
    "respond", "reveal", "satisfy", "solve", "suppose", "survive", "throw",
    "touch", "train", "treat", "visit", "wear", "wish", "proceed", "deploy",
    "cancel", "schedule", "review", "approve", "reject", "resolve", "apply",
    "upgrade", "downgrade", "install", "configure",
}

# Known unit nouns that may trail a number in a quantity phrase.
UNIT_NOUNS = {
    "copies", "items", "item", "units", "unit", "dollars", "cents", "euros",
    "pounds", "percent", "members", "people", "users", "laptops", "monitors",
    "files", "cases", "tickets", "tests", "bugs", "versions", "releases",
    "points", "degrees", "miles", "kilometers", "kilograms", "hours",
    "minutes", "seconds", "ms", "mb", "gb", "kb", "tb", "pages", "words",
    "lines", "repos", "servers", "nodes", "instances", "requests", "errors",
    "issues", "tasks", "sprints", "questions", "answers", "notes", "rows",
    "records", "entries", "orders", "invoices", "contracts", "emails",
    "messages", "calls", "reports", "documents", "photos", "videos", "pm",
    "am", "o'clock", "oclock",
}

# Negations that may sit immediately before a retracted verb.
NEGATION_TOKENS = {
    "not", "never", "no", "cannot", "cant", "don't", "dont", "doesn't",
    "doesnt", "didn't", "didnt", "won't", "wont", "shouldn't", "shouldnt",
    "wouldn't", "wouldnt", "couldn't", "couldnt", "isn't", "isnt",
    "aren't", "arent", "wasn't", "wasnt", "weren't", "werent", "hasn't",
    "hasnt", "haven't", "havent", "hadn't", "hadnt",
}

_PUNCT_ONLY = re.compile(r"^[^\w]+$", re.UNICODE)
_NUMBER_RE = re.compile(r"^\$?\d+(?:[.,]\d+)*$")
_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
_CLAUSE_BOUNDARY = re.compile(r"[.!?;:,]\s*|\n+")


def _strip_edges(token: str) -> str:
    """Strip surrounding punctuation and quotes from a raw token."""
    return token.strip(".,!?;:\"'()[]{}\u2014\u2013\u2026\u2018\u2019\u201c\u201d")


def _is_punct_only(token: str) -> bool:
    return bool(_PUNCT_ONLY.match(token))


def _is_verb_form(core: str) -> bool:
    """Closed-class approximation of verb morphology."""
    c = core.lower()
    if c in VERB_STEMS:
        return True
    if c.endswith("ies") and (c[:-3] + "y") in VERB_STEMS:
        return True
    if c.endswith("es") and c[:-2] in VERB_STEMS:
        return True
    if c.endswith("s") and c[:-1] in VERB_STEMS:
        return True
    if c.endswith("ed"):
        if c[:-2] in VERB_STEMS or c[:-1] in VERB_STEMS:
            return True
    if c.endswith("ing"):
        if c[:-3] in VERB_STEMS or (c[:-3] + "e") in VERB_STEMS:
            return True
    return False


def classify_value(core: str, at_sentence_start: bool = False) -> Optional[str]:
    """
    Classify a token core as a replaceable value.

    Returns one of: ``"number"``, ``"proper"``, ``"common"``, ``"func"``,
    ``"verb"`` or ``None`` when the token cannot be classified.
    """
    if not core:
        return None
    low = core.lower()
    if _NUMBER_RE.match(core) or _TIME_RE.match(core):
        return "number"
    if low in NUMBER_WORDS:
        return "number"
    if low in FUNCTION_WORDS or low in NEGATION_TOKENS:
        return "func"
    if _is_verb_form(core):
        return "verb"
    if low in TEMPORAL_PROPER_WORDS:
        return "proper"
    if core[0].isupper():
        # Capitalised but sentence-initial: ambiguous, so not a proper noun.
        return "common" if at_sentence_start else "proper"
    return "common"


def _is_unit_like(core: str) -> bool:
    """True when a token may legitimately trail a number in a quantity phrase."""
    if not core:
        return False
    low = core.lower()
    if low in UNIT_NOUNS:
        return True
    if low in FUNCTION_WORDS or low in NEGATION_TOKENS:
        return False
    if _is_verb_form(core):
        return False
    if not core.isalpha() or not core.islower():
        return False
    return len(core) > 2


class CorrectionIntentResolver:
    """
    Resolves spoken self-corrections in a transcript.

    Usage::

        resolver = CorrectionIntentResolver(language="en")
        text, nums, negs, applied = resolver.resolve(raw_transcript)
    """

    def __init__(self, language: str = ""):
        self.language = (language or "").lower()
        self.lang_prefix = self.language.split("-")[0].split("_")[0]
        self._triggers = self._build_triggers()

    # -- trigger table ------------------------------------------------------

    def _build_triggers(self) -> List[Tuple[str, str, bool, bool]]:
        """
        Returns ``(name, regex, is_explicit, requires_value_neighbours)``.

        Longer phrases are matched first so that ``no wait`` wins over a bare
        ``wait``.
        """
        table: List[Tuple[str, str, bool, bool]] = []
        for name, pattern, needs_values in EXPLICIT_TRIGGERS:
            table.append((name, pattern, True, needs_values))
        for name, pattern, needs_values in INTENSIFIER_TRIGGERS:
            table.append((name, pattern, False, needs_values))
        for name, pattern, needs_values in MULTILINGUAL_TRIGGERS.get(self.lang_prefix, []):
            table.append((name, pattern, True, needs_values))
        table.sort(key=lambda item: len(item[1]), reverse=True)
        return table

    # -- public API ---------------------------------------------------------

    def resolve(self, text: str) -> Tuple[str, List[str], List[str], List[str]]:
        """
        Resolve every self-correction in ``text``.

        Returns ``(resolved_text, retracted_numbers, retracted_negations, applied)``
        where ``retracted_numbers`` holds digit-only strings and
        ``retracted_negations`` holds the literal negation tokens that were
        intentionally removed (including tokens consumed inside a trigger
        phrase such as the ``no`` of ``no wait``).
        """
        if not text or not text.strip():
            return text, [], [], []

        working = text
        applied: List[str] = []
        trigger_negations: List[str] = []
        superseded_numbers: List[str] = []
        superseded_negations: List[str] = []

        # Bounded loop. Each pass resolves every trigger it finds, so a single
        # pass is normally sufficient; the loop guards against a pathological
        # re-trigger.
        for _ in range(4):
            tokens = self._tokenize(working)
            edits = self._find_edits(tokens, working)
            if not edits:
                break
            for edit in sorted(edits, key=lambda e: e["old_start"], reverse=True):
                working = (
                    working[:edit["old_start"]]
                    + edit["replacement"]
                    + working[edit["edit_end"]:]
                )
                applied.append(edit["label"])
                superseded_numbers.extend(edit["numbers"])
                superseded_negations.extend(edit["negations"])
            working = re.sub(r"[ \t]{2,}", " ", working)

        # Trigger phrases are consumed whole. Any protected token that lived
        # inside a trigger phrase (the "no" of "no wait", the "never" of
        # "never mind") must be reported as intentionally retracted, otherwise
        # FactGuard treats the consumed trigger as a dropped semantic negation
        # and silently reverts the whole correction.
        for name, pattern, _explicit, _needs in self._triggers:
            if not re.search(pattern, text, flags=re.IGNORECASE):
                continue
            trigger_negations.extend(self._protected_tokens_in(text, pattern))

        final_nums = self._collect_remaining(superseded_numbers, working, numeric=True)
        final_negs = self._collect_remaining(
            superseded_negations + trigger_negations, working, numeric=False
        )
        return working, final_nums, final_negs, applied

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> List[Tuple[str, int, int]]:
        """Return ``[(token, start_offset, end_offset)]`` for non-space runs."""
        return [(m.group(0), m.start(), m.end()) for m in re.finditer(r"\S+", text)]

    @staticmethod
    def _token_index_at(tokens: List[Tuple[str, int, int]], offset: int) -> Optional[int]:
        """Index of the token containing ``offset``."""
        for index, (_tok, start, end) in enumerate(tokens):
            if start <= offset < end:
                return index
        return None

    def _find_edits(
        self,
        tokens: List[Tuple[str, int, int]],
        text: str,
    ) -> List[Dict[str, object]]:
        """Locate every trigger in ``text`` and build the corresponding edit."""
        edits: List[Dict[str, object]] = []
        claimed: List[Tuple[int, int]] = []

        for name, pattern, is_explicit, needs_values in self._triggers:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                if not match.group(0).strip():
                    continue
                start_index = self._token_index_at(tokens, match.start())
                end_index = self._token_index_at(tokens, match.end() - 1)
                if start_index is None or end_index is None:
                    continue
                # Skip triggers already covered by a longer, higher-priority
                # trigger (e.g. the bare "wait" inside "no wait").
                if any(not (end_index < a or start_index > b) for a, b in claimed):
                    continue
                edit = self._build_edit(
                    tokens,
                    text,
                    start_index,
                    end_index,
                    name,
                    is_explicit,
                    needs_values,
                    match.group(0),
                )
                if edit is not None:
                    edits.append(edit)
                    claimed.append((start_index, end_index))

        # Two triggers can produce edits whose consumed ranges overlap (for
        # example "at 2 actually I mean 3"). Only the first one may apply.
        kept: List[Dict[str, object]] = []
        spans: List[Tuple[int, int]] = []
        for edit in sorted(edits, key=lambda e: (int(e["old_start"]), -int(e["edit_end"]))):
            span = (int(edit["old_start"]), int(edit["edit_end"]))
            if any(not (span[1] <= a or span[0] >= b) for a, b in spans):
                continue
            kept.append(edit)
            spans.append(span)
        return kept

    def _build_edit(
        self,
        tokens: List[Tuple[str, int, int]],
        text: str,
        trig_start: int,
        trig_end: int,
        name: str,
        is_explicit: bool,
        needs_values: bool,
        trigger_text: str,
    ) -> Optional[Dict[str, object]]:
        """Compute the replacement span for a single trigger, or None to skip."""
        trigger_end_offset = tokens[trig_end][2]

        # ---- locate the superseded span (backwards) ------------------------
        cursor = trig_start - 1
        while cursor >= 0 and _is_punct_only(tokens[cursor][0]):
            cursor -= 1
        if cursor < 0:
            return None

        negation_idx: Optional[int] = None
        old_start = cursor
        old_end = cursor + 1

        core_old = _strip_edges(tokens[cursor][0])
        old_class = classify_value(core_old, at_sentence_start=cursor == 0)

        # Negation retraction: "do not proceed -- actually, proceed".
        if old_class == "verb" and cursor - 1 >= 0:
            neg_core = _strip_edges(tokens[cursor - 1][0]).lower()
            if neg_core in NEGATION_TOKENS:
                negation_idx = cursor - 1
                old_start = negation_idx
                old_end = cursor + 1

        # Quantity phrase: "5 copies" -> number + unit noun.
        if negation_idx is None and old_class == "common" and cursor - 1 >= 0:
            prev_core = _strip_edges(tokens[cursor - 1][0])
            prev_class = classify_value(prev_core, at_sentence_start=cursor - 1 == 0)
            if prev_class == "number":
                old_start = cursor - 1
                old_end = cursor + 1
                old_class = "number"

        # Value modifier: "next Tuesday".
        if old_class == "proper" and cursor - 1 >= 0:
            prev_core = _strip_edges(tokens[cursor - 1][0]).lower()
            if prev_core in VALUE_MODIFIERS:
                old_start = cursor - 1
                old_end = cursor + 1

        # ---- negation retraction short-circuit ----------------------------
        # Handled before the new-span scan: the replacement must be the same
        # core word, so skipping over an intervening token would be wrong.
        if negation_idx is not None:
            new_cursor = trig_end + 1
            if new_cursor >= len(tokens):
                return None
            replacement_core = _strip_edges(tokens[new_cursor][0])
            if replacement_core.lower() != core_old.lower():
                return None
            superseded_text = " ".join(
                _strip_edges(tokens[i][0]) for i in range(old_start, old_end)
            )
            consumed_end = tokens[new_cursor][2]
            return {
                "old_start": tokens[old_start][1],
                "edit_end": max(trigger_end_offset, consumed_end),
                "replacement": " ".join(
                    _strip_edges(tokens[i][0]) for i in range(negation_idx + 1, old_end)
                ),
                "label": "Retracted spoken negation",
                "numbers": self._numbers_in(superseded_text),
                "negations": [n for n in NEGATION_TOKENS if n in superseded_text.lower()],
            }

        # ---- locate the replacement span (forwards) -----------------------
        new_cursor = trig_end + 1
        if new_cursor >= len(tokens):
            return self._maybe_clause_retraction(
                text, tokens, trig_start, trig_end, trigger_end_offset, name, old_start, old_end
            )
        new_start = new_cursor
        new_end = new_cursor + 1

        new_core = _strip_edges(tokens[new_cursor][0])
        new_class = classify_value(new_core, at_sentence_start=False)

        # Skip a single intervening function word / verb ("no wait call Jane").
        if new_class in ("func", "verb", None) and new_cursor + 1 < len(tokens):
            nxt_core = _strip_edges(tokens[new_cursor + 1][0])
            nxt_class = classify_value(nxt_core, at_sentence_start=False)
            if nxt_class in ("number", "proper", "common"):
                new_cursor += 1
                new_start = new_cursor
                new_end = new_cursor + 1
                new_core = nxt_core
                new_class = nxt_class

        # Quantity phrase on the replacement side: "3 laptops".
        if new_class == "number" and new_cursor + 1 < len(tokens):
            tail_core = _strip_edges(tokens[new_cursor + 1][0])
            if _is_unit_like(tail_core) and not self._starts_new_clause(tokens, new_cursor + 1):
                new_end = new_cursor + 2

        # "next Wednesday" style modifier on the replacement side.
        if new_class == "proper" and new_cursor + 1 < len(tokens):
            tail_core = _strip_edges(tokens[new_cursor + 1][0]).lower()
            if tail_core in VALUE_MODIFIERS:
                new_end = new_cursor + 2

        if new_class is None:
            return None

        # ---- value-neighbour guard ----------------------------------------
        if needs_values:
            prev_class = classify_value(core_old, at_sentence_start=(cursor == 0))
            if prev_class not in ("number", "proper", "common"):
                return None
            if new_class not in ("number", "proper", "common"):
                return None

        # ---- compatibility gate -------------------------------------------
        if not self._compatible(old_class, new_class, is_explicit, tokens, old_start):
            return None

        replacement = " ".join(
            _strip_edges(tokens[i][0]) for i in range(new_start, new_end)
        )
        if not replacement.strip():
            return None

        superseded_text = " ".join(
            _strip_edges(tokens[i][0]) for i in range(old_start, old_end)
        )

        # The replacement span sits *after* the trigger, so it has to be
        # consumed from its original position as well. Otherwise the new
        # value would appear twice: once in place and once in the old slot.
        consumed_end = tokens[new_end - 1][2]

        return {
            "old_start": tokens[old_start][1],
            "edit_end": max(trigger_end_offset, consumed_end),
            "replacement": replacement,
            "label": f"Resolved spoken self-correction ({trigger_text.strip()})",
            "numbers": self._numbers_in(superseded_text),
            "negations": [n for n in NEGATION_TOKENS if n in superseded_text.lower()],
        }

    def _maybe_clause_retraction(
        self,
        text: str,
        tokens: List[Tuple[str, int, int]],
        trig_start: int,
        trig_end: int,
        trigger_end_offset: int,
        name: str,
        old_start: int,
        old_end: int,
    ) -> Optional[Dict[str, object]]:
        """
        Handle a trigger that has no value after it.

        Only explicit retraction markers ("never mind") qualify; they drop the
        abandoned clause that precedes them.
        """
        if name not in ("never_mind", "laisse_tombe", "da_igual"):
            return None

        trigger_offset = tokens[trig_start][1]
        prefix = text[:trigger_offset]
        boundary = None
        for match in _CLAUSE_BOUNDARY.finditer(prefix):
            boundary = match.end()
        clause_start = boundary if boundary is not None else 0

        # Nothing to retract if the clause is only the trigger itself.
        if clause_start >= trigger_offset:
            return None

        superseded_text = text[clause_start:trigger_end_offset]
        return {
            "old_start": clause_start,
            "edit_end": trigger_end_offset,
            "replacement": "",
            "label": "Retracted abandoned clause",
            "numbers": self._numbers_in(superseded_text),
            "negations": [n for n in NEGATION_TOKENS if n in superseded_text.lower()],
        }

    @staticmethod
    def _starts_new_clause(tokens: List[Tuple[str, int, int]], index: int) -> bool:
        """True when the token at ``index`` opens a new clause (so it is not a unit)."""
        if index >= len(tokens):
            return True
        core = _strip_edges(tokens[index][0]).lower()
        if core in {"and", "but", "or", "then", "also", "so", "because", "which", "that"}:
            return True
        if core.endswith((".", "!", "?")):
            return True
        return False

    def _compatible(
        self,
        old_class: Optional[str],
        new_class: Optional[str],
        is_explicit: bool,
        tokens: List[Tuple[str, int, int]],
        old_start: int,
    ) -> bool:
        """
        Decide whether the superseded span may legitimately be replaced.

        This is the meaning-preservation gate. It rejects the cases where a
        marker word was used as an intensifier rather than a correction.
        """
        if old_class is None or new_class is None:
            return False

        # A function word can never be the superseded value.
        if old_class == "func":
            return False
        if new_class == "func":
            return False

        # A verb can only be superseded in the explicit negation-retraction
        # path, which is handled before this gate.
        if old_class == "verb" or new_class == "verb":
            return False

        if old_class == "number":
            return new_class == "number"

        if old_class == "proper":
            return new_class in ("proper", "number")

        # old_class == "common"
        if new_class in ("proper", "number"):
            return True
        if not is_explicit:
            # Intensifier marker: a common noun may only be superseded when it
            # is bound by a preposition. Without that binding the marker was
            # almost certainly an intensifier, not a correction.
            if old_start - 1 >= 0:
                prev = _strip_edges(tokens[old_start - 1][0]).lower()
                if prev in BINDING_PREPOSITIONS:
                    return True
            return False
        # Explicit marker: the speaker announced the correction, so a common
        # noun may be superseded by another common noun.
        return True

    @staticmethod
    def _numbers_in(text: str) -> List[str]:
        """Digit-only forms of the numbers contained in ``text``."""
        found = []
        for match in re.findall(r"\$?\d+(?:,\d+)*(?:\.\d+)?", text):
            digits = re.sub(r"[^\d]", "", match)
            if digits:
                found.append(digits)
        return found

    @staticmethod
    def _protected_tokens_in(text: str, pattern: str) -> List[str]:
        """Negation tokens that occur inside occurrences of ``pattern``."""
        found: List[str] = []
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            chunk = match.group(0).lower()
            for neg in NEGATION_TOKENS:
                if re.search(r"\b" + re.escape(neg) + r"\b", chunk):
                    found.append(neg)
        return found

    @staticmethod
    def _collect_remaining(
        candidates: List[str],
        final_text: str,
        numeric: bool,
    ) -> List[str]:
        """
        Keep only candidates that no longer appear in the final text.

        A candidate that survived is not a retraction and must not be
        reported to FactGuard.
        """
        remaining: List[str] = []
        for candidate in candidates:
            if numeric:
                digits = re.sub(r"[^\d]", "", candidate)
                if digits and digits not in re.sub(r"[^\d]", "", final_text):
                    remaining.append(digits)
            else:
                if candidate.lower() not in final_text.lower():
                    remaining.append(candidate)
        seen = set()
        ordered = []
        for item in remaining:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                ordered.append(item)
        return ordered
