# FlowPilot Multilingual Benchmark Corpus: Tamil & Polish (100 Items)

**Status:** Active Benchmark Specification & Evaluation Manifest  
**Version:** 2.0 (Spoken-Style Tamil Dictation & Calibrated Tanglish Transliteration)  
**Primary Languages:** Tamil (`ta`) and Polish (`pl`)  
**Total Items:** 100 balanced utterances (50 Tamil, 50 Polish)  
**Invariants:** Zero cloud egress, local evaluation only, FactGuard entity preservation, dual-reference Tamil (Script / Tanglish).  

---

## 1. Corpus Structure & Breakdown

| Language | Group | Count | Characteristics |
| :--- | :--- | :--- | :--- |
| **Tamil (`ta`)** | Conversational (`clean`) | 20 | Authentic spoken dialogue, greetings, scheduling, requests (e.g. எப்படி இருக்கீங்க) |
| **Tamil (`ta`)** | Developer Code-Switching (`developer_code`) | 15 | Mixed Tamil + Latin technical tokens (Docker, Git, React, API, AWS, CI/CD) |
| **Tamil (`ta`)** | FactGuard Entity Preservation (`quantities`) | 15 | Currency (₹ / INR / $), phone numbers, dates, negations (இல்லை, வேண்டாம், அல்ல) |
| **Polish (`pl`)** | Conversational (`clean`) | 20 | Everyday conversational Polish, standard diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż) |
| **Polish (`pl`)** | Developer & Professional (`developer_code`) | 15 | Software engineering terms, Kubernetes, PostgreSQL, gRPC, pull requests |
| **Polish (`pl`)** | FactGuard Entity Preservation (`quantities`) | 15 | Currency (PLN / zł), VAT, IBAN account numbers, negations (nie, nigdy), ISO numbers |

---

## 2. Tamil Evaluation Items (50)

Each Tamil item includes both the spoken reference / native script reference (`formatted_reference`) and the calibrated phonetic Tanglish transliteration reference (`tanglish_reference`).

