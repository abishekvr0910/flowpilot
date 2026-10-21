"""
FlowPilot Real-Voice Multilingual Evaluation Corpus & Schema
Implements PR 2 evaluation schema for:
- English (en), Hindi (hi), Tamil (ta), Malayalam (ml)
- Consented evaluation audio manifest verification
- Separate raw spoken reference vs. desired formatted writing reference
- Developer identifiers, mixed-script, numbers, dates, negations, and noise groups
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class CorpusItem:
    item_id: str
    language: str                      # "en" | "hi" | "ta" | "ml"
    group: str                         # "clean" | "developer_code" | "mixed_script" | "low_volume" | "noise" | "quantities"
    spoken_reference: str              # Verbatim what was spoken
    formatted_reference: str           # Approved desired writing output
    speaker_id: str
    consent_verified: bool = True      # Only consented evaluation audio is permitted
    audio_file: Optional[str] = None   # Relative path to WAV fixture if available
    duration_sec: float = 0.0
    critical_entities: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorpusItem":
        return cls(
            item_id=data["item_id"],
            language=data["language"],
            group=data["group"],
            spoken_reference=data["spoken_reference"],
            formatted_reference=data["formatted_reference"],
            speaker_id=data["speaker_id"],
            consent_verified=data.get("consent_verified", True),
            audio_file=data.get("audio_file"),
            duration_sec=float(data.get("duration_sec", 0.0)),
            critical_entities=list(data.get("critical_entities", []))
        )

class RealVoiceCorpus:
    """Manages evaluation manifests, filtering, and integrity validation for speech benchmarks."""

    def __init__(self, items: Optional[List[CorpusItem]] = None):
        self.items: List[CorpusItem] = items or []

    def add_item(self, item: CorpusItem):
        self.items.append(item)

    def filter_by_language(self, language: str) -> List[CorpusItem]:
        return [item for item in self.items if item.language == language]

    def filter_by_group(self, group: str) -> List[CorpusItem]:
        return [item for item in self.items if item.group == group]

    def validate_integrity(self) -> Tuple[bool, List[str]]:
        """Verifies schema conformance, consent, and non-empty reference strings."""
        errors = []
        valid_languages = {"en", "hi", "ta", "ml"}

        for item in self.items:
            if item.language not in valid_languages:
                errors.append(f"[{item.item_id}] Invalid language '{item.language}'. Must be one of {valid_languages}")
            if not item.spoken_reference or not item.spoken_reference.strip():
                errors.append(f"[{item.item_id}] Empty spoken_reference string.")
            if not item.formatted_reference or not item.formatted_reference.strip():
                errors.append(f"[{item.item_id}] Empty formatted_reference string.")
            if not item.consent_verified:
                errors.append(f"[{item.item_id}] Unverified consent flag. Only consented evaluation data allowed.")
            if item.audio_file and not os.path.isabs(item.audio_file):
                # Check path if provided
                pass

        return len(errors) == 0, errors

    def save_manifest(self, path: Path):
        """Saves corpus manifest to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [item.to_dict() for item in self.items]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_manifest(cls, path: Path) -> "RealVoiceCorpus":
        """Loads corpus manifest from JSON file."""
        if not path.is_file():
            raise FileNotFoundError(f"Corpus manifest not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = [CorpusItem.from_dict(d) for d in data]
        return cls(items)

def get_dev_smoke_corpus() -> RealVoiceCorpus:
    """
    Returns the initial 40 development smoke utterances:
    10 per priority language (English, Hindi, Tamil, Malayalam)
    Covering: clean speech, code tokens, mixed-script, quantities, and negations.
    """
    items = [
        # --- ENGLISH (en) ---
        CorpusItem(
            item_id="en-01-clean",
            language="en",
            group="clean",
            spoken_reference="the meeting is scheduled for next monday morning at nine thirty",
            formatted_reference="The meeting is scheduled for next Monday morning at 9:30.",
            speaker_id="dev-spk-en-01",
            duration_sec=3.2,
            critical_entities=["monday", "9:30"]
        ),
        CorpusItem(
            item_id="en-02-code",
            language="en",
            group="developer_code",
            spoken_reference="git commit dash m fix parse hotkey string in hotkey service dot py",
            formatted_reference="git commit -m 'fix parse_hotkey_string in hotkey_service.py'",
            speaker_id="dev-spk-en-01",
            duration_sec=4.1,
            critical_entities=["git", "-m", "parse_hotkey_string", "hotkey_service.py"]
        ),
        CorpusItem(
            item_id="en-03-negation",
            language="en",
            group="clean",
            spoken_reference="we did not push the binary release because tests failed",
            formatted_reference="We did not push the binary release because tests failed.",
            speaker_id="dev-spk-en-01",
            duration_sec=3.5,
            critical_entities=["not", "failed"]
        ),
        CorpusItem(
            item_id="en-04-quantities",
            language="en",
            group="quantities",
            spoken_reference="the latency dropped by twenty five point four percent from one point five seconds to eight hundred milliseconds",
            formatted_reference="The latency dropped by 25.4% from 1.5s to 800ms.",
            speaker_id="dev-spk-en-01",
            duration_sec=5.0,
            critical_entities=["25.4%", "1.5s", "800ms"]
        ),
        CorpusItem(
            item_id="en-05-code-url",
            language="en",
            group="developer_code",
            spoken_reference="check the pull request at https github com flowpilot releases tag v three point one point zero",
            formatted_reference="Check the pull request at https://github.com/flowpilot/releases/tag/v3.1.0",
            speaker_id="dev-spk-en-01",
            duration_sec=5.5,
            critical_entities=["https://github.com", "v3.1.0"]
        ),
        CorpusItem(
            item_id="en-06-noise",
            language="en",
            group="noise",
            spoken_reference="please reload the ctranslate two runtime on cpu int eight",
            formatted_reference="Please reload the CTranslate2 runtime on CPU int8.",
            speaker_id="dev-spk-en-01",
            duration_sec=3.6,
            critical_entities=["CTranslate2", "CPU", "int8"]
        ),
        CorpusItem(
            item_id="en-07-lowvol",
            language="en",
            group="low_volume",
            spoken_reference="do not delete the cached model directory",
            formatted_reference="Do not delete the cached model directory.",
            speaker_id="dev-spk-en-01",
            duration_sec=2.9,
            critical_entities=["not", "model"]
        ),
        CorpusItem(
            item_id="en-08-code",
            language="en",
            group="developer_code",
            spoken_reference="set variable max retries to three and timeout to five seconds",
            formatted_reference="Set variable max_retries = 3 and timeout = 5s.",
            speaker_id="dev-spk-en-01",
            duration_sec=3.8,
            critical_entities=["max_retries", "3", "5s"]
        ),
        CorpusItem(
            item_id="en-09-clean",
            language="en",
            group="clean",
            spoken_reference="voice dictation requires zero cloud egress and total privacy",
            formatted_reference="Voice dictation requires zero cloud egress and total privacy.",
            speaker_id="dev-spk-en-01",
            duration_sec=3.7,
            critical_entities=["zero", "privacy"]
        ),
        CorpusItem(
            item_id="en-10-quantities",
            language="en",
            group="quantities",
            spoken_reference="invoice number forty two for seven hundred and fifty dollars was paid on october twenty first",
            formatted_reference="Invoice #42 for $750 was paid on October 21st.",
            speaker_id="dev-spk-en-01",
            duration_sec=4.6,
            critical_entities=["#42", "$750", "October 21st"]
        ),

        # --- HINDI (hi) ---
        CorpusItem(
            item_id="hi-01-clean",
            language="hi",
            group="clean",
            spoken_reference="आज का काम समय पर पूरा हो गया है",
            formatted_reference="आज का काम समय पर पूरा हो गया है।",
            speaker_id="dev-spk-hi-01",
            duration_sec=2.8,
            critical_entities=["काम", "समय"]
        ),
        CorpusItem(
            item_id="hi-02-mixed",
            language="hi",
            group="mixed_script",
            spoken_reference="server restart करने के बाद python script सही चल रही है",
            formatted_reference="Server restart करने के बाद Python script सही चल रही है।",
            speaker_id="dev-spk-hi-01",
            duration_sec=4.2,
            critical_entities=["Server", "restart", "Python", "script"]
        ),
        CorpusItem(
            item_id="hi-03-negation",
            language="hi",
            group="clean",
            spoken_reference="यह फ़ाइल किसी भी सर्वर पर नहीं भेजी जाएगी",
            formatted_reference="यह फ़ाइल किसी भी सर्वर पर नहीं भेजी जाएगी।",
            speaker_id="dev-spk-hi-01",
            duration_sec=3.5,
            critical_entities=["नहीं", "फ़ाइल"]
        ),
        CorpusItem(
            item_id="hi-04-quantities",
            language="hi",
            group="quantities",
            spoken_reference="कुल पच्चीस हज़ार रुपये खाते में जमा किए गए",
            formatted_reference="कुल ₹25,000 खाते में जमा किए गए।",
            speaker_id="dev-spk-hi-01",
            duration_sec=3.9,
            critical_entities=["₹25,000"]
        ),
        CorpusItem(
            item_id="hi-05-code",
            language="hi",
            group="developer_code",
            spoken_reference="database connection timeout को दस सेकंड पर set करें",
            formatted_reference="Database connection timeout को 10s पर set करें।",
            speaker_id="dev-spk-hi-01",
            duration_sec=4.0,
            critical_entities=["Database", "timeout", "10s"]
        ),
        CorpusItem(
            item_id="hi-06-noise",
            language="hi",
            group="noise",
            spoken_reference="कृपया माइक का volume थोड़ा बढ़ाएं",
            formatted_reference="कृपया माइक का volume थोड़ा बढ़ाएं।",
            speaker_id="dev-spk-hi-01",
            duration_sec=3.1,
            critical_entities=["माइक", "volume"]
        ),
        CorpusItem(
            item_id="hi-07-lowvol",
            language="hi",
            group="low_volume",
            spoken_reference="हम किसी भी परिस्थिति में पासवर्ड शेयर नहीं करेंगे",
            formatted_reference="हम किसी भी परिस्थिति में पासवर्ड शेयर नहीं करेंगे।",
            speaker_id="dev-spk-hi-01",
            duration_sec=3.6,
            critical_entities=["नहीं", "पासवर्ड"]
        ),
        CorpusItem(
            item_id="hi-08-mixed",
            language="hi",
            group="mixed_script",
            spoken_reference="नया feature master branch में merge हो चुका है",
            formatted_reference="नया feature master branch में merge हो चुका है।",
            speaker_id="dev-spk-hi-01",
            duration_sec=3.8,
            critical_entities=["feature", "master", "branch", "merge"]
        ),
        CorpusItem(
            item_id="hi-09-clean",
            language="hi",
            group="clean",
            spoken_reference="सभी परीक्षण सफलतापूर्वक पास हो गए हैं",
            formatted_reference="सभी परीक्षण सफलतापूर्वक पास हो गए हैं।",
            speaker_id="dev-spk-hi-01",
            duration_sec=3.2,
            critical_entities=["परीक्षण", "पास"]
        ),
        CorpusItem(
            item_id="hi-10-quantities",
            language="hi",
            group="quantities",
            spoken_reference="पंद्रह अगस्त उन्नीस सौ सैंतालीस को भारत आज़ाद हुआ",
            formatted_reference="15 अगस्त 1947 को भारत आज़ाद हुआ।",
            speaker_id="dev-spk-hi-01",
            duration_sec=4.1,
            critical_entities=["15", "1947", "भारत"]
        ),

        # --- TAMIL (ta) ---
        CorpusItem(
            item_id="ta-01-clean",
            language="ta",
            group="clean",
            spoken_reference="இன்றைய பணிகள் அனைத்தும் சரியாக முடிந்துவிட்டன",
            formatted_reference="இன்றைய பணிகள் அனைத்தும் சரியாக முடிந்துவிட்டன.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.4,
            critical_entities=["பணிகள்"]
        ),
        CorpusItem(
            item_id="ta-02-mixed",
            language="ta",
            group="mixed_script",
            spoken_reference="react frontend build இப்போது சரியாக இயங்குகிறது",
            formatted_reference="React frontend build இப்போது சரியாக இயங்குகிறது.",
            speaker_id="dev-spk-ta-01",
            duration_sec=4.0,
            critical_entities=["React", "frontend", "build"]
        ),
        CorpusItem(
            item_id="ta-03-negation",
            language="ta",
            group="clean",
            spoken_reference="இந்த தரவு இணையத்தில் பகிரப்படவில்லை",
            formatted_reference="இந்த தரவு இணையத்தில் பகிரப்படவில்லை.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.5,
            critical_entities=["பகிரப்படவில்லை"]
        ),
        CorpusItem(
            item_id="ta-04-quantities",
            language="ta",
            group="quantities",
            spoken_reference="மொத்தம் ஐந்நூறு பயனர்கள் பதிவு செய்துள்ளனர்",
            formatted_reference="மொத்தம் 500 பயனர்கள் பதிவு செய்துள்ளனர்.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.8,
            critical_entities=["500", "பயனர்கள்"]
        ),
        CorpusItem(
            item_id="ta-05-code",
            language="ta",
            group="developer_code",
            spoken_reference="fastapi router path ஐ சரிபார்க்கவும்",
            formatted_reference="FastAPI router path ஐ சரிபார்க்கவும்.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.2,
            critical_entities=["FastAPI", "router", "path"]
        ),
        CorpusItem(
            item_id="ta-06-noise",
            language="ta",
            group="noise",
            spoken_reference="குரல் பதிவு ஒலி தெளிவாக கேட்கிறது",
            formatted_reference="குரல் பதிவு ஒலி தெளிவாக கேட்கிறது.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.0,
            critical_entities=["குரல்", "பதிவு"]
        ),
        CorpusItem(
            item_id="ta-07-lowvol",
            language="ta",
            group="low_volume",
            spoken_reference="இரகசிய குறியீட்டை யாரிடமும் சொல்ல வேண்டாம்",
            formatted_reference="இரகசிய குறியீட்டை யாரிடமும் சொல்ல வேண்டாம்.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.3,
            critical_entities=["வேண்டாம்"]
        ),
        CorpusItem(
            item_id="ta-08-mixed",
            language="ta",
            group="mixed_script",
            spoken_reference="docker container ஐ restart செய்யவும்",
            formatted_reference="Docker container ஐ restart செய்யவும்.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.4,
            critical_entities=["Docker", "container", "restart"]
        ),
        CorpusItem(
            item_id="ta-09-clean",
            language="ta",
            group="clean",
            spoken_reference="தமிழ் மொழி குரல் பதிவு வெற்றிகரமாக செயல்படுகிறது",
            formatted_reference="தமிழ் மொழி குரல் பதிவு வெற்றிகரமாக செயல்படுகிறது.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.8,
            critical_entities=["தமிழ்", "குரல்"]
        ),
        CorpusItem(
            item_id="ta-10-quantities",
            language="ta",
            group="quantities",
            spoken_reference="இரண்டாயிரத்து இருபத்தாறாம் ஆண்டு அக்டோபர் மாதம்",
            formatted_reference="2026 ஆம் ஆண்டு அக்டோபர் மாதம்.",
            speaker_id="dev-spk-ta-01",
            duration_sec=3.7,
            critical_entities=["2026", "அக்டோபர்"]
        ),

        # --- MALAYALAM (ml) ---
        CorpusItem(
            item_id="ml-01-clean",
            language="ml",
            group="clean",
            spoken_reference="ഇന്നത്തെ ജോലികൾ എല്ലാം പൂർത്തിയായി",
            formatted_reference="ഇന്നത്തെ ജോലികൾ എല്ലാം പൂർത്തിയായി.",
            speaker_id="dev-spk-ml-01",
            duration_sec=2.9,
            critical_entities=["ജോലികൾ"]
        ),
        CorpusItem(
            item_id="ml-02-mixed",
            language="ml",
            group="mixed_script",
            spoken_reference="nodejs application crash ആയിട്ടുണ്ട്",
            formatted_reference="Node.js application crash ആയിട്ടുണ്ട്.",
            speaker_id="dev-spk-ml-01",
            duration_sec=3.4,
            critical_entities=["Node.js", "application", "crash"]
        ),
        CorpusItem(
            item_id="ml-03-negation",
            language="ml",
            group="clean",
            spoken_reference="ഈ ഡാറ്റ പുറത്തേക്ക് അയച്ചിട്ടില്ല",
            formatted_reference="ഈ ഡാറ്റ പുറത്തേക്ക് അയച്ചിട്ടില്ല.",
            speaker_id="dev-spk-ml-01",
            duration_sec=3.1,
            critical_entities=["ഡാറ്റ", "അയച്ചിട്ടില്ല"]
        ),
        CorpusItem(
            item_id="ml-04-quantities",
            language="ml",
            group="quantities",
            spoken_reference="നൂറ്റമ്പത് രൂപ മാത്രമാണ് ഇതിന്റെ ചിലവ്",
            formatted_reference="₹150 മാത്രമാണ് ഇതിന്റെ ചിലവ്.",
            speaker_id="dev-spk-ml-01",
            duration_sec=3.3,
            critical_entities=["₹150"]
        ),
        CorpusItem(
            item_id="ml-05-code",
            language="ml",
            group="developer_code",
            spoken_reference="postgresql database query പരിശോധിച്ച് നോക്കുക",
            formatted_reference="PostgreSQL database query പരിശോധിച്ച് നോക്കുക.",
            speaker_id="dev-spk-ml-01",
            duration_sec=3.9,
            critical_entities=["PostgreSQL", "database", "query"]
        ),
        CorpusItem(
            item_id="ml-06-noise",
            language="ml",
            group="noise",
            spoken_reference="ശബ്ദം വ്യക്തമായി കേൾക്കുന്നുണ്ട്",
            formatted_reference="ശബ്ദം വ്യക്തമായി കേൾക്കുന്നുണ്ട്.",
            speaker_id="dev-spk-ml-01",
            duration_sec=2.7,
            critical_entities=["ശബ്ദം"]
        ),
        CorpusItem(
            item_id="ml-07-lowvol",
            language="ml",
            group="low_volume",
            spoken_reference="പാസ്‌വേഡ് ആർക്കും നൽകരുത്",
            formatted_reference="പാസ്‌വേഡ് ആർക്കും നൽകരുത്.",
            speaker_id="dev-spk-ml-01",
            duration_sec=2.8,
            critical_entities=["പാസ്‌വേഡ്", "നൽകരുത്"]
        ),
        CorpusItem(
            item_id="ml-08-mixed",
            language="ml",
            group="mixed_script",
            spoken_reference="kubernetes cluster deploy ചെയ്തു കഴിഞ്ഞു",
            formatted_reference="Kubernetes cluster deploy ചെയ്തു കഴിഞ്ഞു.",
            speaker_id="dev-spk-ml-01",
            duration_sec=3.7,
            critical_entities=["Kubernetes", "cluster", "deploy"]
        ),
        CorpusItem(
            item_id="ml-09-clean",
            language="ml",
            group="clean",
            spoken_reference="മലയാളം സംഭാഷണം കൃത്യമായി തിരിച്ചറിയുന്നു",
            formatted_reference="മലയാളം സംഭാഷണം കൃത്യമായി തിരിച്ചറിയുന്നു.",
            speaker_id="dev-spk-ml-01",
            duration_sec=3.5,
            critical_entities=["മലയാളം", "സംഭാഷണം"]
        ),
        CorpusItem(
            item_id="ml-10-quantities",
            language="ml",
            group="quantities",
            spoken_reference="രണ്ടായിരത്തി ഇരുപത്താറ് വർഷം",
            formatted_reference="2026 വർഷം.",
            speaker_id="dev-spk-ml-01",
            duration_sec=2.9,
            critical_entities=["2026"]
        ),
    ]
    return RealVoiceCorpus(items)
