# FlowPilot Security Policy

## Supported Versions

| Version | Supported | Security Maintenance |
|:---|:---:|:---|
| 3.0.x | :white_check_mark: | Active (Release Hardened) |
| 2.1.x | :x: | Deprecated |
| 2.0.x | :x: | Deprecated |

---

## Security Architecture & Design Guarantees

FlowPilot is designed with a defense-in-depth posture appropriate for desktop voice input tools:

### 1. Zero Network Egress
- Local execution by default: all speech models (`faster-whisper`, `silero-vad`) execute purely on local CPU execution providers via CTranslate2 and ONNX Runtime.
- The [network egress regression test](tests/test_network_egress.py) blocks attempted non-loopback connections in selected code paths. It is not continuous runtime monitoring or an independent certification.

### 2. Process Isolation & Win32 APIs
- FlowPilot runs as a standard medium-integrity desktop process. It does not require elevated administrator privileges for normal operation.
- Global shortcuts are registered using the standard Win32 `RegisterHotKey` API, avoiding intrusive low-level global keyboard hooks (`WH_KEYBOARD_LL`) that could interfere with password managers or trigger security alerts.
- Single-instance enforcement uses a local Win32 Named Mutex (`Global\FlowPilot_Desktop_SingleInstance_Mutex`) to eliminate race conditions and unauthorized secondary process injection.

### 3. Non-Destructive Clipboard Management
- When injecting text via the Windows clipboard (`Ctrl+V`), FlowPilot backs up the user's prior clipboard format and restores it immediately following paste verification, preventing accidental clipboard data loss.

---

## Reporting a Vulnerability

If you discover a security vulnerability within FlowPilot:

1. **Do not open a public GitHub issue.**
2. Report the vulnerability privately via [GitHub's private vulnerability reporting](https://github.com/abishekvr0910/flowpilot/security/advisories/new), if enabled for this repository. If unavailable, contact a maintainer through a previously verified private channel; do not publish exploit details in an issue.
3. Include detailed steps to reproduce the issue, environment details (Windows version, Python version), and any proof-of-concept material.

The maintainer will triage private reports as capacity permits. No contractual response-time guarantee is offered.
