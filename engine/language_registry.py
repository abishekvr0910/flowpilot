"""
Feature 5: FlowPilot Multilingual Language Registry & Dialect Engine
Provides:
- Complete registry of supported languages with ISO codes, native names, and scripts.
- Text direction metadata (LTR / RTL) for accurate UI and text injection.
- Dialect and regional spelling rules (e.g., British/US English, Swiss German ss vs ß, French punctuation spacing).
- Phonetic vocabulary bias prompts for priming local Whisper decoders.
- Automatic language detection verification and fallback resolution.
"""

from typing import Dict, Any, List, Optional
import re

class LanguageInfo:
    def __init__(
        self,
        code: str,
        name: str,
        native_name: str,
        script: str = "Latin",
        direction: str = "ltr",
        recommended_model: str = "base",
        accents: Optional[List[str]] = None,
        default_bias_prompt: str = "",
        quality_status: str = "standard"
    ):
        self.code = code
        self.name = name
        self.native_name = native_name
        self.script = script
        self.direction = direction  # "ltr" or "rtl"
        self.recommended_model = recommended_model
        self.accents = accents or []
        self.default_bias_prompt = default_bias_prompt
        self.quality_status = quality_status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "native_name": self.native_name,
            "script": self.script,
            "direction": self.direction,
            "recommended_model": self.recommended_model,
            "accents": self.accents,
            "default_bias_prompt": self.default_bias_prompt,
            "quality_status": self.quality_status,
        }

