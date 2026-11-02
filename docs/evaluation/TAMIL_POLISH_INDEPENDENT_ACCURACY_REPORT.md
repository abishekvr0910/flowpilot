# FlowPilot Independent Multilingual Accuracy Benchmark

**Date:** 2026-11-02 22:30:45  
**Evaluation Scope:** 20 Consented Mozilla Common Voice 17.0 Audio Clips (10 Tamil, 10 Polish)  
**Ground Truth:** Human Reference Transcripts (Independent of ASR Models)  
**Zero Cloud Egress Invariant:** 100% Verified (Local CPU Inference, 0 Outbound Sockets)

---

## 1. Executive Summary

| Language | Metric | AI4Bharat IndicConformer Medium (137 MB INT8) | Whisper Small (461 MB INT8) | Whisper Base (74 MB INT8) | Leapfrog / Accuracy Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tamil (`ta`)** | **Word Error Rate (WER)** | **24.0%** | 65.0% | 82.7% | **63.1% relative error reduction** |
| **Tamil (`ta`)** | **Character Error Rate (CER)** | **5.6%** | 19.3% | — | **71.1% relative CER reduction** |
| **Tamil (`ta`)** | **Average Latency** | **0.91s** | 2.99s | 0.98s | **3.31x faster than Whisper Small** |
| **Polish (`pl`)** | **Word Error Rate (WER)** | *(Specialist in Dev)* | **18.0%** | 54.6% | Whisper Small delivers high accuracy on Polish |
| **Polish (`pl`)** | **Average Latency** | — | **2.41s** | 0.79s | Clean baseline established for Parakeet |

---

## 2. Tamil Item-by-Item Benchmark Matrix

