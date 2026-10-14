import io
import os
from typing import List, Optional, Dict, Any
from openai import OpenAI

# Check if faster-whisper is available for offline transcription
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False

try:
    from engine.language_registry import LanguageRegistry
    from engine.personalization import PersonalizationEngine
    HAS_REGISTRY = True
except ImportError:
    HAS_REGISTRY = False

class STTEngine:
    def __init__(self, config: Dict[str, Any], personalization: Optional[Any] = None):
        self.config = config
        self.personalization = personalization or (PersonalizationEngine() if HAS_REGISTRY else None)
        self._local_model: Optional[Any] = None

    def _get_local_model(self):
        if not HAS_FASTER_WHISPER:
            raise RuntimeError("faster-whisper is not installed. Please use cloud mode or install faster-whisper.")
        if self._local_model is None:
            size = self.config.get("local_model_size", "base")
            print(f"[STT] Loading local faster-whisper model '{size}' on CPU (int8)...")
            self._local_model = WhisperModel(size, device="cpu", compute_type="int8")
            print("[STT] Local model loaded on CPU (int8).")
        return self._local_model

    def build_bias_prompt(self, custom_vocabulary: List[str], language: str) -> str:
        """
        Builds a phonetic bias prompt for Whisper using LanguageRegistry
        and personal custom dictionary to bias technical terms and multilingual flow.
        """
        vocab = list(custom_vocabulary)
        if self.personalization:
            # Merge personal dictionary terms
            dict_terms = self.personalization.get_terms_list()
            for t in dict_terms:
                if t not in vocab:
                    vocab.append(t)

        if HAS_REGISTRY:
            return LanguageRegistry.get_bias_prompt(language, vocab)

        prompt_parts = []
        if vocab:
            vocab_str = ", ".join(vocab)
            prompt_parts.append(f"Technical glossary: {vocab_str}.")

        if self.config.get("enable_code_switching", True):
            prompt_parts.append("Natural conversational flow with accurate multilingual code-switching and correct capitalization.")

        return " ".join(prompt_parts)

    def transcribe(self, wav_bytes: bytes, custom_vocabulary: Optional[List[str]] = None) -> Dict[str, Any]:
        mode = self.config.get("engine_mode", "cloud")
        vocab = custom_vocabulary or self.config.get("custom_vocabulary", [])
        lang = self.config.get("language", "auto")
        bias_prompt = self.build_bias_prompt(vocab, lang)

        if mode == "local":
            return self._transcribe_local(wav_bytes, bias_prompt, lang)
        else:
            return self._transcribe_cloud(wav_bytes, bias_prompt, lang)

    def _transcribe_local(self, wav_bytes: bytes, initial_prompt: str, language: str) -> Dict[str, Any]:
        model = self._get_local_model()
        audio_stream = io.BytesIO(wav_bytes)

        whisper_lang = None if language == "auto" else language

        segments, info = model.transcribe(
            audio_stream,
            beam_size=5,
            language=whisper_lang,
            initial_prompt=initial_prompt,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )

        full_text = " ".join([segment.text for segment in segments]).strip()
        detected_language = info.language if hasattr(info, "language") else "unknown"

        return {
            "text": full_text,
            "detected_language": detected_language,
            "engine": "local_faster_whisper",
            "duration": getattr(info, "duration", 0)
        }

    def _transcribe_cloud(self, wav_bytes: bytes, initial_prompt: str, language: str) -> Dict[str, Any]:
        provider = self.config.get("cloud_provider", "groq")
        
        if provider == "groq":
            api_key = self.config.get("groq_api_key") or os.environ.get("GROQ_API_KEY")
            base_url = "https://api.groq.com/openai/v1"
            model_name = "whisper-large-v3"
        else:
            api_key = self.config.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
            base_url = "https://api.openai.com/v1"
            model_name = "whisper-1"

        if not api_key:
            # If no API key provided, fallback to local if available
            if HAS_FASTER_WHISPER:
                print("[STT] No Cloud API Key provided. Falling back to local offline model...")
                return self._transcribe_local(wav_bytes, initial_prompt, language)
            raise ValueError(f"Please enter an API Key for {provider.capitalize()} in Settings or configure local model.")

        client = OpenAI(api_key=api_key, base_url=base_url)

        audio_file = ("audio.wav", wav_bytes, "audio/wav")

        kwargs = {
            "model": model_name,
            "file": audio_file,
            "response_format": "verbose_json"
        }
        if initial_prompt:
            kwargs["prompt"] = initial_prompt
        if language and language != "auto":
            kwargs["language"] = language

        response = client.audio.transcriptions.create(**kwargs)
        raw_text = getattr(response, "text", "")
        detected_language = getattr(response, "language", language)

        return {
            "text": raw_text.strip(),
            "detected_language": detected_language,
            "engine": f"cloud_{provider}_{model_name}",
            "duration": getattr(response, "duration", 0)
        }