| Item ID | Group | Native Tamil Script Reference | Tanglish Transliteration Reference | Critical Entities |
| :--- | :--- | :--- | :--- | :--- |
| `ta-conv-01` | clean | வணக்கம், நீங்க எப்படி இருக்கீங்க? | *vanakkam, neenga eppadi irukkeenga?* | `வணக்கம்`, `எப்படி`, `இருக்கீங்க` |
| `ta-conv-02` | clean | இன்னைக்கு காலையில வானிலை ரொம்ப நல்லா இருக்கு. | *innaikku kaalaiyila vaanilai romba nallaa irukku.* | `காலையில`, `வானிலை`, `நல்லா` |
| `ta-conv-03` | clean | நாளைக்கு காலைல ஒன்பது மணிக்கு நாம மீட் பண்ணலாமா? | *naalaikku kaalaila onbadhu manikku naama meet pannalaamaa?* | `ஒன்பது`, `9:00`, `மீட்` |
| `ta-conv-04` | clean | எனக்கு ஒரு cup சூடான காபி வேணும். | *enakku oru cup soodaana kaapi venum.* | `cup`, `காபி`, `வேணும்` |
| `ta-conv-05` | clean | இந்த idea எனக்கு ரொம்ப பிடிச்சிருக்கு. | *indha idea enakku romba pidichirukku.* | `idea`, `பிடிச்சிருக்கு` |
| `ta-conv-06` | clean | நீங்க சொன்னத நான் தெளிவா புரிஞ்சுகிட்டேன். | *neenga sonnadha naan thelivaa purinjugitten.* | `தெளிவா`, `புரிஞ்சுகிட்டேன்` |
| `ta-conv-07` | clean | நாம எப்போ lunchக்கு போலாம்? | *naama eppo lunchukku polaam?* | `lunch`, `போலாம்` |
| `ta-conv-08` | clean | இன்னைக்கு வேலை எல்லாம் நல்லபடியா முடிஞ்சது. | *innaikku velai ellaam nallabadiyaa mudinjadhu.* | `நல்லபடியா`, `முடிஞ்சது` |
| `ta-conv-09` | clean | உங்க helpக்கு ரொம்ப நன்றி. | *unga helpukku romba nandri.* | `help`, `நன்றி` |
| `ta-conv-10` | clean | நேத்து ராத்திரி பெஞ்ச மழையால ரோடு எல்லாம் நனைஞ்சிருக்கு. | *netthu raatthiri penja mazhaiyaala road-u ellaam nanainjirukku.* | `மழை`, `ரோடு` |
| `ta-conv-11` | clean | இந்த weekend நாம ஊருக்கு போலாம். | *indha weekend naama oorukku polaam.* | `weekend`, `போலாம்` |
| `ta-conv-12` | clean | உங்களுக்கு time கிடைக்கும்போது எனக்கு call பண்ணுங்க. | *ungalukku time kidaikkumbodhu enakku call pannunga.* | `time`, `call` |
| `ta-conv-13` | clean | அடுத்த வாரம் புதன்கிழமை ஒரு முக்கியமான meeting இருக்கு. | *aduttha vaaram budhankizhamai oru mukkiyamaana meeting irukku.* | `புதன்கிழமை`, `meeting` |
| `ta-conv-14` | clean | இதப்பத்தி நீங்க என்ன நினைக்கிறீங்கன்னு சொல்லுங்க. | *idhappatthi neenga enna ninaikkireengannu sollunga.* | `சொல்லுங்க` |
| `ta-conv-15` | clean | புது project start பண்ண இதுதான் correct-ஆன time. | *pudhu project start panna idhudhaan correct-aana time.* | `project`, `start`, `time` |
| `ta-conv-16` | clean | நாம எல்லாரும் ஒண்ணா சேர்ந்து வேலை செய்யணும். | *naama ellaarum onnaa serndhu velai seyyanum.* | `ஒண்ணா`, `வேலை` |
| `ta-conv-17` | clean | கவலைப்படாதீங்க, எல்லாம் சீக்கிரம் சரியாகிடும். | *kavalaippadaadheenga, ellaam seekkiram sariyaagidum.* | `கவலைப்படாதீங்க`, `சரியாகிடும்` |
| `ta-conv-18` | clean | வீட்ல எல்லாரும் நல்லா இருக்காங்களா? | *veetla ellaarum nallaa irukkaangalaa?* | `நல்லா`, `இருக்காங்களா` |
| `ta-conv-19` | clean | நேரத்துக்கு தூங்கி எந்திரிக்கிறது உடம்புக்கு நல்லது. | *neratthukku thoongi endhirikkiradhu udambukku nalladhu.* | `நல்லது`, `உடம்புக்கு` |
| `ta-conv-20` | clean | மறுபடியும் உங்கள பாத்ததுல ரொம்ப சந்தோஷம். | *marubadiyum ungala paatthadhula romba sandhosham.* | `சந்தோஷம்` |
| `ta-dev-01` | developer_code | புது Docker container build பண்ணி deploy பண்ணுங்க. | *pudhu Docker container build panni deploy pannunga.* | `Docker`, `container`, `build`, `deploy` |
| `ta-dev-02` | developer_code | Git pull பண்ணிட்டு feature branch ல checkout பண்ணுங்க. | *Git pull pannittu feature branch la checkout pannunga.* | `Git`, `pull`, `feature branch`, `checkout` |
| `ta-dev-03` | developer_code | Backend API ல 500 error வருது, logs செக் பண்ணுங்க. | *Backend API la 500 error varudhu, logs check pannunga.* | `Backend`, `API`, `500`, `logs`, `check` |
| `ta-dev-04` | developer_code | PostgreSQL database connection pool timeout ஆகுது. | *PostgreSQL database connection pool timeout aagudhu.* | `PostgreSQL`, `database`, `timeout` |
| `ta-dev-05` | developer_code | இந்த pull request ல unit tests இன்னும் pass ஆகல. | *indha pull request la unit tests innum pass aagala.* | `pull request`, `unit tests`, `pass`, `ஆகல` |
| `ta-dev-06` | developer_code | AWS Lambda function latency அதிகமா இருக்கு, optimize பண்ணனும். | *AWS Lambda function latency adhigamaa irukku, optimize pannanum.* | `AWS`, `Lambda`, `latency`, `optimize` |
| `ta-dev-07` | developer_code | React component render cycle ல memory leak இருக்கு. | *React component render cycle la memory leak irukku.* | `React`, `render`, `memory leak` |
| `ta-dev-08` | developer_code | Redis cache invalidate பண்ணிட்டு பேஜ்ஜ reload பண்ணுங்க. | *Redis cache invalidate pannittu page-a reload pannunga.* | `Redis`, `cache`, `invalidate`, `reload` |
| `ta-dev-09` | developer_code | Microservices communication gRPC protocol ல நடக்குது. | *Microservices communication gRPC protocol la nadakkudhu.* | `Microservices`, `gRPC`, `protocol` |
| `ta-dev-10` | developer_code | Staging environment ல இந்த bug reproduce ஆகுது. | *Staging environment la indha bug reproduce aagudhu.* | `Staging`, `environment`, `bug`, `reproduce` |
| `ta-dev-11` | developer_code | Kubernetes cluster pod crash loop ல இருக்கு. | *Kubernetes cluster pod crash loop la irukku.* | `Kubernetes`, `pod`, `crash loop` |
| `ta-dev-12` | developer_code | Main branch ல merge conflict வந்துருக்கு, resolve பண்ணுங்க. | *Main branch la merge conflict vandhurukku, resolve pannunga.* | `Main branch`, `merge conflict`, `resolve` |
| `ta-dev-13` | developer_code | CI/CD pipeline test stage ல fail ஆயிடுச்சு. | *CI/CD pipeline test stage la fail aayiduchu.* | `CI/CD`, `pipeline`, `fail` |
| `ta-dev-14` | developer_code | Frontend UI responsive layout flexbox ல fix பண்ணியாச்சு. | *Frontend UI responsive layout flexbox la fix panniyaachu.* | `Frontend`, `UI`, `flexbox`, `fix` |
| `ta-dev-15` | developer_code | Production server CPU utilization 95% வரை போயிருச்சு. | *Production server CPU utilization 95% varai poyiruchu.* | `Production`, `CPU`, `utilization`, `95%` |
| `ta-fg-01` | quantities | மொத்த திட்ட மதிப்பீடு ₹4,50,000 மற்றும் GST 18% ஆகும். | *mottha thitta madhippeedu ₹4,50,000 mattrum GST 18% aagum.* | `₹4,50,000`, `18%`, `GST` |
| `ta-fg-02` | quantities | கடைசி தேதி 2026 நவம்பர் 15 வரை நீட்டிக்கப்பட்டுள்ளது. | *kadaisi thedhi 2026 November 15 varai neettikkappattulladhu.* | `2026`, `15`, `நவம்பர்` |
| `ta-fg-03` | clean | இந்த பரிவர்த்தனைக்கு எந்தவொரு கட்டணமும் இல்லை. | *indha parivartthanaikku endhavoru kattanamum illai.* | `இல்லை`, `எந்தவொரு` |
| `ta-fg-04` | quantities | தொலைபேசி எண் +91 98765 43210 என்ற எண்ணில் தொடர்பு கொள்ளவும். | *tholaipesi enn +91 98765 43210 endra ennil thodarbu kollavum.* | `+91 98765 43210`, `+91` |
| `ta-fg-05` | quantities | அறிக்கை எண் TR-2026-884 இன் படி 42 குறைபாடுகள் பதிவாகியுள்ளன. | *arikkai enn TR-2026-884 in padi 42 kuraipaadugal padhivaagiyullana.* | `TR-2026-884`, `42` |
| `ta-fg-06` | quantities | இந்த ஒப்பந்தத்தில் மாதாந்திர வாடகை ₹75,000 என குறிப்பிடப்பட்டுள்ளது. | *indha oppandhatthil maadhaandhira vaadagai ₹75,000 ena kurippidappattulladhu.* | `₹75,000` |
| `ta-fg-07` | clean | எந்த சூழ்நிலையிலும் கடவுச்சொல்லை பிறருடன் பகிரக்கூடாது. | *endha soozhnilaiyilum kadavuchollai pirarudan pagirakkoodaadhu.* | `பகிரக்கூடாது`, `கடவுச்சொல்` |
| `ta-fg-08` | quantities | வங்கி கணக்கு எண் 042210010955 என்ற கணக்கிற்கு பணம் அனுப்பப்பட்டது. | *vangi kanakku enn 042210010955 endra kanakkirku panam anuppappattadhu.* | `042210010955` |
| `ta-fg-09` | quantities | ஆய்வக சோதனை முடிவுகள் 99.8% துல்லியமாக வந்துள்ளன. | *aayvaga sodhanai mudivugal 99.8% thulliyamaaga vandhullana.* | `99.8%` |
| `ta-fg-10` | quantities | நிறுவனத்தின் ஆண்டு வருவாய் $1.2M இலக்கை எட்டியுள்ளது. | *niruvanatthin aandu varuvaay $1.2M ilakkai ettiyulladhu.* | `$1.2M` |
| `ta-fg-11` | developer_code | சர்வர் IP முகவரி 192.168.1.150 போர்ட் 8080 இல் இயங்குகிறது. | *server IP mugavari 192.168.1.150 port 8080 il iyangugiradhu.* | `192.168.1.150`, `8080` |
| `ta-fg-12` | clean | விண்ணப்பம் நிராகரிக்கப்படவில்லை, பரிசீலனையில் உள்ளது. | *vinnappam niraagarikkappadavillai, pariseelanaiyil ulladhu.* | `நிராகரிக்கப்படவில்லை` |
| `ta-fg-13` | quantities | வெப்பநிலை 37.5 டிகிரி செல்சியஸாக பதிவாகியுள்ளது. | *veppanilai 37.5 degree Celsius-aaga padhivaagiyulladhu.* | `37.5`, `செல்சியஸ்` |
| `ta-fg-14` | quantities | அடுத்த தணிக்கை தேதி 2027 ஜனவரி 10 என நிர்ணயிக்கப்பட்டுள்ளது. | *aduttha thanikkai thedhi 2027 January 10 ena nirnayikkappattulladhu.* | `2027`, `10`, `ஜனவரி` |
| `ta-fg-15` | quantities | பாதிக்கப்பட்ட கணினிகளின் எண்ணிக்கை 12 மட்டுமே, 15 அல்ல. | *baadhikkappatta kaninigalin ennikkai 12 mattume, 15 alla.* | `12`, `15`, `அல்ல`, `மட்டுமே` |

