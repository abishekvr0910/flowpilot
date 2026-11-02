# FlowPilot Multilingual Benchmark Corpus: Tamil & Polish (100 Items)

**Status:** Active Benchmark Specification & Evaluation Manifest  
**Version:** 1.0 (v3.1.0 Post-GA Multilingual Expansion)  
**Primary Languages:** Tamil (`ta`) and Polish (`pl`)  
**Total Items:** 100 balanced utterances (50 Tamil, 50 Polish)  
**Invariants:** Zero cloud egress, local evaluation only, FactGuard entity preservation, dual-reference Tamil (Script / Tanglish).  

---

## 1. Corpus Structure & Breakdown

| Language | Group | Count | Characteristics |
| :--- | :--- | :--- | :--- |
| **Tamil (`ta`)** | Conversational (`clean`) | 20 | Daily dialogue, greetings, scheduling, requests |
| **Tamil (`ta`)** | Developer Code-Switching (`developer_code`) | 15 | Mixed Tamil + Latin technical tokens (Docker, Git, React, API, AWS, CI/CD) |
| **Tamil (`ta`)** | FactGuard Entity Preservation (`quantities`) | 15 | Currency (₹ / INR / $), phone numbers, dates, negations (இல்லை, வேண்டாம், அல்ல) |
| **Polish (`pl`)** | Conversational (`clean`) | 20 | Everyday conversational Polish, standard diacritics (ą, ć, ę, ł, ń, ó, ś, ź, ż) |
| **Polish (`pl`)** | Developer & Professional (`developer_code`) | 15 | Software engineering terms, Kubernetes, PostgreSQL, gRPC, pull requests |
| **Polish (`pl`)** | FactGuard Entity Preservation (`quantities`) | 15 | Currency (PLN / zł), VAT, IBAN account numbers, negations (nie, nigdy), ISO numbers |

---

## 2. Tamil Evaluation Items (50)

Each Tamil item includes both the canonical native Tamil script reference (`formatted_reference`) and the deterministic phonological Tanglish transliteration reference (`tanglish_reference`).

