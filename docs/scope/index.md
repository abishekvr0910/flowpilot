# FlowPilot Scope and Roadmap

Current status and boundaries for the FlowPilot desktop dictation and writing project.

## At a glance

FlowPilot is a Windows-first, 100% offline dictation and private writing tool. For the whole-product specification and verification standard across all 13 core subsystems, see the [Whole-Product Master Scope](FLOWPILOT_WHOLE_PRODUCT_MASTER_SCOPE.md). For the commercial General Availability (GA) closure roadmap, see the [GA Final Closure Scope](FLOWPILOT_GA_FINAL_CLOSURE_SCOPE.md). The current source version is **3.2.2**; the latest published application download checked on 2026-11-14 is **v3.1.3**, unsigned. [Current status and handoff](../STATUS.md) is the authority for current completion and next steps. See the [release manifest](../release/RELEASE_ARTIFACT_MANIFEST.md) for artifact hashes, test evidence, and open gates.

| ID | Capability or milestone | Area | Status |
|---|---|---|---|
| 01 | Dictate into normal Windows applications | Foundation | existing |
| 02 | Keyboard focus safety (no focus stealing) | Foundation | existing |
| 03 | Verified text insertion via Win32 and UI Automation | Foundation | existing |
| 04 | Windows audio ducking and restore | Foundation | existing |
| 05 | Global hotkey with Win32 message pump | Foundation | existing |
| 06 | Dual Whisper models: base and small | Foundation | existing |
| 07 | Silero VAD voice activity detection | Foundation | existing |
| 08 | FactGuard critical fact and negation preservation | Foundation | existing |
| 09 | Spoken self correction resolution | Foundation | existing |
| 10 | Native companions and creator | Foundation | existing |
| 11 | Optional local API | Foundation | existing |
| 12 | Local storage and privacy controls | Foundation | existing |
| 13 | Windows RC8 pilot candidate | Foundation | existing |
| 26 | External transform safety repair | Next release | done |
| 28 | Persistent microphone selection | Next release | done (3.5mm & USB bus hot-plug verified) |
| 29 | Competitive outcome evaluation | Next release | in-progress |
| 32 | Pilot reliability hardening | Next release | in-progress |
| 14 | Consented Windows pilot | Next release | planned |
| 15 | Real speaker language evaluation | Next release | planned |
| 16 | Real application paste reliability | Next release | planned |
| 25 | Runtime latency and resource evaluation | Next release | in-progress |
| 17 | Distribution size and publisher identity | Next release | partial (installer and signing tools implemented; published artifacts unsigned) |
| 18 | Trust, security, and public claims review | Next release | planned |
| 19 | Whole app usability and visual quality | Product quality | planned |
| 20 | Context aware companion visibility | Product quality | in-progress |
| 27 | Media audio aware hiding | Product quality | in-progress |
| 21 | Original character quality and rights | Product quality | planned |
| 22 | Safe editing beyond the scratchpad | Product quality | blocked (external rewrite/undo disabled pending verified revision adapter) |
| 30 | Optional local text repair and infilling | Product quality | implemented, opt-in sandbox; broader validation pending |
| 31 | Approved local correction learning | Product quality | done |
| 23 | Optional editor presence | Later | planned |
| 24 | Windowed media and screen share behavior | Later | closed (manual app rules) |

## Areas

- [Voice and writing](voice.md): existing foundations, the external transform repair, and language, delivery, performance, and editing work.
- [Workspace](workspace.md): 3 existing work areas and one whole app usability step.
- [Companions](companions.md): the native pet, the next visibility slice, original character polish, and later context work.
- [Release and trust](release.md): privacy and local API boundaries, the RC8 pilot prerelease, and the evidence needed before general release.
- [Competitive validation](competitive.md): a fair comparison of useful text, delivery, correction effort, and user preference.

## Order and boundaries

The current source, RC8, and RC9 refuse unsupported external Replace and Revert operations. Older candidates do not acquire later repairs from source edits. Persistent microphone identity, independent delivery observation, pilot capture guards, and terminal delivery hardening are present in source. Candidate hardware behavior and physical 3.5mm Realtek WASAPI hot-plug unplug/reconnect have been verified via `scripts/verify_audio_device_gate.py` and `scripts/interactive_physical_mic_test.py` ([physical integrity receipt](../testing/PHYSICAL_USB_UNPLUG_RECEIPT_20261027_000556.md)), and dedicated USB bus audio device (`USB\VID_...`) hot-plug confirmation has been verified and logged via `scripts/verify_usb_bus_hotplug.py` ([physical USB bus receipt](../testing/PHYSICAL_USB_BUS_UNPLUG_RECEIPT_20261028_203758.md)); broad first-attempt paste reliability across heavy applications, diverse human speech, and paired competitor outcomes remain active evaluation tracks. Universal repetition loop suppression has resolved Indic and multilingual looping without hallucinatory padding. Inno Setup packaging and an RFC 3161 signing pipeline are implemented. Published v3.1.3 packages remain unsigned; signing tooling does not close the publisher identity gate. Feature 30 exists in source behind an opt-in setting; it is not enabled by default. Define build identity, thresholds, and failure reporting before new trials. Product quality work can proceed separately without relabelling older release evidence.

The initial competitive objective is better private developer dictation on Windows, measured as less time to correct, usable text without worse factual errors or unsafe delivery. General release readiness and competitive superiority are separate decisions. A result on one language, model, or machine does not establish universal superiority. The historical execution sequence is in the [Gemini handoff](GEMINI_SCOPE_EXECUTION_HANDOFF_2026-10-26.md), superseded for current status by [the current handoff](../STATUS.md); no claim of being "100% better" is authorized by a suite count or this scope.

FlowPilot stays local first. The normal desktop path does not depend on a cloud model. Optional localhost integrations have their own trust boundary. A green automated suite is not proof of universal paste reliability, zero risk, regulatory compliance, or superiority over Wispr Flow. Character art and interface work must be original or properly licensed. We are not planning a competitor code clone.

Mobile apps, broad Linux and macOS release support, automatic actions in arbitrary applications, and automatic recognition of every windowed video are outside the current release scope. They can be revisited after the Windows journey works reliably for pilot users.


## Legend

`existing` means implemented, not fully validated on customer hardware. `candidate-verified` means verified on the recorded hardware and artifact only. `planned` means not complete. `needs a decision` means behavior and tests still need an agreed design. Follow the priorities in [current status](../STATUS.md); historical checklists may refer to older candidates.
