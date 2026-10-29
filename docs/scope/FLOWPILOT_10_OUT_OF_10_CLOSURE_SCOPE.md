# FlowPilot: 10/10 General Availability (GA) Execution Scope

**Document Version:** 3.3.0-GA-TEN-OUT-OF-TEN-SPEC  
**Status:** In Progress / Active Execution  
**Target Architecture:** Windows 10/11 x64 Native  
**Target Release:** FlowPilot v3.1.0-RC12 / v3.1.0-GA  

---

## 1. Objective

Elevate FlowPilot from its current **8.8 / 10** maturity to a **10 / 10 Commercial Production Quality Standard** by closing the three remaining distribution and packaging gaps identified in the architectural audit:

1. **One-Click Native Windows Installer (`FlowPilot-Setup-v3.1.0.exe`)**:
   - Provision Inno Setup 6 compiler (`ISCC.exe`) on the host device via `winget`.
   - Compile `installer/flowpilot_setup.iss` with LZMA2 ultra compression.
   - Verify non-elevated user-local installation in `%localappdata%\Programs\FlowPilot`.
   - Verify Start Menu, optional Desktop shortcut, and startup registry key (`HKCU\...\Run`).
   - Verify active mutex detection (`Global\FlowPilot_Desktop_SingleInstance_Mutex`).

2. **Master Binary Rebuild & Verification**:
   - Rebuild standalone PyInstaller frozen binary bundle from current `master` HEAD (`35ac93b`) containing:
     - Universal Selection Rewriter (`Ctrl+Alt+T`) & Rollback Latch (`Alt+Shift+U`).
     - Universal Phrase Repetition Loop Suppression (`(?u)(?:^|\s)(.{3,35}?)(?:\s+\1){2,}(?=\s|$)`).
     - USB Audio Bus Hot-Plug Harness (`USB\VID_...` sentinel guard).
     - Idle Memory Unloader (1.5 GB -> <100 MB RAM).
     - Caret-Aware Context Formatting & Live Replacement Detector.

3. **Authenticode Signing Pipeline Validation**:
   - Validate `scripts/sign_authenticode.py` against both test self-signed certificates and Azure Trusted Signing specifications.
   - Ensure binary integrity and SHA-256 digests remain valid post-signature.

4. **Full 60-Suite Audit & Speech Self-Test Gate**:
   - Pass offline speech recognition self-test (`FlowPilot.exe --self-test`) via SAPI.
   - Run full 60-suite audit runner (`tests/run_all_tests.py`), verifying 55 passing, 5 skips, 0 failures.

5. **GitHub Release Promotion & Distribution Assets**:
   - Generate release checksum manifests (`.sha256`).
   - Publish `FlowPilot-Setup-v3.1.0.exe` alongside the standalone ZIP archive on GitHub Releases under tag `v3.1.0-RC12` / `v3.1.0`.

---

## 2. Work Breakdown Structure (WBS)

1. Provision Inno Setup 6 via `winget`
2. Rebuild PyInstaller Frozen Bundle from `master` HEAD
3. Verify Offline Speech Self-Test (`FlowPilot.exe --self-test`)
4. Compile Inno Setup Installer (`FlowPilot-Setup-v3.1.0.exe`)
5. Validate Installer Execution & Mutex Guard
6. Run Full 60-Suite Audit Suite
7. Package Release Archive & Generate SHA-256 Manifest
8. Publish Release Assets to GitHub
