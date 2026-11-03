# FlowPilot Independent Multilingual Accuracy Benchmark

**Date:** 2026-11-04 00:23:50  
**Evaluation Scope:** 20 Consented Mozilla Common Voice 17.0 Audio Clips (10 Tamil, 10 Polish)  
**Ground Truth:** Human Reference Transcripts (Independent of ASR Models)  
**Zero Cloud Egress Invariant:** 100% Verified (Local CPU Inference, 0 Outbound Sockets)

---

## 1. Executive Summary

| Language | Metric | AI4Bharat IndicConformer Medium (137 MB INT8) | Whisper Small (461 MB INT8) | Whisper Base (74 MB INT8) | Leapfrog / Accuracy Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tamil (`ta`)** | **Word Error Rate (WER)** | **18.5%** | 61.7% | 81.9% | **70.1% relative error reduction** |
| **Tamil (`ta`)** | **Character Error Rate (CER)** | **4.4%** | 19.8% | — | **77.6% relative CER reduction** |
| **Tamil (`ta`)** | **Average Latency** | **0.71s** | 2.81s | 0.90s | **3.93x faster than Whisper Small** |
| **Polish (`pl`)** | **Word Error Rate (WER)** | *(Specialist in Dev)* | **18.0%** | 49.6% | Whisper Small delivers high accuracy on Polish |
| **Polish (`pl`)** | **Average Latency** | — | **2.21s** | 0.72s | Clean baseline established for Parakeet |

---

## 2. Tamil Item-by-Item Benchmark Matrix

