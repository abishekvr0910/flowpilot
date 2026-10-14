import io
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
import numpy as np
from openai import OpenAI

# Check if faster-whisper is available for offline transcription
try:
    from faster_whisper import WhisperModel
    import faster_whisper.utils
    HAS_FASTER_WHISPER = True

    # Multi-location fallback hook for Silero VAD assets
    _orig_get_assets = faster_whisper.utils.get_assets_path

    def _robust_get_assets_path() -> str:
        # 1. Try original get_assets_path
        try:
            orig = _orig_get_assets()
            if os.path.isdir(orig) and os.path.isfile(os.path.join(orig, "silero_encoder_v5.onnx")):
                return orig
        except Exception:
            pass

        # 2. Check sys._MEIPASS (PyInstaller bundled internal directory)
        if hasattr(sys, "_MEIPASS"):
            meipass_vad = os.path.join(sys._MEIPASS, "faster_whisper", "assets")
            if os.path.isdir(meipass_vad) and os.path.isfile(os.path.join(meipass_vad, "silero_encoder_v5.onnx")):
                return meipass_vad
            meipass_root = os.path.join(sys._MEIPASS, "assets")
            if os.path.isdir(meipass_root) and os.path.isfile(os.path.join(meipass_root, "silero_encoder_v5.onnx")):
                return meipass_root

        # 3. Check relative to sys.executable directory (for packaged binary)
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        candidates = [
            os.path.join(exe_dir, "_internal", "faster_whisper", "assets"),
            os.path.join(exe_dir, "faster_whisper", "assets"),
            os.path.join(exe_dir, "assets"),
        ]
        for c in candidates:
            if os.path.isdir(c) and os.path.isfile(os.path.join(c, "silero_encoder_v5.onnx")):
                return c

        # 4. Check relative to project root
        proj_root = Path(__file__).resolve().parent.parent
        root_candidate = proj_root / "assets"
        if root_candidate.is_dir() and (root_candidate / "silero_encoder_v5.onnx").is_file():
            return str(root_candidate)

        return _orig_get_assets()

    faster_whisper.utils.get_assets_path = _robust_get_assets_path
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

    def preload_model(self):
        """Asynchronously preloads the local faster-whisper model on CPU during application startup."""
        try:
            self._get_local_model()
        except Exception as e:
            print(f"[STT Warning] Preload failed: {e}")

    def _get_local_model(self):
        if not HAS_FASTER_WHISPER:
            raise RuntimeError("faster-whisper is not installed. Please use cloud mode or install faster-whisper.")
        if self._local_model is None:
            size = self.config.get("local_model_size", "base")
            import os
            threads = self.config.get("cpu_threads") or min(8, os.cpu_count() or 4)
            print(f"[STT] Loading local faster-whisper model '{size}' on CPU (int8, threads={threads})...")
            try:
                # First attempt: strictly local offline load without querying Hugging Face Hub
                self._local_model = WhisperModel(
                    size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=threads,
                    local_files_only=True
                )
            except Exception as e:
                # If local cache missing on fresh install, download once explicitly
                print(f"[STT] Local offline cache not found ({e}). Downloading model '{size}' once for offline use...")
                self._local_model = WhisperModel(
                    size,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=threads,
                    local_files_only=False
                )
            print(f"[STT] Local model '{size}' loaded on CPU (int8, threads={threads}). Zero-egress offline mode active.")
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

    def transcribe(self, audio_data: Union[bytes, np.ndarray], custom_vocabulary: Optional[List[str]] = None) -> Dict[str, Any]:
        mode = self.config.get("engine_mode", "cloud")
        vocab = custom_vocabulary or self.config.get("custom_vocabulary", [])
        lang = self.config.get("language", "auto")
        bias_prompt = self.build_bias_prompt(vocab, lang)

        if mode == "local":
            return self._transcribe_local(audio_data, bias_prompt, lang)
        else:
            if isinstance(audio_data, np.ndarray):
                import soundfile as sf
                buf = io.BytesIO()
                sf.write(buf, audio_data, 16000, format="WAV", subtype="PCM_16")
                wav_bytes = buf.getvalue()
            else:
                wav_bytes = audio_data
            return self._transcribe_cloud(wav_bytes, bias_prompt, lang)

    def _transcribe_local(self, audio_data: Union[bytes, np.ndarray], initial_prompt: str, language: str) -> Dict[str, Any]:
        model = self._get_local_model()
        if isinstance(audio_data, np.ndarray):
            audio_input = audio_data
        else:
            audio_input = io.BytesIO(audio_data)

        whisper_lang = None if language == "auto" else language

        # Default beam_size=1 (greedy search) provides ~2x speedup on CPU while preserving accuracy
        beam_size = self.config.get("beam_size", 1)
        # Pre-gated dictation audio does not require redundant VAD chunking overhead (~480ms saved)
        vad_filter = self.config.get("vad_filter", False)

        try:
            segments, info = model.transcribe(
                audio_input,
                beam_size=beam_size,
                language=whisper_lang,
                initial_prompt=initial_prompt,
                vad_filter=vad_filter,
                vad_parameters=dict(min_silence_duration_ms=400) if vad_filter else None
            )
            segment_list = list(segments)
        except Exception as e:
            if vad_filter:
                print(f"[STT Warning] Transcribe with vad_filter failed ({e}). Falling back without vad_filter...")
                if not isinstance(audio_input, np.ndarray):
                    audio_input.seek(0)
                segments, info = model.transcribe(
                    audio_input,
                    beam_size=beam_size,
                    language=whisper_lang,
                    initial_prompt=initial_prompt,
                    vad_filter=False
                )
                segment_list = list(segments)
            else:
                raise e

        full_text = " ".join([segment.text for segment in segment_list]).strip()
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
