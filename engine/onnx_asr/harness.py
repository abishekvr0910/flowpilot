"""
ONNX Runtime Multilingual Specialist ASR Harness.
Specification: docs/specs/0006-onnx-multilingual-specialist-asr-harness.md

Provides high-accuracy offline CPU speech recognition for specialist languages:
- Tamil ('ta'): AI4Bharat IndicConformer Medium (~120M parameters, INT8 Quantized, 137 MB)
- Cross-platform, 100% offline, zero cloud egress.
"""
import io
import os
import re
import sys
import time
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, Tuple, List
import numpy as np

logger = logging.getLogger("FlowPilot.OnnxASR")

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Phonetic loanword mappings for common developer terms in Tamil dictation
KNOWN_TAMIL_TECH_MAP: Dict[str, str] = {
    'டாக்கர்': 'Docker',
    'டாகர்': 'Docker',
    'குபர்னெடிஸ்': 'Kubernetes',
    'குபர்நெட்டிஸ்': 'Kubernetes',
    'குபெர்னெட்டீஸ்': 'Kubernetes',
    'பைதான்': 'Python',
    'பைத்தான்': 'Python',
    'கிராஃப்கியூஎல்': 'GraphQL',
    'கிராப்கியூஎல்': 'GraphQL',
    'பாஸ்டேபிஐ': 'FastAPI',
    'போஸ்ட்கிரெஸ்': 'PostgreSQL',
    'போஸ்ட்கிரெஸ்கியூஎல்': 'PostgreSQL',
    'நெக்ஸ்ட்ஜேஎஸ்': 'Next.js',
    'டைப்ஸ்கிரிப்ட்': 'TypeScript',
    'விஸ்பர்': 'Whisper',
    'சர்வர்': 'Server',
}


def repair_tamil_unicode(text: str) -> str:
    """
    Normalizes and repairs Tamil Unicode sequences resulting from subword token joining.
    Fixes stacked combining vowel signs, viramas followed by vowel signs, and orphaned marks.
    """
    if not text:
        return text
    # 1. Virama followed by dependent vowel sign (e.g. க்ொ -> கொ, த்ா -> தா)
    text = re.sub(r'\u0BCD([\u0BBE-\u0BCC])', r'\1', text)
    # 2. Vowel sign followed by virama (e.g. கா் -> கா)
    text = re.sub(r'([\u0BBE-\u0BCC])\u0BCD', r'\1', text)
    # 3. Multiple consecutive combining vowel signs (e.g. ிி -> ி)
    text = re.sub(r'([\u0BBE-\u0BCC])[\u0BBE-\u0BCC]+', r'\1', text)
    # 4. Multiple viramas
    text = re.sub(r'\u0BCD+', '\u0BCD', text)
    # 5. Combining sign at start of word (following space or start of string)
    vowel_map = {
        '\u0BBE': 'ஆ', '\u0BBF': 'இ', '\u0BC0': 'ஈ',
        '\u0BC1': 'உ', '\u0BC2': 'ஊ', '\u0BC6': 'எ',
        '\u0BC7': 'ஏ', '\u0BC8': 'ஐ', '\u0BCA': 'ஒ',
        '\u0BCB': 'ஓ', '\u0BCC': 'ஔ'
    }
    text = re.sub(r'(?:(?<=[\s\b])|^)([\u0BBE-\u0BCD])', lambda m: vowel_map.get(m.group(1), ''), text)
    return text


def _phonetic_normalize(s: str) -> str:
    """Normalizes phonological variants between spoken Tamil transliteration and English."""
    s = s.lower()
    s = re.sub(r'c(?=[eiy])', 's', s)
    s = s.replace('c', 'k').replace('b', 'p').replace('d', 'th').replace('dh', 'th')
    s = s.replace('ee', 'i').replace('oo', 'u').replace('aa', 'a')
    s = s.replace('z', 's').replace('sh', 's').replace('v', 'w').replace('w', 'v')
    return s


def _levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insert = prev[j + 1] + 1
            delete = curr[j] + 1
            sub = prev[j] + (0 if c1 == c2 else 1)
            curr.append(min(insert, delete, sub))
        prev = curr
    return prev[-1]