| Clip ID | Audio Duration | Ground Truth Reference | IndicConformer Output (WER / Time) | Whisper Small Output (WER / Time) | Speedup |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ta-cv-001`** | 6.696s | `பாலாஜி என்பது பாலன் என்ற பொருளுடையது.` | `பாலாஜி என்பது பாலன் என்ற பெருளுடையது`<br>(**WER: 20.0%**, 0.792s) | `Balaji என்பது, Palan, என்ற பிருளுடியது.`<br>(WER: 60.0%, 3.223s) | **4.07x** |
| **`ta-cv-002`** | 7.38s | `சீக்கிரத்தில் ஐநூறு ரூபாய் செலவழித்து அவரது முழு உருவப்படமொன்று சபையில் வைத்தோம்.` | `சீக்கிரத்தில் ஐநூறு ரூபாய் செலவழித்து அவரது முழு உருவப்படமொன்று சபையில் வைத்தோம்`<br>(**WER: 0.0%**, 0.917s) | `சீக்கிரத்தில் 500 ரோபாய் சலவழித்து அவருது முழு உருவப்படம் என்று சபையில் வைத்தோம்.`<br>(WER: 66.7%, 3.063s) | **3.34x** |
| **`ta-cv-003`** | 3.96s | `பகலில் இயங்கிக் கொண்டே இருப்பர்.` | `பகலில் இயங்கிக் கொண்டே இருப்பர்`<br>(**WER: 0.0%**, 0.505s) | `பகலில் எங்கிக்கும்டையிருப்பேன்.`<br>(WER: 75.0%, 2.379s) | **4.71x** |
| **`ta-cv-004`** | 3.456s | `மிகுதியும் பயன் விளையும்.` | `மிகுதியும் பயன் விளையும்`<br>(**WER: 0.0%**, 0.45s) | `நிகுதியம் பயன் விளையும்`<br>(WER: 33.3%, 2.547s) | **5.66x** |
| **`ta-cv-005`** | 4.428s | `புதுப்புனலில் பாய்ந்து நீந்தி விளையாடுகிறாள்.` | `புது புனலில் பாய்ந்து நீந்தி விளையாடுகிறாள்`<br>(**WER: 50.0%**, 0.589s) | `புதுப் புனலில் பாய்ந்து நீந்தி விளியாடக்குராள்.`<br>(WER: 75.0%, 2.617s) | **4.44x** |
| **`ta-cv-006`** | 5.256s | `அது தாவிக்கொண்டு சந்தோஷமாக அவர்கள் அருகில் வந்தது.` | `அது தாவிக்கொண்டு சந்தோஷமாக அவர்கள் அருகில் வந்தது`<br>(**WER: 0.0%**, 0.714s) | `அது தாபிக்கும் சந்தோஷமாக அவர்கள் அறைக்குள் வந்தது.`<br>(WER: 33.3%, 2.655s) | **3.72x** |
| **`ta-cv-007`** | 5.256s | `கோடைக்கானல் பல நாட்டு மக்களுக்கும் ஒரு தங்கல்மனை போன்றது.` | `கோடைக்கானல் பல நாட்டு மக்களுக்கும் ஒரு தங்கள் மனை போன்றது`<br>(**WER: 28.6%**, 0.659s) | `குடைக்கானல் பல நாட்டு மக்களுக்கும் ஒரு தங்கள் மனைப்போன்றது.`<br>(WER: 42.9%, 2.938s) | **4.46x** |
| **`ta-cv-008`** | 5.4s | `நாற்காற் பிராணிகளிலே எருமை இருத்தலைப்போல!` | `நாற்காற் பிராணிகளிலே எருமை இருத்தலை போல`<br>(**WER: 50.0%**, 0.689s) | `நாட்கார் பிராணிகளிலே ஏறுமை இருத்தலை போல.`<br>(WER: 100.0%, 2.404s) | **3.49x** |
| **`ta-cv-009`** | 7.848s | `பெரிய உலையிலிட்டு வறுக்கப்பட்டு, மாபெரும் இரும்பு உலக்கைகளினால் பொடி செய்யப்படுகிறது.` | `பெரிய உளையிலிட்டு வறுக்கப்பட்டு மாபெரும் இரும்பு உலக்ககளினால் பொடி செய்யப்படுகிறது`<br>(**WER: 25.0%**, 1.001s) | `பெரிய உளையில் எட்டு வர்க்கப்பட்டு, மாபரம் இரும்பு உளக்கழினால் பொடி செய்யப்படுக்குறது.`<br>(WER: 75.0%, 3.159s) | **3.16x** |
| **`ta-cv-010`** | 6.516s | `பள்ளிக்கூடங்களில் வாசிக்கும் மாணவர்கள் இதை எளிதில் ஆடலாம் என்பது என் கருத்து.` | `பள்ளிகக்கூடங்களில் வாசிக்கும் மாணவர்கள் இதை எளிதில் ஆடலாம் என்பது என் கருத்து`<br>(**WER: 11.1%**, 0.826s) | `பள்ளிக்குடங்களில் வாசிக்கும் மானவர்கள் இதை எடுதில் ஆடலாம் என்பது என்பது`<br>(WER: 55.6%, 3.065s) | **3.71x** |

---

## 3. Polish Item-by-Item Benchmark Matrix

| Clip ID | Audio Duration | Ground Truth Reference | Whisper Small Output (WER / Time) | Whisper Base Output (WER / Time) |
| :--- | :--- | :--- | :--- | :--- |
| **`pl-cv-001`** | 4.104s | `Usiadł na szyszce i wsłuchał się.` | `Usiadł na szyżce i słuchał się.`<br>(**WER: 33.3%**, 2.12s) | `Usiad nasz istę i słuchał się.`<br>(WER: 66.7%, 0.738s) |
| **`pl-cv-002`** | 3.336s | `Wydawało mu się, że jest martwy.` | `Wydawało mu się, że jest martwy.`<br>(**WER: 0.0%**, 2.371s) | `Bydawał mu się, że jest martwy.`<br>(WER: 16.7%, 0.806s) |
| **`pl-cv-003`** | 2.904s | `Inżynier nie rozumiał.` | `Inżynier nie rozumiał.`<br>(**WER: 0.0%**, 2.354s) | `I Zhenier nie rozumiał.`<br>(WER: 66.7%, 0.676s) |
| **`pl-cv-004`** | 3.216s | `Dokończę jeden poziom i idę spać.` | `Do końca jeden poziom i despatch.`<br>(**WER: 66.7%**, 2.535s) | `W końcu jeden poziomie spadzi.`<br>(WER: 100.0%, 0.723s) |
| **`pl-cv-005`** | 3.624s | `To jest nieokreślone, ale pewne.` | `To jest nieukryślone, ale pewne.`<br>(**WER: 20.0%**, 2.303s) | `To jest nieokryślone, ale pewne.`<br>(WER: 20.0%, 0.814s) |
| **`pl-cv-006`** | 3.864s | `Król odbywa dalekie wycieczki łodzią.` | `Król odbywa dalekie wycieczki łodziom.`<br>(**WER: 20.0%**, 2.122s) | `Król odbywa dalekie wycieczki łodzią.`<br>(WER: 0.0%, 0.653s) |
| **`pl-cv-007`** | 3.984s | `Pośliznąłeś się, więc wolniej, ostrożniej.` | `Poszli znowu się, więc wolniej, ostrożniej.`<br>(**WER: 40.0%**, 2.044s) | `Poczli z nościa, więc wolniej ostrożniej.`<br>(WER: 60.0%, 0.644s) |
| **`pl-cv-008`** | 4.056s | `Zaczęliśmy mówić o tresowanych zwierzętach, co kto widział.` | `Zaczęliśmy mówić o tresowanych zwierzętach, co kto widział.`<br>(**WER: 0.0%**, 2.053s) | `Zaczyliśmy mówić o trusowanych zwierzętach, co kto widzą.`<br>(WER: 37.5%, 0.698s) |
| **`pl-cv-009`** | 2.976s | `Tak jak gdybyśmy się zupełnie nie znali.` | `Tak jak gdybyśmy się zupełnie nie znali.`<br>(**WER: 0.0%**, 2.055s) | `Tak jak gdy wyśmy się zupełnie nie znali.`<br>(WER: 28.6%, 0.654s) |
| **`pl-cv-010`** | 8.568s | `Jednak musimy zwrócić uwagę, w jaki sposób wodór będzie pozyskiwany.` | `Jednak musimy zwrócić uwagę, w jaki sposób wodór będzie pozyskiwany.`<br>(**WER: 0.0%**, 2.166s) | `Przed na konuczeny z Brutijubar.g. x. Borderbandy Provesquibane.`<br>(WER: 100.0%, 0.76s) |

---

## 4. Key Takeaways
1. **Tamil Leapfrog is Real and Independent:** Tested against verified human ground truth, IndicConformer cuts Word Error Rate substantially compared to Whisper Small (18.5% vs 61.7%) while decoding in ~0.71s on CPU (3.93x speedup).
2. **Polish Accuracy Baseline:** Whisper Small achieves **18.0% WER** on Polish with accurate diacritic handling (`6.5% CER`).
3. **Zero Hallucination:** Tamil dictation preserves authentic native script and grammatical morphemes without reverting to textbook literary Tamil or hallucinating English tokens.
