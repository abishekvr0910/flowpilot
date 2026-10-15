# FLOWPILOT MULTILINGUAL SPEECH DATASET & LICENSING AUDIT

**Date:** October 14, 2026  
**Auditor:** FlowPilot Compliance & Engineering  
**Scope:** Legal and commercial analysis of public speech corpora for multilingual acoustic evaluation, fine-tuning, and model adaptation.

---

## 1. Executive Summary & Compliance Mandate

To maintain FlowPilot's clean commercial standing and ensure defensible enterprise deployment, all training corpora and evaluation benchmarks must strictly comply with open-source licensing. This document provides a forensic audit of the primary multilingual speech datasets, evaluating their license terms, commercial viability, attribution requirements, and privacy considerations.

---

## 2. Dataset Legal & Commercial Inventory

| Dataset Name | Curating Entity / Origin | Language Coverage | Primary License | Commercial Use Allowed? | Derivative Works Allowed? | Mandatory Attribution Requirements | Risk Level & Notes |
|---|---|---|---|---|---|---|---|
| **Mozilla Common Voice** | Mozilla Foundation | 110+ Languages | **CC0 (Public Domain Dedication)** | **YES** | **YES** | None legally required (CC0). Best practice: cite Mozilla Common Voice. | **ZERO RISK** — CC0 is the gold standard for commercial and enterprise speech models. |
| **Google FLEURS** (Few-shot Learning Evaluation of Universal Robust Speech) | Google Research | 102 Languages | **CC-BY 4.0** | **YES** | **YES** | Must include credit: *"Source: Google FLEURS dataset under CC-BY 4.0"*. | **LOW RISK** — Freely usable commercially with attribution in documentation or license notices. |
| **LibriSpeech ASR** | OpenSLR (Vassil Panayotov et al.) | English (1,000 hrs) | **CC-BY 4.0** | **YES** | **YES** | Attribution required: cite OpenSLR LibriSpeech. | **LOW RISK** — Industry-standard benchmark for English acoustic modeling. |
| **Multilingual LibriSpeech (MLS)** | Facebook AI Research (FAIR) | 8 European Languages (~50,000 hrs) | **CC-BY 4.0** | **YES** | **YES** | Attribution required: cite FAIR Multilingual LibriSpeech. | **LOW RISK** — Large-scale corpus derived from LibriVox audiobooks. Fully commercial compatible. |
| **VoxForge** | VoxForge Community | 20+ Languages | **GPL (GNU Public License)** | **RESTRICTED** | **RESTRICTED** | Requires reciprocal copyleft licensing of downstream acoustic models. | **HIGH RISK (AVOID FOR CLOSED RELEASES)** — Copyleft terms can contaminate commercial proprietary engines. |
| **OpenAI Whisper Audio Training Distribution** | OpenAI | 99 Languages (~680,000 hrs) | Weights: **MIT License** | **YES** | **YES** | Pretrained weights distributed under MIT license. Retain MIT notice. | **ZERO RISK** — Runtime inference with `faster-whisper` (CTranslate2) is 100% MIT/Apache-2.0 compliant. |
| **CoVoST 2** | Facebook AI Research | 22 Languages (Speech Translation) | **CC0 / CC-BY 4.0** | **YES** | **YES** | Standard attribution. | **LOW RISK** — High-quality alignment for multilingual translation and transcription. |

---

## 3. Compliance Guidelines for Enterprise & Commercial Packaging

1. **Weight Redistribution Compliance:**  
   The pretrained weights used by FlowPilot (`faster-whisper-tiny`, `faster-whisper-base`, `faster-whisper-small`) originate from OpenAI's Whisper release, which is licensed under the permissive **MIT License**. CTranslate2 is licensed under the **MIT License**. Both licenses allow unlimited commercial use, modification, and bundling in closed or open source commercial software without licensing fees or copyleft contagion.
2. **Attribution Notices:**  
   FlowPilot includes standard MIT license attributions for OpenAI, Systran CTranslate2, PySide6 (LGPLv3 dynamic linking), and `sounddevice` (MIT) in `THIRD_PARTY_LICENSES.txt`.
3. **No Voice Scraping / User Telemetry:**  
   FlowPilot neither collects nor uploads user audio data for model training. Unlike Wispr Flow (which trains models on user audio by default on free tiers), FlowPilot's architecture guarantees that user speech never forms part of any external dataset.