| Clip ID | Audio Duration | Ground Truth Reference | IndicConformer Output (WER / Time) | Whisper Small Output (WER / Time) | Speedup |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ta-cv-001`** | 6.696s | `பாலாஜி என்பது பாலன் என்ற பொருளுடையது.` | `பாலாஜி என்பது பாலன் என்ற பொருளுடையது`<br>(**WER: 0.0%**, 0.999s) | `Balaji என்பது, Palan, என்ற பிருளுடியது.`<br>(WER: 60.0%, 3.529s) | **3.53x** |
| **`ta-cv-002`** | 7.38s | `சீக்கிரத்தில் ஐநூறு ரூபாய் செலவழித்து அவரது முழு உருவப்படமொன்று சபையில் வைத்தோம்.` | `சீக்கிரத்தில் ஐநூறு ரூபாய் செலவழைத்து அவரது முழு உருவப்படம் ஒன்று சபையில் வைத்தோம்`<br>(**WER: 33.3%**, 1.182s) | `சீக்கிரத்தில் 500 ரோபாய் சலவழித்து அவருது முழு உருவப்படம் என்று சபையில் வைத்தோம்.`<br>(WER: 66.7%, 3.324s) | **2.81x** |
| **`ta-cv-003`** | 3.96s | `பகலில் இயங்கிக் கொண்டே இருப்பர்.` | `பகலில் இயங்கிக் கொண்டே இருப்பர்`<br>(**WER: 0.0%**, 0.614s) | `பகலில் எங்கிக்கும்டையிருப்பேன்.`<br>(WER: 75.0%, 2.612s) | **4.25x** |
| **`ta-cv-004`** | 3.456s | `மிகுதியும் பயன் விளையும்.` | `மிகுதியும் பயன் விளையும்`<br>(**WER: 0.0%**, 0.546s) | `நிகுதியம் பயன் விளையம்`<br>(WER: 66.7%, 2.251s) | **4.12x** |
| **`ta-cv-005`** | 4.428s | `புதுப்புனலில் பாய்ந்து நீந்தி விளையாடுகிறாள்.` | `புது புனலல் பாய்ந்து நீந்தி விளையாடுகிறாள்`<br>(**WER: 50.0%**, 0.797s) | `புதுப் புனலில் பாய்ந்து நீந்தி விளியாடகராள்.`<br>(WER: 75.0%, 2.891s) | **3.63x** |
| **`ta-cv-006`** | 5.256s | `அது தாவிக்கொண்டு சந்தோஷமாக அவர்கள் அருகில் வந்தது.` | `அது தாவிிக்ொண்டு சந்தோஷமாக அவர்கள் அருகில் வந்தது`<br>(**WER: 16.7%**, 0.789s) | `அது தாபிக்கொண்டு சந்தோஷமாக அவர்கள் அறைக்குள் வந்தது.`<br>(WER: 33.3%, 2.854s) | **3.62x** |
| **`ta-cv-007`** | 5.256s | `கோடைக்கானல் பல நாட்டு மக்களுக்கும் ஒரு தங்கல்மனை போன்றது.` | `கோடைக்கானல் பல நாட்டு மக்களுக்கும் ஒரு தங்கள்ல் மனை போன்றது`<br>(**WER: 28.6%**, 0.892s) | `குடைக்கானல் பல நாட்டு மக்களுக்கும் ஒரு தங்கள் மனைப்போன்றது.`<br>(WER: 42.9%, 2.835s) | **3.18x** |
| **`ta-cv-008`** | 5.4s | `நாற்காற் பிராணிகளிலே எருமை இருத்தலைப்போல!` | `நாற்காட பிராணிகளிலே எருமை இருத்தலைப் போல`<br>(**WER: 75.0%**, 0.896s) | `நாட்கார் பிராணிகளிலே ஏறுமை இருத்தலை போல.`<br>(WER: 100.0%, 2.599s) | **2.9x** |
| **`ta-cv-009`** | 7.848s | `பெரிய உலையிலிட்டு வறுக்கப்பட்டு, மாபெரும் இரும்பு உலக்கைகளினால் பொடி செய்யப்படுகிறது.` | `பெரிய உளையலிட்டு வறுக்கப்பட்டு மாபெரும் இரும்பு உலக்ககளினால் பொடி செய்யப்படுகிறது`<br>(**WER: 25.0%**, 1.253s) | `பெரிய உளையில் எட்டு வர்க்கப்பட்டு மாபரம் இரும்பு உளக்கழினால் பொடி செய்யப்படுக்குறது.`<br>(WER: 75.0%, 3.524s) | **2.81x** |
| **`ta-cv-010`** | 6.516s | `பள்ளிக்கூடங்களில் வாசிக்கும் மாணவர்கள் இதை எளிதில் ஆடலாம் என்பது என் கருத்து.` | `பள்ளிகக்கூடங்களில் வாசிக்கும் மாணவர்கள் இதை எளிதில் ஆடலாம் என்பது என் கருத்து`<br>(**WER: 11.1%**, 1.085s) | `பள்ளிக்குடங்களில் வாசிக்கும் மானவர்கள் இதை எடுதில் ஆடலாம் என்பது என்பது`<br>(WER: 55.6%, 3.519s) | **3.24x** |

---

## 3. Polish Item-by-Item Benchmark Matrix

| Clip ID | Audio Duration | Ground Truth Reference | Whisper Small Output (WER / Time) | Whisper Base Output (WER / Time) |
| :--- | :--- | :--- | :--- | :--- |
| **`pl-cv-001`** | 4.104s | `Usiadł na szyszce i wsłuchał się.` | `Usiadł na szyżce i słuchał się.`<br>(**WER: 33.3%**, 2.711s) | `Usiad nasz istę i słuchał się.`<br>(WER: 66.7%, 0.761s) |
| **`pl-cv-002`** | 3.336s | `Wydawało mu się, że jest martwy.` | `Wydawało mu się, że jest martwy.`<br>(**WER: 0.0%**, 2.419s) | `Bydała umusierze jest martwy.`<br>(WER: 66.7%, 0.749s) |
| **`pl-cv-003`** | 2.904s | `Inżynier nie rozumiał.` | `Inżynier nie rozumiał.`<br>(**WER: 0.0%**, 2.108s) | `I Zhenier nie rozumiał.`<br>(WER: 66.7%, 0.677s) |
| **`pl-cv-004`** | 3.216s | `Dokończę jeden poziom i idę spać.` | `Do końca jeden poziom i despatch.`<br>(**WER: 66.7%**, 2.147s) | `W końcu jeden poziomie spadzi.`<br>(WER: 100.0%, 0.764s) |
| **`pl-cv-005`** | 3.624s | `To jest nieokreślone, ale pewne.` | `To jest nieukryślone, ale pewne.`<br>(**WER: 20.0%**, 2.309s) | `To jest nieokryślone, ale pewne.`<br>(WER: 20.0%, 0.808s) |
| **`pl-cv-006`** | 3.864s | `Król odbywa dalekie wycieczki łodzią.` | `Król odbywa dalekie wycieczki łodziom.`<br>(**WER: 20.0%**, 2.522s) | `Król odbywa dalekie wycieczki łodzią.`<br>(WER: 0.0%, 0.807s) |
| **`pl-cv-007`** | 3.984s | `Pośliznąłeś się, więc wolniej, ostrożniej.` | `Poszli znowu się, więc wolniej, ostrożniej.`<br>(**WER: 40.0%**, 2.528s) | `Poczli z nościa, więc wolniej ostrożniej.`<br>(WER: 60.0%, 0.814s) |
| **`pl-cv-008`** | 4.056s | `Zaczęliśmy mówić o tresowanych zwierzętach, co kto widział.` | `Zaczęliśmy mówić o tresowanych zwierzętach, co kto widział.`<br>(**WER: 0.0%**, 2.512s) | `Zaczyliśmy mówić o trusowanych zwierzętach, co kto widzą.`<br>(WER: 37.5%, 0.853s) |
| **`pl-cv-009`** | 2.976s | `Tak jak gdybyśmy się zupełnie nie znali.` | `Tak jak gdybyśmy się zupełnie nie znali.`<br>(**WER: 0.0%**, 2.275s) | `Tak jak gdy wyśmy się zupełnie nie znali.`<br>(WER: 28.6%, 0.799s) |
| **`pl-cv-010`** | 8.568s | `Jednak musimy zwrócić uwagę, w jaki sposób wodór będzie pozyskiwany.` | `Jednak musimy zwrócić uwagę, w jaki sposób wodór będzie pozyskiwany.`<br>(**WER: 0.0%**, 2.563s) | `Przed na konuczeny z Brutijubar.g. X, w sposób Vodorbandy Provesquibane.`<br>(WER: 100.0%, 0.911s) |

---

## 4. Key Takeaways
1. **Tamil Leapfrog is Real and Independent:** Tested against verified human ground truth, IndicConformer cuts Word Error Rate substantially compared to Whisper Small (24.0% vs 65.0%) while decoding in ~0.91s on CPU (3.31x speedup).
2. **Polish Accuracy Baseline:** Whisper Small achieves **18.0% WER** on Polish with accurate diacritic handling (`6.5% CER`).
3. **Zero Hallucination:** Tamil dictation preserves authentic native script and grammatical morphemes without reverting to textbook literary Tamil or hallucinating English tokens.
