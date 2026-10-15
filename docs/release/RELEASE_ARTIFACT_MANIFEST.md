# FlowPilot Release Artifact Manifest & Source of Truth

**Document Version:** 1.0.0  
**Last Updated:** 2026-10-15  
**Maintainer:** FlowPilot Core Engineering & Release Team  

This document serves as the authoritative, tamper-evident record of all FlowPilot releases, candidate artifacts, source commits, cryptographic hashes, and rollback baselines.

---

## 1. Stable Baseline (Official Rollback Target)

The official stable release is **FlowPilot v3.0.2**, tagged and published on GitHub. This baseline remains strictly immutable and protected against overwriting.

| Attribute | Baseline Specification |
| :--- | :--- |
| **Release Tag** | [`v3.0.2-release`](https://github.com/abishekvr0910/flowpilot/releases/tag/v3.0.2-release) |
| **Tagged Git Commit** | `b9bd76396b2883fa2e87e8b131d231dc39c34515` (`b9bd763`) |
| **Master Branch Commit** | `ba5c93e1183edf1d89db7688fe1e8041ba228a13` (`ba5c93e` - 1 documentation audit commit ahead of release tag) |
| **Official Archive** | `dist/FlowPilot-v3.0.2-win64.zip` |
| **Archive File Size** | 252,311,634 bytes (~240.6 MiB) |
| **SHA-256 Checksum** | `985E031C7AF2617E4C03138D1A00472607FF9F9E1D2CFF636827F26077F63F74` |
| **Unpacked Backup Dir** | `dist/FlowPilot_backup_v302/` (875 MB on disk, verified intact) |
| **GitHub Asset URL** | `https://github.com/abishekvr0910/flowpilot/releases/download/v3.0.2-release/FlowPilot-v3.0.2-win64.zip` |
| **Publication State** | Published & Immutable on GitHub |

---

## 2. Active Development & Controlled Pilot Candidates

Development occurs on an isolated local feature branch (`feature/developer-reliability-upgrade`). In accordance with change control rules, this branch is not pushed to `origin` and has not been merged into `master`.

### Pilot Candidate Inventory

| Version / Revision | Source Commit | File Path | File Size (Bytes) | SHA-256 Checksum | Status / Notes |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **v3.1.0-pilot (Rev 1)** | `00e34d3f59` | `dist/FlowPilot-v3.1.0-pilot-win64.zip` | 251,173,567 | `4FD81150A5E404AB64C52B0C03BACB454D59DF6911BF0E23D3EABC363ED1B6FE` | Superseded; quarantined due to unverified injection contract. Preserved for provenance. |
| **v3.1.0-pilot-r2 (Candidate)** | `feature/developer-reliability-upgrade` | `dist/FlowPilot-v3.1.0-pilot-r2-win64.zip` | 251,185,211 | `F2DAB2CC995257A74602343AFDA993465D118E4CC09EB1509D3F8B1E2F2E27F4` | Fully hardened pilot candidate. Physical injection confirmation verified in Notepad (18/18 E2E scenarios PASS, 24/24 regressions PASS, zero egress confirmed, npm private). |

---

## 3. Historical Release Tag Baseline

| Release Tag | Tag Ref (Annotated / Lightweight) | Target Commit | Published GitHub Release? |
| :--- | :--- | :--- | :---: |
| `v2.0.0-release` | `83744efe48` | `02c1241aa9` | No (Git tag only) |
| `v2.1.0-release` | `8c770abca0` | `c0c7411d4a` | No (Git tag only) |
| `v3.0.0-release` | `ce136e2094` | `ec118d2371` | No (Git tag only) |
| `v3.0.1-release` | `93cff43eb8` | `5fd8e2fb64` | No (Git tag only) |
| `v3.0.2-release` | `b9bd76396b` | `b9bd76396b` | **Yes (Official GitHub Release)** |

---

## 4. Host Build & Execution Environment

- **Operating System:** Microsoft Windows 11 Pro / Enterprise (x64)
- **Python Version:** 3.11.15 / 3.12 compatible (Virtual environment: `hermes-agent`)
- **Node.js Version:** `v24.15.0`
- **npm Version:** `11.12.1`
- **PyInstaller Version:** 6.13.0
- **Audio Subsystem:** WASAPI / CoreAudio via `sounddevice` 0.5.1 and `pycaw` 20240210
- **Speech Engine:** `faster-whisper` 1.1.1 on CPU INT8 (CTranslate2 4.5.0)
- **VAD Subsystem:** Silero VAD v5 ONNX (`silero_encoder_v5.onnx`, `silero_decoder_v5.onnx`)