| Item ID | Group | Native Tamil Script Reference | Tanglish Transliteration Reference | Critical Entities |
| :--- | :--- | :--- | :--- | :--- |
| `ta-conv-01` | clean | வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்? | *vanakkam, neengal eppadi irukkireergal?* | `வணக்கம்`, `எப்படி` |
| `ta-conv-02` | clean | இன்று காலை வானிலை மிகவும் இனிமையாக உள்ளது. | *indru kaalai vaanilai migavum inimaiyaaga ulladhu.* | `காலை`, `வானிலை` |
| `ta-conv-03` | clean | நாளைக்கு காலை ஒன்பது மணிக்கு நாம் சந்திக்கலாமா? | *naalaikku kaalai onbadhu manikku naam sandhikkalaamaa?* | `ஒன்பது`, `9:00` |
| `ta-conv-04` | clean | எனக்கு ஒரு கப் சூடான காபி வேண்டும். | *enakku oru cup soodaana kaapi vaendum.* | `காபி` |
| `ta-conv-05` | clean | இந்த யோசனை எனக்கு மிகவும் பிடித்திருக்கிறது. | *indha yoasanai enakku migavum piditthirukkiradhu.* | `யோசனை` |
| `ta-conv-06` | clean | நீங்கள் சொன்னதை நான் தெளிவாக புரிந்து கொண்டேன். | *neengal sonnadhai naan thelivaaga purindhu kondaen.* | `தெளிவாக` |
| `ta-conv-07` | clean | நாம் எப்போது மதிய உணவுக்கு செல்லலாம்? | *naam eppoadhu madhiya unavukku sellalaam?* | `மதிய உணவு` |
| `ta-conv-08` | clean | இன்றைய வேலை அனைத்தும் வெற்றிகரமாக முடிந்தது. | *indraya vaelai anaitthum vetrigaramaaga mudindhadhu.* | `வெற்றிகரமாக` |
| `ta-conv-09` | clean | உங்களுடைய உதவிக்கு என் மனமார்ந்த நன்றி. | *ungaludaiya udhavikku en manamaarndha nandri.* | `நன்றி` |
| `ta-conv-10` | clean | நேற்று இரவு பெய்த மழையால் சாலைகள் நனைந்துள்ளன. | *naetru iravu peydha mazhaiyaal saalaigal nanaindhullana.* | `மழை` |
| `ta-conv-11` | clean | இந்த வார இறுதியில் நாம் வெளியூர் பயணம் செல்வோம். | *indha vaara irudhiyil naam veliyoor payanam selvom.* | `பயணம்` |
| `ta-conv-12` | clean | உங்களுக்கு நேரம் கிடைக்கும்போது எனக்கு அழைக்கவும். | *ungalukku naeram kidaikkumpoadhu enakku azhaikkavum.* | `அழைக்கவும்` |
| `ta-conv-13` | clean | அடுத்த வாரம் புதன்கிழமை ஒரு முக்கியமான கூட்டம் இருக்கிறது. | *aduttha vaaram budhankizhamai oru mukkiyamaana koottam irukkiradhu.* | `புதன்கிழமை`, `கூட்டம்` |
| `ta-conv-14` | clean | இதைப்பற்றி நீங்கள் என்ன நினைக்கிறீர்கள் என்று சொல்லுங்கள். | *idhaippatri neengal enna ninaikkireergal endru sollungal.* | `சொல்லுங்கள்` |
| `ta-conv-15` | clean | புதிய திட்டத்தை தொடங்குவதற்கு இதுவே சரியான நேரம். | *pudhiya thittatthai thodanguvadharku idhuvae sariyaana naeram.* | `திட்டம்` |
| `ta-conv-16` | clean | நாம் அனைவரும் ஒன்றாக இணைந்து உழைக்க வேண்டும். | *naam anaivarum ondraaga inaindhu uzhaikka vaendum.* | `ஒன்றாக` |
| `ta-conv-17` | clean | கவலைப்பட வேண்டாம், எல்லாம் விரைவாக சரியாகிவிடும். | *kavalaippada vaendaam, ellaam viraivaaga sariyaagividum.* | `வேண்டாம்`, `சரியாகிவிடும்` |
| `ta-conv-18` | clean | உங்கள் குடும்பத்தினர் அனைவரும் நலமாக இருக்கிறார்களா? | *ungal kudumbatthinar anaivarum nalamaaga irukkiraargalaa?* | `குடும்பத்தினர்` |
| `ta-conv-19` | clean | நேரத்திற்கு தூங்குவதும் விழிப்பதும் உடலுக்கு நல்லது. | *naeratthirku thoonguvadhum vizhippadhum udalukku nalladhu.* | `நல்லது` |
| `ta-conv-20` | clean | மீண்டும் உங்களை சந்தித்ததில் மிக்க மகிழ்ச்சி. | *meendum ungalai sandhitthadhil mikka magizhchi.* | `மகிழ்ச்சி` |
| `ta-dev-01` | developer_code | புதிய Docker container ஐ build செய்து deploy பண்ணுங்க. | *pudhiya Docker container ai build seydhu deploy pannunga.* | `Docker`, `container`, `build`, `deploy` |
| `ta-dev-02` | developer_code | Git pull பண்ணிட்டு feature branch ல checkout பண்ணுங்க. | *Git pull pannittu feature branch la checkout pannunga.* | `Git`, `pull`, `feature branch`, `checkout` |
| `ta-dev-03` | developer_code | Backend API ல 500 error வருது, logs செக் பண்ணுங்க. | *Backend API la 500 error varudhu, logs check pannunga.* | `Backend`, `API`, `500`, `logs` |
| `ta-dev-04` | developer_code | PostgreSQL database connection pool timeout ஆகுது. | *PostgreSQL database connection pool timeout aagudhu.* | `PostgreSQL`, `database`, `timeout` |
| `ta-dev-05` | developer_code | இந்த pull request ல unit tests pass ஆகல. | *indha pull request la unit tests pass aagala.* | `pull request`, `unit tests`, `pass`, `ஆகல` |
| `ta-dev-06` | developer_code | AWS Lambda function latency அதிகமா இருக்கு, optimize பண்ணனும். | *AWS Lambda function latency adhigamaa irukku, optimize pannanum.* | `AWS`, `Lambda`, `latency`, `optimize` |
| `ta-dev-07` | developer_code | React component render cycle ல memory leak இருக்கு. | *React component render cycle la memory leak irukku.* | `React`, `render`, `memory leak` |
| `ta-dev-08` | developer_code | Redis cache invalidate பண்ணிட்டு reload பண்ணுங்க. | *Redis cache invalidate pannittu reload pannunga.* | `Redis`, `cache`, `invalidate`, `reload` |
| `ta-dev-09` | developer_code | Microservices communication gRPC protocol ல நடக்குது. | *Microservices communication gRPC protocol la nadakkudhu.* | `Microservices`, `gRPC`, `protocol` |
| `ta-dev-10` | developer_code | Staging environment ல bug reproduce ஆகுது. | *Staging environment la bug reproduce aagudhu.* | `Staging`, `environment`, `bug`, `reproduce` |
| `ta-dev-11` | developer_code | Kubernetes cluster pod crash loop ல இருக்கு. | *Kubernetes cluster pod crash loop la irukku.* | `Kubernetes`, `pod`, `crash loop` |
| `ta-dev-12` | developer_code | Main branch ல merge conflict வந்துருக்கு, resolve பண்ணுங்க. | *Main branch la merge conflict vandhurukku, resolve pannunga.* | `Main branch`, `merge conflict`, `resolve` |
| `ta-dev-13` | developer_code | CI/CD pipeline test stage ல fail ஆயிடுச்சு. | *CI/CD pipeline test stage la fail aayiducchu.* | `CI/CD`, `pipeline`, `fail` |
| `ta-dev-14` | developer_code | Frontend UI responsive layout flexbox ல fix பண்ணியாச்சு. | *Frontend UI responsive layout flexbox la fix panniyaacchu.* | `Frontend`, `UI`, `flexbox`, `fix` |
| `ta-dev-15` | developer_code | Production server CPU utilization 95% வரை போயிருச்சு. | *Production server CPU utilization 95% varai poayirucchu.* | `Production`, `CPU`, `utilization`, `95%` |
| `ta-fg-01` | quantities | மொத்த திட்ட மதிப்பீடு ₹4,50,000 மற்றும் GST 18% ஆகும். | *mottha thitta madhippeedu ₹4,50,000 mattrum GST 18% aagum.* | `₹4,50,000`, `18%`, `GST` |
| `ta-fg-02` | quantities | கடைசி தேதி 2026 நவம்பர் 15 வரை நீட்டிக்கப்பட்டுள்ளது. | *kadaisi thaedhi 2026 November 15 varai neettikkappattulladhu.* | `2026`, `15` |
| `ta-fg-03` | clean | இந்த பரிவர்த்தனைக்கு எந்தவொரு கட்டணமும் இல்லை. | *indha parivartthanaiykku endhavoru kattanamum illai.* | `இல்லை`, `எந்தவொரு` |
| `ta-fg-04` | quantities | தொலைபேசி எண் +91 98765 43210 என்ற எண்ணில் தொடர்பு கொள்ளவும். | *tholaipaesi enn +91 98765 43210 endra ennil thodarbu kollavum.* | `+91 98765 43210`, `+91` |
| `ta-fg-05` | quantities | அறிக்கை எண் TR-2026-884 இன் படி 42 குறைபாடுகள் பதிவாகியுள்ளன. | *arikkai enn TR-2026-884 in padi 42 kuraipaadugal padhivaagiyullana.* | `TR-2026-884`, `42` |
| `ta-fg-06` | quantities | இந்த ஒப்பந்தத்தில் மாதாந்திர வாடகை ₹75,000 என குறிப்பிடப்பட்டுள்ளது. | *indha oppandhatthil maadhaandhira vaadagai ₹75,000 ena kurippidappattulladhu.* | `₹75,000` |
| `ta-fg-07` | clean | எந்த சூழ்நிலையிலும் கடவுச்சொல்லை பிறருடன் பகிரக்கூடாது. | *endha soozhnilaiyilum kadavuchollai pirarudan pagirakkoodaadhu.* | `பகிரக்கூடாது`, `கடவுச்சொல்` |
| `ta-fg-08` | quantities | வங்கி கணக்கு எண் 042210010955 என்ற கணக்கிற்கு பணம் அனுப்பப்பட்டது. | *vangi kanakku enn 042210010955 endra kanakkirku panam anuppappattadhu.* | `042210010955` |
| `ta-fg-09` | quantities | ஆய்வக சோதனை முடிவுகள் 99.8% துல்லியமாக வந்துள்ளன. | *aayvaga soadhanai mudivugal 99.8% thulliyamaaga vandhullana.* | `99.8%` |
| `ta-fg-10` | quantities | நிறுவனத்தின் ஆண்டு வருவாய் $1.2M இலக்கை எட்டியுள்ளது. | *niruvanatthin aandu varuvaay $1.2M ilakkai ettiyulladhu.* | `$1.2M` |
| `ta-fg-11` | developer_code | சர்வர் IP முகவரி 192.168.1.150 போர்ட் 8080 இல் இயங்குகிறது. | *server IP mugavari 192.168.1.150 port 8080 il iyangugiradhu.* | `192.168.1.150`, `8080` |
| `ta-fg-12` | clean | விண்ணப்பம் நிராகரிக்கப்படவில்லை, பரிசீலனையில் உள்ளது. | *vinnappam niraagarikkappadavillai, pariseelanaiyil ulladhu.* | `நிராகரிக்கப்படவில்லை` |
| `ta-fg-13` | quantities | வெப்பநிலை 37.5 டிகிரி செல்சியஸாக பதிவாகியுள்ளது. | *veppanilai 37.5 degree Celsius-aaga padhivaagiyulladhu.* | `37.5`, `செல்சியஸ்` |
| `ta-fg-14` | quantities | அடுத்த தணிக்கை தேதி 2027 ஜனவரி 10 என நிர்ணயிக்கப்பட்டுள்ளது. | *aduttha thanikkai thaedhi 2027 January 10 ena nirnayikkappattulladhu.* | `2027`, `10` |
| `ta-fg-15` | quantities | பாதிக்கப்பட்ட கணினிகளின் எண்ணிக்கை 12 மட்டுமே, 15 அல்ல. | *baadhikkappatta kaninigalin ennikkai 12 mattumae, 15 alla.* | `12`, `15`, `அல்ல`, `மட்டுமே` |

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
