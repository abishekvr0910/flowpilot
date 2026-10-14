# FlowPilot Scientific Benchmark Protocol & Evaluation Methodology

**Product:** FlowPilot Desktop  
**Target:** Standardized Measurement of Speech Recognition, Polishing, and Windows Integration  
**Version:** 2.0  
**Date:** October 14, 2026  

---

## 1. Overview and Objectives

This protocol specifies the exact testing conditions, datasets, metric definitions, and execution harnesses used to benchmark FlowPilot against commercial competitors (including Wispr Flow, Nuance Dragon, and standard Whisper desktop implementations).

The primary objectives are:
1. Ensure 100% reproducible, evidence-driven benchmarking.
2. Eliminate mock substitutions or fabricated performance claims.
3. Quantify accuracy (WER, CER), latency (RTF, end-to-end injection time), and factual preservation (FactGuard score).

---

## 2. Test Environments and Hardware Specifications

### 2.1 Standard Host Reference Platform
- **Operating System:** Windows 11 Enterprise / Pro (x64), Version 22H2 or later.
- **CPU:** Intel Core i7 / AMD Ryzen 7 (multi-threaded, AVX2 support).
- **RAM:** Minimum 16 GB DDR4/DDR5.
- **Audio Capture Device:** PortAudio direct access to Windows CoreAudio / Intel Smart Sound Technology Digital Microphone Array.
- **Sample Rate Support:** 16,000 Hz native, with automatic fallback resampling from 44,100 Hz or 48,000 Hz.

### 2.2 Acoustic Test Conditions
1. **Studio Clean (Baseline):** 0 dB SNR background noise, direct microphone capture or lossless PCM synthesis (SAPI/TTS) at 16kHz mono.
2. **Office Ambient:** 15 dB SNR background noise (keyboard typing, ventilation, muffled distant speech).
3. **Hardware Real-World:** Live acoustic capture via physical microphone array with PortAudio ring buffering.

---

## 3. Evaluation Datasets & Licensing Compliance

All datasets selected for benchmarking comply with commercial-safe and open-research licensing:

| Dataset | Split / Domain | License | Primary Use Case |
|:---|:---|:---:|:---|
| **Mozilla Common Voice (v13+)** | Test split (multi-accent English, German, French, Spanish) | CC0 (Public Domain) | Baseline conversational WER & phonetic diversity |
| **Google FLEURS** | 102 languages test split | CC-BY 4.0 | Multilingual script accuracy & LID benchmarking |
| **LibriSpeech (test-clean)** | 100-hour clean test set | CC-BY 4.0 | Read speech phonetic benchmark |
| **FlowPilot Technical Corpus** | Custom curated 50-prompt engineering suite | Internal Open | Identifiers (`camelCase`, `snake_case`), URLs, CLI commands, self-corrections |

---

## 4. Formal Metric Definitions

### 4.1 Word Error Rate (WER)
Word Error Rate is computed via Levenshtein edit distance at the word token level:
$$\text{WER} = \frac{S + D + I}{N} = \frac{\text{Substitutions} + \text{Deletions} + \text{Insertions}}{\text{Total Reference Words}}$$
- Punctuation and casing are normalized according to the target evaluation mode (Verbatim vs. Polished).

### 4.2 Character Error Rate (CER)
For non-segmented scripts (Chinese, Japanese) or morphologically dense scripts (Arabic, Hindi), CER is the primary metric:
$$\text{CER} = \frac{S_c + D_c + I_c}{N_c}$$
- Evaluates script glyph fidelity and terminal punctuation without relying on whitespace word boundaries.

### 4.3 Real-Time Factor (RTF)
Measures computational efficiency:
$$\text{RTF} = \frac{T_{\text{processing}}}{T_{\text{audio}}}$$
- An RTF of 0.10 means that 10 seconds of speech is transcribed in 1.0 second.
- FlowPilot targets RTF < 0.25 on standard multi-core CPUs.

### 4.4 FactGuard Semantic Preservation Rate ($F_{\text{guard}}$)
Measures the fidelity of critical factual tokens before and after writing intelligence polishing:
$$F_{\text{guard}} = \frac{|\mathcal{T}_{\text{fact}}(\text{Raw}) \cap \mathcal{T}_{\text{fact}}(\text{Polished})|}{|\mathcal{T}_{\text{fact}}(\text{Raw})|} \times 100\%$$
Where $\mathcal{T}_{\text{fact}}$ includes:
1. **Numbers & Quantities:** Integers, floats, percentages, currencies ($12,000, 25%).
2. **Temporal Tokens:** Dates, days of week, months, times (Tuesday, 3:00 PM).
3. **Negations:** Critical negation adverbs (`not`, `never`, `none`, `without`, `cannot`).
4. **Commitments:** Modal verbs (`must`, `shall`, `agreed`).
- Target: **100.0%**. Any modification of these tokens triggers an immediate fallback to verbatim speech.

### 4.5 Injection & Focus Retention Rate
$$\text{Success Rate} = \frac{\text{Successful Injections without Focus Theft}}{\text{Total Injection Attempts}} \times 100\%$$
- Verified by checking the target window handle (`HWND`) before hotkey trigger, during recording, during HUD rendering, and after text injection.

---

## 5. Automated Benchmark Harness Execution

The benchmark suite is automated through Python harnesses in `tests/`:

1. **Full Benchmark Corpus:**
   ```bash
   python tests/benchmark_corpus.py
   ```
   Evaluates WER, CER, RTF, and FactGuard across model sizes (`tiny`, `base`, `small`).

2. **Multilingual Script Validation:**
   ```bash
   python tests/test_multilingual_validation.py
   ```
   Evaluates 10 distinct locales, script directions (LTR/RTL), and non-Latin terminal punctuation.

3. **Multi-Cycle End-to-End Application Test:**
   ```bash
   python tests/test_notepad_dictation_e2e.py
   ```
   Validates live text insertion into Notepad over 5 continuous dictation cycles with clipboard integrity verification.

---

## 6. Scientific Reproducibility Guarantees
- No simulated or randomized pass criteria.
- Real PortAudio and CoreAudio COM interfaces invoked directly.
- Real Win32 API calls (`RegisterHotKey`, `AttachThreadInput`, `SendInput`, `OpenClipboard`, `CloseClipboard`).
- Raw logs and metrics captured with timestamps in standard JSON/markdown artifacts.
