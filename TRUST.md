# Evaluating FlowPilot

FlowPilot is an open-source Windows dictation app with speech recognition on your CPU. This page connects product claims to their implementation, test coverage, and remaining limits so you can decide whether it fits your workflow.

**Scope:** current source and the separately listed build records in the [artifact manifest](docs/release/RELEASE_ARTIFACT_MANIFEST.md). A source commit and a passing local test run do not update an existing download; use the release notes for the exact archive you install.

## What you can check

| Question | Current source behavior | Evidence and limits |
| --- | --- | --- |
| Where is speech recognized? | `faster-whisper` runs on CPU with local model loading. Cloud STT mode is rejected. | [STT engine](engine/stt_engine.py), [network regression](tests/test_network_egress.py). Provision model weights during setup. Tests cover selected execution paths, not every dependency or configuration. |
| Is my dictation saved? | New profiles default to `save_history_text: false`. The completed-dictation persistence path returns without writing vault audio/text, legacy history, insights, or pilot metrics. The latest text remains in memory for recovery. | [Defaults](engine/config.py), [persistence path](engine/orchestrator.py), [history tests](tests/test_transforms_and_history.py). Existing profile choices persist. Meeting notes, scratchpad, settings, logs, and the Windows clipboard have separate lifecycles; see [privacy](PRIVACY.md). |
| What can leave the app? | Dictation is inserted into another application through Windows input/clipboard facilities. Optional text transforms can call a separate loopback model service. | [Injector](engine/text_injector.py), [local model adapter](engine/local_llm.py). The destination application, clipboard tools, and separate model server have their own storage and network behavior. |
| Does local mean access-controlled? | The optional integration server requires a user-provided API token for REST and WebSocket routes and rejects cross-origin browser clients. | [Server](engine/server.py), [security boundaries](SECURITY.md). This is not isolation from a malicious process running as the same Windows user; keep the token private and the listener on loopback. |
| Does text always arrive? | Injection distinguishes confirmed, sent-but-unverified, and failed/recoverable outcomes. | [Injector](engine/text_injector.py), [test protocol](docs/testing/FLOWPILOT_BENCHMARK_PROTOCOL.md). Real editor, privilege, and focus behavior vary. A safe refusal is not a successful paste; a recovery is not first-attempt success. |
| Is it faster or more accurate than Wispr? | No completed paired benchmark establishes that claim in this review. | [Comparison protocol and results status](docs/testing/WISPR_FLOW_HEAD_TO_HEAD.md). Publish corpus, hardware, build identity, sample counts, and failures with future measurements. |
| Can I verify a download? | The published release manifest records an archive hash and source identity. | [Artifact manifest](docs/release/RELEASE_ARTIFACT_MANIFEST.md). A hash checks file identity; it does not prove publisher identity, safety, or source-to-binary equivalence. |

## Current release assurance

The local `dist/FlowPilot/FlowPilot.exe` inspected on October 18 returned `NotSigned` from Windows Authenticode. That observation applies to this local executable, not automatically to the published ZIP. Publisher signing and exact-artifact verification remain release work. Check the downloaded executable's signature using the [release guide](docs/release/flowpilot_build_and_release.md).

This repository does not establish an independent security audit, SOC 2/ISO certification, a contractual support SLA, or a 99.9% insertion guarantee. The security policy describes implemented boundaries and known limitations. The [governance status](docs/security/GITHUB_BRANCH_PROTECTION.md) records which GitHub controls were observed and which are proposed.

## Try it with a small, repeatable check

1. Follow the [Windows quickstart](QUICKSTART.md) using a test phrase without private information.
2. Check your actual history setting; upgrades preserve existing configuration. Verify the behavior of the build you installed.
3. Dictate into a normal Notepad window, then your own editor. Check the inserted text before trying recovery so you can distinguish misses from duplicates.
4. Evaluate offline dictation after the selected model is installed. Report exact build, model, and Windows versions when something fails.

VB-Cable and a TLS proxy are benchmark tools, not prerequisites for normal FlowPilot use.

## How the project earns stronger trust

The next publishable evidence should include an interactive Windows app matrix, exact candidate-artifact checks, third-party notices, and clear download/signature status. Subsequent work should address API rate limits, diagnostic metadata minimization, and supported clipboard formats. Those are tracked as requirements in the [release guide](docs/release/flowpilot_build_and_release.md), not represented here as completed features.

For ordinary problems, use [support](SUPPORT.md). For a suspected vulnerability, use the private route described in [SECURITY.md](SECURITY.md).