def apply_custom_vocabulary_biasing(text: str, custom_vocabulary: Optional[List[str]]) -> str:
    """
    Applies custom vocabulary restoration and case normalization to ASR transcript.
    Restores technical terms, brand names, and user-defined entities in Tamil/Tanglish dictation.
    """
    if not text or not custom_vocabulary:
        return text

    from engine.transliteration import transliterate_tamil_to_tanglish, is_tamil_script

    vocab_lower_map = {v.lower(): v for v in custom_vocabulary}

    # 1. Map known common Tamil loanword phonetic spellings with case suffixes
    for tam, eng in KNOWN_TAMIL_TECH_MAP.items():
        if eng.lower() in vocab_lower_map:
            canonical = vocab_lower_map[eng.lower()]
            stem = tam[:-1] if tam.endswith('்') else tam
            p_ukku = re.escape(stem + 'ுக்கு')
            p_il = re.escape(stem + 'ில்')
            p_la = re.escape(stem + 'ல')
            p_oda = re.escape(stem + 'ோட')
            p_base = re.escape(tam)
            text = re.sub(r'(?<!\w)' + p_ukku + r'(?!\w)', f'{canonical}-ukku', text)
            text = re.sub(r'(?<!\w)' + p_il + r'(?!\w)', f'{canonical}-il', text)
            text = re.sub(r'(?<!\w)' + p_la + r'(?!\w)', f'{canonical}-la', text)
            text = re.sub(r'(?<!\w)' + p_oda + r'(?!\w)', f'{canonical}-oda', text)
            text = re.sub(r'(?<!\w)' + p_base + r'(?!\w)', canonical, text)

    # 2. Dynamic arbitrary user vocabulary biasing
    tokens = re.split(r'(\s+|[.,!?;:"\'()\[\]{}]+)', text)
    out_tokens = []
    user_vocab_norms = [(v, _phonetic_normalize(v)) for v in custom_vocabulary]

    for tok in tokens:
        if not tok or not any(c.isalnum() for c in tok):
            out_tokens.append(tok)
            continue

        # Case A: Exact case-insensitive ASCII match
        if tok.lower() in vocab_lower_map:
            out_tokens.append(vocab_lower_map[tok.lower()])
            continue

        # Case B: Tamil Unicode token matching user custom vocabulary
        if is_tamil_script(tok):
            matched_term = None
            matched_suffix = ""

            suffixes = [
                ('-வுக்கு', '-ukku'), ('-ுக்கு', '-ukku'), ('-க்கு', '-ukku'),
                ('-இல்', '-il'), ('-ல்', '-il'), ('-ல', '-la'), ('-ோட', '-oda'),
                ('வுக்கு', '-ukku'), ('ுக்கு', '-ukku'), ('க்கு', '-ukku'),
                ('இல்', '-il'), ('ல்', '-il'), ('ல', '-la'), ('ோட', '-oda'),
            ]

            for tam_sfx, eng_sfx in suffixes:
                if tok.endswith(tam_sfx) and len(tok) > len(tam_sfx):
                    base_candidate = tok[:-len(tam_sfx)].rstrip('-')
                    if not base_candidate:
                        continue
                    tang = transliterate_tamil_to_tanglish(base_candidate)
                    norm_tang = _phonetic_normalize(tang)
                    for orig_v, norm_v in user_vocab_norms:
                        if tang.lower() == orig_v.lower() or norm_tang == norm_v or (len(norm_v) >= 4 and _levenshtein(norm_tang, norm_v) <= 1):
                            matched_term = orig_v
                            matched_suffix = eng_sfx
                            break
                    if matched_term:
                        break

            if not matched_term:
                tang = transliterate_tamil_to_tanglish(tok)
                norm_tang = _phonetic_normalize(tang)
                for orig_v, norm_v in user_vocab_norms:
                    if tang.lower() == orig_v.lower() or norm_tang == norm_v or (len(norm_v) >= 4 and _levenshtein(norm_tang, norm_v) <= 1):
                        matched_term = orig_v
                        matched_suffix = ""
                        break

            if matched_term:
                out_tokens.append(f"{matched_term}{matched_suffix}")
                continue

        out_tokens.append(tok)

    text = "".join(out_tokens)

    # 3. Final regex casing pass for all custom vocab terms
    for v in custom_vocabulary:
        pattern = r'(?i)\b' + re.escape(v) + r'\b'
        text = re.sub(pattern, v, text)

    return text


