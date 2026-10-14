# FlowPilot ⚡
> **Next-Generation Universal Multilingual Voice Intelligence**  
> A privacy-first, zero-censorship alternative to Wispr Flow designed for power users and developers.

---

## 🌟 Why FlowPilot? (Fixing Wispr Flow's Flaws)

| Problem in Wispr Flow | How FlowPilot Solves It |
|---|---|
| **Privacy Intrusion:** Captures screenshots of your screen and sends them to the cloud. | **100% Privacy Compliant:** Zero screenshots. Inspects only the active executable (`code.exe`, `slack.exe`) locally via Win32 APIs. |
| **Technical Jargon Butchered:** Misses acronyms (*"AWS Lambda logs"* -> *"Alice's lamb belongs"*). | **Developer Glossary Biasing:** Injects your project terms (`Kubernetes`, `GraphQL`, `Pydantic`) directly into Whisper's prompt decoder. |
| **Windows Overhead & Freezing:** Heavy Electron client causing CPU spikes and editor hangs. | **Lightweight Native Core:** Built in Python + Win32 hooks with low RAM and zero application freezing. |
| **Cloud-Only & Subscriptions:** $15/month with no offline option. | **Hybrid Freedom:** 100% Offline Local Model (`faster-whisper`) OR Ultra-Fast Cloud BYOK (Groq @ ~300ms latency). |
| **Censorship & Pausing Penalties:** Bowdlerizes profanities and rewrites sentences when you pause. | **Granular Tone Dials:** `Verbatim` (0% AI rewrites), `Developer` (code formatting), `Casual` (uncensored), and `Cleaned`. |
| **Pasting Glitches:** Fails to paste or overwrites clipboard data. | **Safe Win32 Injection:** Locks active window focus, verifies paste, and automatically restores your original clipboard! |
| **Multilingual Limitations:** Locks to 1 language per dictation block. | **Polyglot Code-Switching:** 100+ languages with seamless mid-sentence bilingual dictation. |

---

## 🚀 Quick Start

### 1. Launch FlowPilot
Run the main script:
```powershell
python run.py
```
This will start the engine server on `http://127.0.0.1:8765` and automatically open your dashboard.

### 2. How to Dictate Anywhere
1. Click into any application (VS Code, Slack, Chrome, Word, Notepad, etc.).
2. Press **`Ctrl + Shift + Space`** to start dictating.
3. Speak naturally in any language (or mix languages).
4. Press **`Ctrl + Shift + Space`** again to finish.
5. Watch FlowPilot clean, format, and paste the text directly at your cursor!

---

## 🛠️ Configuration & Settings

Open `http://127.0.0.1:8765` in your browser to access the control center:
* **Tone Modes:** Toggle between `Developer`, `Cleaned`, `Verbatim`, `Casual`, and `Email`.
* **Engine:** Switch between **Ultra-Fast Cloud** (Groq Whisper-large-v3) and **100% Offline** (Local `faster-whisper`).
* **Custom Glossary:** Add your company or project-specific keywords with one click.
* **Languages:** Choose primary language or leave on `Auto-Detect`, with polyglot code-switching enabled.
* **History:** Browse, search, and copy previous dictations.