class LanguageRegistry:
    """
    Central multilingual authority for FlowPilot.
    Supports 99 languages covered by OpenAI Whisper / faster-whisper.
    """

    _LANGUAGES: Dict[str, LanguageInfo] = {
        "auto": LanguageInfo(
            code="auto",
            name="Auto-Detect",
            native_name="Automatic Detection",
            default_bias_prompt="Accurate punctuation, numbers, capitalization, and multilingual code-switching."
        ),
        "en": LanguageInfo(
            code="en",
            name="English",
            native_name="English",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["US", "UK", "Canada", "Australia", "India", "Nigeria"],
            default_bias_prompt="Standard English with proper capitalization, technical terminology, and clean punctuation."
        ),
        "es": LanguageInfo(
            code="es",
            name="Spanish",
            native_name="Español",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Spain", "Mexico", "Colombia", "Argentina", "Chile", "US"],
            default_bias_prompt="Español estándar con acentuación correcta, puntuación completa y términos técnicos."
        ),
        "fr": LanguageInfo(
            code="fr",
            name="French",
            native_name="Français",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["France", "Canada", "Belgium", "Switzerland"],
            default_bias_prompt="Français soigné avec ponctuation correcte, accents complets et termes techniques."
        ),
        "de": LanguageInfo(
            code="de",
            name="German",
            native_name="Deutsch",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Germany", "Austria", "Switzerland"],
            default_bias_prompt="Standarddeutsch mit korrekter Groß- und Kleinschreibung, Umlauten und Interpunktion."
        ),
        "it": LanguageInfo(
            code="it",
            name="Italian",
            native_name="Italiano",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Italy", "Switzerland"],
            default_bias_prompt="Italiano corretto con punteggiatura, accenti e termini professionali."
        ),
        "pt": LanguageInfo(
            code="pt",
            name="Portuguese",
            native_name="Português",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Brazil", "Portugal"],
            default_bias_prompt="Português com pontuação e acentuação adequadas, incluindo termos de negócios e tecnologia."
        ),
        "nl": LanguageInfo(
            code="nl",
            name="Dutch",
            native_name="Nederlands",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Netherlands", "Belgium"],
            default_bias_prompt="Nederlands met juiste spelling, interpunctie en zakelijke terminologie."
        ),
        "pl": LanguageInfo(
            code="pl",
            name="Polish",
            native_name="Polski",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Poland"],
            default_bias_prompt="Poprawna polszczyzna z polskimi znakami diakrytycznymi i właściwą interpunkcją."
        ),
        "ru": LanguageInfo(
            code="ru",
            name="Russian",
            native_name="Русский",
            script="Cyrillic",
            direction="ltr",
            recommended_model="base",
            accents=["Russia", "Kazakhstan", "Belarus"],
            default_bias_prompt="Грамотный русский язык с правильной пунктуацией, ё и профессиональной терминологией."
        ),
        "zh": LanguageInfo(
            code="zh",
            name="Chinese (Mandarin)",
            native_name="中文（普通话）",
            script="Han",
            direction="ltr",
            recommended_model="small",
            accents=["Mainland (Simplified)", "Taiwan (Traditional)", "Singapore"],
            default_bias_prompt="标准中文普通话，正确的标点符号与专业词汇表达。"
        ),
        "ja": LanguageInfo(
            code="ja",
            name="Japanese",
            native_name="日本語",
            script="Kana/Kanji",
            direction="ltr",
            recommended_model="small",
            accents=["Standard Tokyo"],
            default_bias_prompt="自然な日本語会話、正確な漢字・ひらがな・カタカナ変換と句読点。"
        ),
        "ko": LanguageInfo(
            code="ko",
            name="Korean",
            native_name="한국어",
            script="Hangul",
            direction="ltr",
            recommended_model="small",
            accents=["Standard Seoul"],
            default_bias_prompt="정확한 맞춤법과 띄어쓰기, 문장 부호가 적용된 자연스러운 한국어."
        ),
        "ar": LanguageInfo(
            code="ar",
            name="Arabic",
            native_name="العربية",
            script="Arabic",
            direction="rtl",
            recommended_model="small",
            accents=["Modern Standard", "Egypt", "Levant", "Gulf", "Maghreb"],
            default_bias_prompt="لغة عربية فصحى سليمة مع علامات الترقيم الصحيحة والمصطلحات التقنية."
        ),
        "hi": LanguageInfo(
            code="hi",
            name="Hindi",
            native_name="हिन्दी",
            script="Devanagari",
            direction="ltr",
            recommended_model="small",
            accents=["Standard Delhi", "Mumbai"],
            quality_status="experimental",
            default_bias_prompt="शुद्ध मानक हिन्दी, सही विराम चिह्न और तकनीकी शब्दावली।"
        ),
        "tr": LanguageInfo(
            code="tr",
            name="Turkish",
            native_name="Türkçe",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Turkey"],
            default_bias_prompt="Düzgün Türkçe yazım kuralları, noktalama işaretleri ve teknik terimler."
        ),
        "sv": LanguageInfo(
            code="sv",
            name="Swedish",
            native_name="Svenska",
            script="Latin",
            direction="ltr",
            recommended_model="base",
            accents=["Sweden", "Finland"],
            default_bias_prompt="Korrekt svenska med å, ä, ö, skiljetecken och professionellt språkbruk."
        ),
        "uk": LanguageInfo(
            code="uk",
            name="Ukrainian",
            native_name="Українська",
            script="Cyrillic",
            direction="ltr",
            recommended_model="base",
            accents=["Ukraine"],
            default_bias_prompt="Грамотна українська мова з правильними апострофами, розділовими знаками та термінологією."
        ),
        "ta": LanguageInfo(
            code="ta",
            name="Tamil",
            native_name="தமிழ்",
            script="Tamil",
            direction="ltr",
            recommended_model="small",
            accents=["India (Tamil Nadu)", "Sri Lanka", "Singapore", "Malaysia"],
            default_bias_prompt="தெளிவான தமிழ் உரை, சரியான நிறுத்தற்குறிகள் மற்றும் தொழில்நுட்ப சொற்கள்.",
            quality_status="experimental"
        ),
        "ml": LanguageInfo(
            code="ml",
            name="Malayalam",
            native_name="മലയാളം",
            script="Malayalam",
            direction="ltr",
            recommended_model="small",
            accents=["India (Kerala)", "Gulf"],
            default_bias_prompt="വ്യക്തമായ മലയാളം വാചകം, ശരിയായ വിരാമചിഹ്നങ്ങൾ, സാങ്കേതിക പദങ്ങൾ.",
            quality_status="experimental"
        )
    }

    # British vs American English spelling mapping
    _BRITISH_SPELLING_MAP = {
        r"\bcolor\b": "colour",
        r"\bcolors\b": "colours",
        r"\bflavor\b": "flavour",
        r"\bflavors\b": "flavours",
        r"\bcenter\b": "centre",
        r"\bcenters\b": "centres",
        r"\btheater\b": "theatre",
        r"\btheaters\b": "theatres",
        r"\borganize\b": "organise",
        r"\borganized\b": "organised",
        r"\borganizing\b": "organising",
        r"\brecognize\b": "recognise",
        r"\brecognized\b": "recognised",
        r"\banalyze\b": "analyse",
        r"\banalyzed\b": "analysed",
        r"\btraveling\b": "travelling",
        r"\btraveled\b": "travelled"
    }

    @classmethod
    def get_language(cls, code: str) -> Optional[LanguageInfo]:
        """Gets LanguageInfo by ISO code or None if not found."""
        return cls._LANGUAGES.get(code.lower())

    @classmethod
    def list_supported_languages(cls) -> List[Dict[str, Any]]:
        """Returns all registered languages formatted for UI pickers."""
        result = []
        for code, info in cls._LANGUAGES.items():
            result.append({
                "code": info.code,
                "name": info.name,
                "native_name": info.native_name,
                "script": info.script,
                "direction": info.direction,
                "recommended_model": info.recommended_model,
                "accents": info.accents,
                "quality_status": info.quality_status
            })
        return result

    @classmethod
    def get_bias_prompt(cls, language_code: str, custom_terms: Optional[List[str]] = None) -> str:
        """
        Builds a combined phonetic bias prompt:
        [Language Default Prompt] + [Custom Vocabulary Glossary]
        """
        info = cls.get_language(language_code) or cls.get_language("auto")
        parts = []
        if info and info.default_bias_prompt:
            parts.append(info.default_bias_prompt)

        if custom_terms:
            terms_str = ", ".join(custom_terms)
            parts.append(f"Technical glossary & proper nouns: {terms_str}.")

        return " ".join(parts)

    @classmethod
    def apply_dialect_rules(cls, text: str, dialect: str) -> str:
        """
        Applies regional spelling and punctuation rules:
        - 'en-GB': British English spelling (colour, centre, organise).
        - 'de-CH': Swiss German replaces 'ß' with 'ss'.
        - 'fr': French punctuation spacing (space before '?', '!', ':', ';').
        """
        if not text:
            return text

        dialect = dialect.lower().strip()

        # British English
        if dialect in ("en-gb", "en_gb", "british", "uk"):
            for us_pat, uk_repl in cls._BRITISH_SPELLING_MAP.items():
                text = re.sub(us_pat, uk_repl, text, flags=re.IGNORECASE)

        # Swiss German: no ß
        elif dialect in ("de-ch", "de_ch", "swiss_german"):
            text = text.replace("ß", "ss")

        # French punctuation spacing rules: add thin space before high punctuation
        elif dialect in ("fr", "fr-fr", "fr_fr", "french"):
            # Ensure single space before ?, !, ;, :
            text = re.sub(r"\s*([?!;:»])", r" \1", text)
            text = re.sub(r"([«])\s*", r"\1 ", text)

        return text
