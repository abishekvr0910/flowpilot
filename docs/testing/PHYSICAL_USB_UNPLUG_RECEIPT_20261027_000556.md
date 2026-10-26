# Audio Hardware Disconnect & Reconnect Cryptographic Integrity Receipt

**Verification Mode:** `PHYSICAL`
**Receipt Classification:** `Cryptographic Integrity Receipt (SHA-256 Digest, Non-Signed)`
**Execution Timestamp:** `2026-10-26T23:05:56.249760+00:00`
**Host Machine:** `LAPTOP-5KASE5RO` (Windows 10)
**Target Device Name:** `Microphone (Realtek(R) Audio)`
**Host API:** `Windows WASAPI`
**Canonical Manifest SHA-256 Integrity Digest:** `F7F73918189FEB374AB1CFA05CFF1B5124E6AD26843370B493D724425B1998F1`

> **Integrity Note:** This receipt provides a tamper-evident SHA-256 cryptographic digest over the captured PCM audio buffers and canonical test manifest. It is an integrity receipt, not an asymmetric private-key digital signature.

---

## 1. Measured Evidence & SLAs

| Phase | Evaluation Parameter | Measured Value | Official SLA | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | Pre-flight baseline capture | 63724 bytes | > 0 bytes | **PASSED** |
| **Phase 2a** | Recorder stall trigger threshold | 2.0 s | `CAPTURE_STALL_SECONDS = 2.0 s` | **CONFIGURED** |
| **Phase 2b** | Post-threshold detection overhead | 0.015 s | <= 0.5 s | **PASSED** |
| **Phase 2c** | Total packet-stall-to-detection | 2.015 s | <= 2.5 s (2.0s + 0.5s) | **PASSED** |
| **Phase 3** | Zero silent fallback refusal | Hard RuntimeError (`-9999`) | No silent default mic hijack | **PASSED** |
| **Phase 4** | Physical endpoint reconnect | Re-resolved in 12.585 s | Auto-detected <= 45.0 s | **PASSED** |
| **Phase 5** | Recovery dictation stream | 63724 bytes | Clean stream, 0 health errors | **PASSED** |

---

## 2. Canonical Manifest & SHA-256 Integrity Digest

```json
{
  "execution_mode": "PHYSICAL",
  "hardware_indices": {
    "initial_index": 25,
    "reconnected_index": 25
  },
  "host": {
    "node": "LAPTOP-5KASE5RO",
    "python": "3.11.15",
    "release": "10",
    "system": "Windows"
  },
  "metrics": {
    "disconnect_detection_sla_seconds": 2.5,
    "packet_stall_to_detection_seconds": 2.015,
    "post_threshold_detection_overhead_seconds": 0.015,
    "pre_flight_bytes": 63724,
    "pre_flight_wav_sha256": "EEBC200B66FB960255E44C50DDC6049A1FF69A1A49FCCCDBC708810403F9C59D",
    "reconnect_latency_seconds": 12.585,
    "recorder_stall_threshold_seconds": 2.0,
    "recovery_bytes": 63724,
    "recovery_wav_sha256": "CC78B6447AE3BBFD37A7E0AC1A20FC24D2580C56E92EAC4CC682A4A0641F6F7E",
    "sla_satisfied": true,
    "zero_silent_fallback_enforced": true
  },
  "receipt_type": "cryptographic_integrity_receipt_sha256_unsigned",
  "schema_version": "1.0.0",
  "target_endpoint": {
    "host_api": "Windows WASAPI",
    "max_channels": 2,
    "mode": "endpoint",
    "name": "Microphone (Realtek(R) Audio)"
  },
  "timestamp_iso": "2026-10-26T23:05:56.249760+00:00",
  "verdict": "PASSED"
}
```

**SHA-256 Integrity Digest of Canonical Manifest:**
`F7F73918189FEB374AB1CFA05CFF1B5124E6AD26843370B493D724425B1998F1`

---

## 3. Compliance Affirmation

- **Zero Silent Fallback:** Verified. Capture was refused with `RuntimeError` while the designated endpoint was detached.
- **Bounded Cleanup:** Verified. The unresponsive stream discarded partial audio and released without blocking caller threads or leaking OS handles.
- **Persistent Identity:** Verified. PortAudio re-enumeration restored the hardware endpoint by name and host API contract.

**Overall Verdict:** **PHYSICAL AUDIO HARDWARE GATE PASSED**
