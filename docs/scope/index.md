# Scope: FlowPilot

FlowPilot is a local voice workstation for Windows users who want to dictate, revise, and recover text without sending their speech to a cloud service. Developers are the first audience. Privacy conscious writers and professionals are a second audience, but regulated use needs its own evidence and review.

**Build approach:** Journey (prove setup, dictation, correction, insertion, recovery, and safe exit on real Windows machines before adding more breadth).
**Workflow:** Beta (verify the real behavior, then test it). Release and security work uses the GA tier.

This is the project scope, not a feature inventory or a promise that every current feature is field proven. `existing` means code is present. A release claim needs separate user and artifact evidence. The public general release is v3.0.2; v3.1.0 RC4 is the current pilot candidate. RC2 and RC3 remain historical.

**Reviewed baseline:** application source at `2710397`, package source at `2baa2f9`, 24 October 2026. The five requested RC3 companion live checks have recorded results. RC4 adds persistent microphone identity, a separate delivery observer, workspace scroll repairs, and a pruned package with copied notices. Hosted CI passed. The exact-candidate interactive gate passed 56/56 on a clean repeat after an initial Notepad focus failure; both outcomes are recorded. These checks do not close every acceptance criterion in spec 0001 or establish a competitive win. The [complete Gemini handoff](../handoffs/GEMINI_PRODUCT_COMPLETION_AND_COMPETITIVE_VALIDATION.md) maps the whole product to evidence, remaining work, delivery order, and proposed comparison gates. Writing that plan does not complete its work.

## At a glance

| # | Feature | Phase | Status |
|---|---|---|---|
| 1 | Offline capture and speech engine | Foundation | existing |
| 2 | Dictation controls and session lifecycle | Foundation | existing |
| 3 | Writing quality and personal vocabulary | Foundation | existing |
| 4 | Text insertion and recovery | Foundation | existing |
| 5 | Multilingual modes and translation | Foundation | existing |
| 6 | Bounded voice commands and editing | Foundation | existing |
| 7 | Setup, settings, and dashboard | Foundation | existing |
| 8 | Scratchpad, history, and insights | Foundation | existing |
| 9 | Meeting notes and deliberation | Foundation | existing |
| 10 | Native companions and creator | Foundation | existing |
| 11 | Optional local API | Foundation | existing |
| 12 | Local storage and privacy controls | Foundation | existing |
| 13 | Windows RC2 candidate | Foundation | existing |
| 26 | External transform safety repair | Next release | done |
| 28 | Persistent microphone selection | Next release | in-progress |
| 29 | Competitive outcome evaluation | Next release | in-progress |
| 32 | Pilot reliability hardening | Next release | in-progress |
| 14 | Consented Windows pilot | Next release | planned |
| 15 | Real speaker language evaluation | Next release | planned |
| 16 | Real application paste reliability | Next release | planned |
| 25 | Runtime latency and resource evaluation | Next release | in-progress |
| 17 | Distribution size and publisher identity | Next release | planned |
| 18 | Trust, security, and public claims review | Next release | planned |
| 19 | Whole app usability and visual quality | Product quality | planned |
| 20 | Context aware companion visibility | Product quality | in-progress |
| 27 | Media audio aware hiding | Product quality | in-progress |
| 21 | Original character quality and rights | Product quality | planned |
| 22 | Safe editing beyond the scratchpad | Product quality | planned |
| 30 | Optional local writing context | Product quality | planned |
| 31 | Approved local correction learning | Product quality | planned |
| 23 | Optional editor presence | Later | planned |
| 24 | Windowed media and screen share behavior | Later | closed (manual app rules) |

## Areas

- [Voice and writing](voice.md): existing foundations, the external transform repair, and language, delivery, performance, and editing work.
- [Workspace](workspace.md): 3 existing work areas and one whole app usability step.
- [Companions](companions.md): the native pet, the next visibility slice, original character polish, and later context work.
- [Release and trust](release.md): privacy and local API boundaries, the RC4 candidate, and the evidence needed before general release.
- [Competitive validation](competitive.md): a fair comparison of useful text, delivery, correction effort, and user preference.

## Order and boundaries

The current source and RC4 candidate refuse unsupported external Replace and Revert operations. RC2 and RC3 do not acquire later repairs from source edits. The persistent microphone and independent delivery observer implementations are now present, with focused tests and a strict interactive gate. Feature 32 is development work on a separate branch; its bounded microphone handling, integrity check, local metrics rotation, and Indic model guidance are not in RC4. Physical microphone disconnect and reconnect behavior still needs validation on a new candidate. Next close the remaining spec 0001 live rows, collect real voice, real paste, and runtime evidence for the consented pilot (feature 14), and run paired competitive trials. Define build identity, thresholds, and failure reporting before trials. Product quality work can proceed separately without relabelling older release evidence.

The initial competitive objective is better private developer dictation on Windows, measured as less time to correct, usable text without worse factual errors or unsafe delivery. General release readiness and competitive superiority are separate decisions. A result on one language, model, or machine does not establish universal superiority. The full completion gates and proposed numerical targets are in the Gemini handoff; no claim of being "100% better" is authorized by a suite count or this scope.

FlowPilot stays local first. The normal desktop path does not depend on a cloud model. Optional localhost integrations have their own trust boundary. A green automated suite is not proof of universal paste reliability, zero risk, regulatory compliance, or superiority over Wispr Flow. Character art and interface work must be original or properly licensed. We are not planning a competitor code clone.

Mobile apps, broad Linux and macOS release support, automatic actions in arbitrary applications, and automatic recognition of every windowed video are outside the current release scope. They can be revisited after the Windows journey works reliably for pilot users.

## Legend

`existing` means implemented before this scope, not fully validated on customer hardware. `planned` means not complete. `needs a decision` means you may ask `/architect` to settle behavior and tests before building. The first unticked box in a feature section is the suggested next step. This scope can be reconciled after each real milestone without treating a proposed spec as shipped code.
