# FlowPilot Official Landing Page Copy & Marketing Collateral

---

## [HERO SECTION]

**Badge:** 🔒 100% Offline • Zero Cloud Egress • Built for Windows

# Speak at 140 WPM.  
# Write at the Speed of Thought.  
# Zero Syllables Sent to the Cloud.

FlowPilot is the AI-powered voice writing assistant engineered for professionals who demand the magic of natural speech dictation with uncompromising enterprise data privacy.

[ **Download FlowPilot for Windows (Portable)** ] *(Free Evaluation • No Account Required)*  
[ **Explore Enterprise Licensing** ]

*Supports Windows 10 & 11 • Standard Intel/AMD CPU • No GPU Required*

---

## [THE PROBLEM STATEMENT]

### Why Legacy Dictation & Cloud Tools Fall Short

| The Frustration | What Happens in Practice | How FlowPilot Solves It |
|:---|:---|:---|
| **Privacy Restrictions** | Cloud tools (Wispr Flow, Otter) stream your audio to remote servers—violating enterprise NDAs, HIPAA guidelines, and client confidentiality. | **100% Local Execution:** FlowPilot runs entirely inside your machine's memory. Exactly 0 bytes leave your device. |
| **Hallucinations & Drift** | Generic cloud LLMs often drop critical negations (*"do not approve"* $\rightarrow$ *"approve"*) or alter sensitive numbers. | **FactGuard Protection:** Deterministic auditing guarantees numbers, dates, negations, and commitments are preserved with mathematical precision. |
| **System Sluggishness** | Electron-based dictation utilities swallow 600MB+ RAM and hijack window focus from your code editor or document. | **Native Win32 Lightweight:** Consumes just ~127 MB RAM and utilizes `WS_EX_NOACTIVATE` to never steal your focus. |

---

## [CORE CAPABILITIES]

### 1. Spoken Self-Correction (Natural Speech Polish)
Don't reach for backspace. If you stumble or change your mind mid-sentence (*"Schedule for Monday — actually, Wednesday at 2 PM"*), FlowPilot automatically detects the correction, cleans filler words, and delivers crisp, polished writing.

### 2. FactGuard™ Meaning Preservation
AI rewriting should enhance clarity, never distort facts. FactGuard rigorously audits every utterance:
- **Numbers & Currencies:** `$12,500` is never rounded or omitted.
- **Dates & Deadlines:** Kept strictly intact.
- **Critical Negations:** Words like `not`, `never`, `cannot`, `without`, and `neither` are protected from AI erasure.

### 3. Developer & Technical Casing
FlowPilot speaks your language. Say *"create camel case user profile and snake case get account balance"*, and watch your document receive `userProfile` and `get_account_balance` directly.

### 4. Background Audio Ducking
Listening to music, podcasts, or a video call? Pressing your dictation hotkey automatically quiets background media and restores it the exact instant you finish speaking.

### 5. Non-Destructive Clipboard & Emergency Recovery
FlowPilot temporarily uses the system clipboard to inject text in ~300ms, then seamlessly restores your pre-existing clipboard contents. Dictating never overwrites your copied secrets. And if a target window closes, right-click the tray to **"Copy Last Dictation"** instantly from memory.

---

## [HEAD-TO-HEAD COMPARISON]

| Capability | FlowPilot 2.0 | Wispr Flow | Dragon Professional |
|:---|:---:|:---:|:---:|
| **Processing Architecture** | **100% Local Device** | Cloud Streaming | Hybrid Server |
| **Outbound Data Sockets** | **0 (Air-Gapped)** | Constant WAN TLS | Periodic Cloud Sync |
| **Writing Polish Latency** | **1–3 ms** | 800–2,500 ms | N/A (Rule formatting) |
| **RAM Consumption** | **~127 MB** | 450–850 MB | 1,200 MB+ |
| **Focus-Safe Floating HUD** | **Yes (`WS_EX_NOACTIVATE`)** | Intermittent focus theft | Heavy toolbar |
| **Fact & Negation Protection** | **FactGuard™ Guaranteed** | LLM Hallucination Risk | Rule-based grammar |
| **Subscription Cost** | **$0 / Perpetual** | $144–$180 / year | $500+ Perpetual |

---

## [SECURITY & COMPLIANCE ARCHITECTURE]

### Built for Regulated Workplaces

- **HIPAA-Eligible Architecture:** Complete local-first execution eliminates Business Associate Agreement (BAA) cloud exposure. Patient identifiers never traverse external networks.
- **GDPR Privacy-by-Design Alignment:** Voice data is ephemeral in local RAM and discarded upon transcription. Zero cross-border data transfer.
- **Air-Gapped Ready:** Operates seamlessly on secure defense networks (SCIFs), flight cockpits, and offshore environments with zero internet access.

---

## [TECHNICAL SPECIFICATIONS]

- **Supported Platforms:** Windows 10 (1903+) & Windows 11 (64-bit)
- **Hardware Requirements:** x86_64 CPU with AVX2 (Intel Core 4th Gen+ / AMD Ryzen), 4GB RAM minimum (8GB recommended)
- **Acoustic Engine:** faster-whisper CTranslate2 (INT8 CPU Quantization)
- **Default Shortcuts:** `Ctrl + Shift + Space` (Toggle), `F9` (Push-to-Talk), `Ctrl + Alt + Space` (Secondary)
- **Distribution:** Standalone Portable Directory (No installer or registry modifications required)

---

## [FREQUENTLY ASKED QUESTIONS]

**Q: Do I need an internet connection to use FlowPilot?**  
*A:* No. FlowPilot executes speech-to-text inference and writing intelligence completely on your local CPU. Once model weights are cached, it never attempts to connect to the internet.

**Q: Will FlowPilot overwrite text I've already copied to my clipboard?**  
*A:* No. FlowPilot preserves your pre-existing clipboard data in memory, performs the text insertion, and restores your original clipboard contents within 1.5 seconds.

**Q: Can I use FlowPilot alongside Wispr Flow?**  
*A:* Yes! Wispr Flow uses `Ctrl + Win`, while FlowPilot defaults to `Ctrl + Shift + Space` and `F9`. They can run simultaneously on the same machine without hotkey collisions.

---

## [DOWNLOAD & GET STARTED]

Ready to accelerate your writing without compromising privacy?

[ **Download FlowPilot v2.0.0 (Windows 64-bit Portable .ZIP)** ]  
*(Size: ~248 MB • SHA-256 Verified)*