---

## 3. Polish Evaluation Items (50)

| Item ID | Group | Spoken / Formatted Reference | Critical Entities |
| :--- | :--- | :--- | :--- |
| `pl-conv-01` | clean | Dzień dobry, jak się dzisiaj czujesz? | `Dzień dobry` |
| `pl-conv-02` | clean | Pogoda za oknem jest dzisiaj wyjątkowo słoneczna. | `słoneczna` |
| `pl-conv-03` | clean | Czy możemy spotkać się jutro o godzinie dziesiątej? | `dziesiątej`, `10:00` |
| `pl-conv-04` | clean | Poproszę o filiżankę gorącej kawy z mlekiem. | `kawy` |
| `pl-conv-05` | clean | Ten pomysł bardzo mi się podoba i ma duży potencjał. | `pomysł` |
| `pl-conv-06` | clean | Wszystko zrozumiałem i zgadzam się z Twoją propozycją. | `zrozumiałem` |
| `pl-conv-07` | clean | Kiedy masz czas, żeby pójść na wspólny obiad? | `obiad` |
| `pl-conv-08` | clean | Dzisiejsze zadania zostały zakończone z pełnym sukcesem. | `sukcesem` |
| `pl-conv-09` | clean | Bardzo dziękuję za Twoją pomoc i poświęcony czas. | `dziękuję` |
| `pl-conv-10` | clean | Po wczorajszym deszczu powietrze jest rześkie i świeże. | `powietrze` |
| `pl-conv-11` | clean | W ten weekend planujemy krótki wyjazd za miasto. | `wyjazd` |
| `pl-conv-12` | clean | Zadzwoń do mnie, proszę, gdy tylko będziesz wolny. | `Zadzwoń` |
| `pl-conv-13` | clean | W przyszłą środę odbędzie się ważne spotkanie zespołu. | `środę`, `spotkanie` |
| `pl-conv-14` | clean | Co sądzisz na temat nowego harmonogramu pracy? | `harmonogramu` |
| `pl-conv-15` | clean | To jest właściwy moment na rozpoczęcie tego projektu. | `projektu` |
| `pl-conv-16` | clean | Wszyscy razem musimy skupić się na osiągnięciu celu. | `celu` |
| `pl-conv-17` | clean | Nie martw się, wszystko wkrótce wróci do normy. | `Nie martw się` |
| `pl-conv-18` | clean | Czy wszyscy w Twojej rodzinie czują się dobrze? | `rodzinie` |
| `pl-conv-19` | clean | Regularny sen jest kluczem do dobrego samopoczucia. | `sen` |
| `pl-conv-20` | clean | Bardzo się cieszę, że znowu mogliśmy się spotkać. | `cieszę` |
| `pl-dev-01` | developer_code | Zbuduj nowy kontener Docker i wdróż go na staging. | `Docker`, `staging` |
| `pl-dev-02` | developer_code | Zrób git pull i przełącz się na gałąź feature/auth. | `git pull`, `feature/auth` |
| `pl-dev-03` | developer_code | Backendowe API zwraca błąd 500 w logach aplikacji. | `API`, `500`, `logach` |
| `pl-dev-04` | developer_code | Pula połączeń bazy danych PostgreSQL osiągnęła limit. | `PostgreSQL`, `limit` |
| `pl-dev-05` | developer_code | Wszystkie testy jednostkowe w pull requeście zakończyły się sukcesem. | `pull requeście`, `testy`, `sukcesem` |
| `pl-dev-06` | developer_code | Funkcja AWS Lambda ma zbyt wysokie opóźnienie i wymaga optymalizacji. | `AWS Lambda`, `opóźnienie`, `optymalizacji` |
| `pl-dev-07` | developer_code | Komponent w React ma wyciek pamięci podczas cyklu renderowania. | `React`, `wyciek pamięci`, `renderowania` |
| `pl-dev-08` | developer_code | Wyczyść pamięć podręczną Redis i przeładuj stronę. | `Redis`, `przeładuj` |
| `pl-dev-09` | developer_code | Komunikacja między mikroserwisami odbywa się przez gRPC. | `mikroserwisami`, `gRPC` |
| `pl-dev-10` | developer_code | Udało się odtworzyć błąd na środowisku stagingowym. | `błąd`, `stagingowym` |
| `pl-dev-11` | developer_code | Pod w klastrze Kubernetes znajduje się w stanie CrashLoopBackOff. | `Kubernetes`, `CrashLoopBackOff` |
| `pl-dev-12` | developer_code | Na gałęzi master wystąpił konflikt scalania, który trzeba rozwiązać. | `master`, `konflikt` |
| `pl-dev-13` | developer_code | Etap testów w potoku CI/CD zakończył się niepowodzeniem. | `CI/CD`, `niepowodzeniem` |
| `pl-dev-14` | developer_code | Responsywny układ interfejsu użytkownika został naprawiony w flexbox. | `flexbox`, `interfejsu` |
| `pl-dev-15` | developer_code | Użycie procesora na serwerze produkcyjnym wzrosło do 95%. | `procesora`, `95%` |
| `pl-fg-01` | quantities | Całkowity koszt projektu wynosi 45 000 zł plus 23% VAT. | `45 000 zł`, `23%`, `VAT` |
| `pl-fg-02` | quantities | Ostateczny termin upływa 15 listopada 2026 roku. | `15 listopada 2026`, `2026` |
| `pl-fg-03` | clean | Ta transakcja nie podlega żadnym dodatkowym opłatom. | `nie podlega`, `żadnym` |
| `pl-fg-04` | quantities | W razie pytań prosimy o kontakt pod numerem +48 601 234 567. | `+48 601 234 567`, `+48` |
| `pl-fg-05` | quantities | Według raportu technicznego TR-2026-884 wykryto dokładnie 42 usterki. | `TR-2026-884`, `42` |
| `pl-fg-06` | quantities | Miesięczny koszt wynajmu lokalu wynosi dokładnie 7 500 PLN. | `7 500 PLN`, `PLN` |
| `pl-fg-07` | clean | Nigdy pod żadnym pozorem nie udostępniaj hasła osobom trzecim. | `Nigdy`, `nie udostępniaj`, `hasła` |
| `pl-fg-08` | quantities | Przelew został wysłany na numer konta 42 1090 2402 0000 0001 2345 6789. | `42 1090 2402 0000 0001 2345 6789` |
| `pl-fg-09` | quantities | Dokładność pomiaru w laboratorium wynosi 99,8% według normy ISO. | `99,8%`, `ISO` |
| `pl-fg-10` | quantities | Roczny przychód firmy osiągnął 1,2 mln USD w czwartym kwartale. | `1,2 mln USD`, `USD` |
| `pl-fg-11` | developer_code | Adres IP serwera to 192.168.1.150 na porcie 8080. | `192.168.1.150`, `8080` |
| `pl-fg-12` | clean | Wniosek nie został odrzucony, lecz przekazany do dalszej weryfikacji. | `nie został odrzucony` |
| `pl-fg-13` | quantities | Temperatura pacjenta wynosiła dokładnie 37,5 stopnia Celsjusza. | `37,5`, `Celsjusza` |
| `pl-fg-14` | quantities | Kolejny audyt zaplanowano na dzień 10 stycznia 2027 roku. | `10 stycznia 2027`, `2027` |
| `pl-fg-15` | quantities | Liczba uszkodzonych pakietów wynosi 12, a nie 15. | `12`, `15`, `nie 15` |

---

## 4. Evaluation Methodology & Metric Protocol

1. **Raw Acoustic WER (Word Error Rate):** Calculated against `spoken_reference` using Unicode tokenization.
2. **Unicode Character Error Rate (CER):** Measures character accuracy normalized with NFC, preserving Indic combining diacritics.
3. **Tanglish Dual-Mode Score:** When `tamil_script_mode == 'tanglish'`, output is scored against `tanglish_reference`.
4. **FactGuard Critical Entity Preservation:** Scored strictly on numbers, currency symbols, identifiers, and negations.
5. **Zero Cloud Egress:** All acoustic evaluation runs locally on CPU / ONNX Runtime.