class OnnxASRHarness:
    """
    Offline Specialist ASR Harness using ONNX Runtime.
    Executes quantized NeMo/Conformer CTC models on CPU with pure NumPy/SciPy audio preprocessing.
    """
    _instance: Optional["OnnxASRHarness"] = None
    _init_lock = threading.Lock()

    def __init__(self, models_dir: Optional[Path] = None):
        self.models_dir = models_dir or (PROJECT_ROOT / "models")
        self._sessions: Dict[str, Any] = {}
        self._vocabs: Dict[str, Dict[int, str]] = {}
        self._mel_filterbanks: Dict[Tuple[int, int, int], np.ndarray] = {}
        self._lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "OnnxASRHarness":
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _resolve_model_files(self, language: str) -> Tuple[Optional[Path], Optional[Path]]:
        """Resolves the ONNX model and vocab.txt paths for a target language."""
        candidates = [
            self.models_dir / f"indicconformer-{language}",
            PROJECT_ROOT / "assets" / "models" / "onnx" / language,
            Path.home() / ".cache" / "flowpilot" / "onnx" / language,
        ]
        for dir_path in candidates:
            if not dir_path.is_dir():
                continue
            model_file = dir_path / "model.int8.onnx"
            if not model_file.is_file():
                model_file = dir_path / "model.onnx"
            vocab_file = dir_path / "vocab.txt"
            if model_file.is_file() and vocab_file.is_file():
                return model_file, vocab_file
        return None, None

    def is_available(self, language: str) -> bool:
        """Returns True if the specialist model files exist locally for the language."""
        if not HAS_ONNX or not HAS_SOUNDFILE:
            return False
        model_file, vocab_file = self._resolve_model_files(language)
        return model_file is not None and vocab_file is not None

    def _load_vocab(self, vocab_path: Path) -> Dict[int, str]:
        vocab: Dict[int, str] = {}
        with vocab_path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip("\r\n").rsplit(" ", 1)
                if len(parts) == 2:
                    try:
                        vocab[int(parts[1])] = parts[0]
                    except ValueError:
                        pass
        return vocab

    def _get_or_create_mel_filterbank(self, sr: int = 16000, n_fft: int = 512, n_mels: int = 80) -> np.ndarray:
        key = (sr, n_fft, n_mels)
        if key in self._mel_filterbanks:
            return self._mel_filterbanks[key]

        def hz_to_mel(f: float) -> float:
            return 2595.0 * np.log10(1.0 + f / 700.0)

        def mel_to_hz(m: float) -> float:
            return 700.0 * (10.0 ** (m / 2595.0) - 1.0)

        mel_min, mel_max = hz_to_mel(0.0), hz_to_mel(sr / 2.0)
        mel_points = np.linspace(mel_min, mel_max, n_mels + 2)
        hz_points = mel_to_hz(mel_points)
        bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

        filters = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float32)
        for i in range(1, n_mels + 1):
            left, center, right = bin_points[i - 1], bin_points[i], bin_points[i + 1]
            if center > left:
                filters[i - 1, left:center] = (np.arange(left, center) - left) / (center - left)
            if right > center:
                filters[i - 1, center:right] = (right - np.arange(center, right)) / (right - center)

        self._mel_filterbanks[key] = filters
        return filters

    def extract_features(
        self,
        audio: np.ndarray,
        sr: int = 16000,
        n_mels: int = 80,
        n_fft: int = 512,
        hop_len: int = 160,
        win_len: int = 400
    ) -> np.ndarray:
        """
        Computes NeMo-compliant 80-channel log-mel filterbanks with per-feature CMVN.
        Output shape: (80, num_frames) float32.
        """
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        window = np.hanning(win_len).astype(np.float32)
        pad_len = n_fft - hop_len
        padded = np.pad(audio, (pad_len // 2, pad_len // 2), mode="reflect")
        num_frames = 1 + (len(padded) - win_len) // hop_len

        frames = np.lib.stride_tricks.as_strided(
            padded,
            shape=(num_frames, win_len),
            strides=(padded.strides[0] * hop_len, padded.strides[0])
        )
        windowed = frames * window
        spectrogram = np.abs(np.fft.rfft(windowed, n=n_fft)) ** 2

        fb = self._get_or_create_mel_filterbank(sr, n_fft, n_mels)
        mel_spec = np.dot(spectrogram, fb.T)
        log_mel = np.log(np.maximum(mel_spec, 1e-5)).T  # (n_mels, num_frames)

        # Per-feature normalization
        mean = np.mean(log_mel, axis=1, keepdims=True)
        std = np.std(log_mel, axis=1, keepdims=True)
        norm = (log_mel - mean) / (std + 1e-5)
        return norm.astype(np.float32)

    def _get_session(self, language: str) -> Tuple[Any, Dict[int, str]]:
        with self._lock:
            if language in self._sessions:
                return self._sessions[language], self._vocabs[language]

            model_file, vocab_file = self._resolve_model_files(language)
            if not model_file or not vocab_file:
                raise FileNotFoundError(f"Specialist model for language '{language}' not found locally.")

            opts = ort.SessionOptions()
            opts.intra_op_num_threads = min(8, os.cpu_count() or 4)
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            logger.info("Loading ONNX Specialist ASR for '%s' from %s", language, model_file)
            session = ort.InferenceSession(str(model_file), sess_options=opts, providers=["CPUExecutionProvider"])
            vocab = self._load_vocab(vocab_file)

            self._sessions[language] = session
            self._vocabs[language] = vocab
            return session, vocab

    def transcribe(
        self,
        audio_data: Union[bytes, np.ndarray],
        language: str = "ta",
        custom_vocabulary: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end transcription of audio using the local ONNX specialist model.
        Returns standard FlowPilot recognition dict.
        """
        t0 = time.perf_counter()
        if not self.is_available(language):
            raise RuntimeError(f"Specialist ASR is not available locally for language '{language}'")

        # Convert audio_data to numpy float32 16kHz
        if isinstance(audio_data, bytes):
            audio_arr, sr = sf.read(io.BytesIO(audio_data), dtype="float32")
        elif isinstance(audio_data, np.ndarray):
            audio_arr = audio_data.astype(np.float32)
            sr = 16000
        else:
            raise TypeError("Unsupported audio_data type")

        if audio_arr.ndim > 1:
            audio_arr = np.mean(audio_arr, axis=1)

        # Resample if not 16 kHz
        if sr != 16000 and len(audio_arr) > 0:
            import math
            gcd = math.gcd(int(sr), 16000)
            from scipy.signal import resample_poly
            audio_arr = resample_poly(audio_arr, 16000 // gcd, int(sr) // gcd).astype(np.float32)
            sr = 16000

        duration_sec = len(audio_arr) / float(sr) if sr > 0 else 0.0
        features = self.extract_features(audio_arr, sr=16000)

        session, vocab = self._get_session(language)

        # Prepare ONNX inputs
        feat_batch = np.expand_dims(features, axis=0)  # (1, 80, time_frames)
        lens_batch = np.array([features.shape[1]], dtype=np.int64)

        inputs = {
            "audio_signal": feat_batch,
            "length": lens_batch
        }

        # Run ONNX inference
        outputs = session.run(None, inputs)
        logprobs = outputs[0][0]  # (time_steps, vocab_size)

        # CTC Greedy Decoding
        pred_ids = np.argmax(logprobs, axis=-1)
        blank_id = len(vocab) - 1  # 256 is blank token (<blk>)

        tokens: List[str] = []
        prev_id = -1
        for idx in pred_ids:
            if idx != prev_id:
                if idx != blank_id:
                    token = vocab.get(idx, "")
                    if token:
                        tokens.append(token)
                prev_id = idx

        raw_text = "".join(tokens).replace("\u2581", " ").replace("▁", " ").strip()

        # Normalization: repair broken Unicode sequences
        if language == "ta":
            raw_text = repair_tamil_unicode(raw_text)

        # Apply custom vocabulary biasing & case normalization if provided
        if custom_vocabulary:
            raw_text = apply_custom_vocabulary_biasing(raw_text, custom_vocabulary)

        elapsed = time.perf_counter() - t0

        return {
            "text": raw_text,
            "detected_language": language,
            "engine": "indic_conformer_onnx",
            "duration": round(duration_sec, 3),
            "inference_time_sec": round(elapsed, 4),
            "task": "transcribe"
        }


def get_specialist_harness() -> OnnxASRHarness:
    return OnnxASRHarness.get_instance()
