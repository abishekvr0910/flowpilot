# Physical Audio Endpoint Hot-Plug (3.5mm Realtek WASAPI) Cryptographic Integrity Receipt

**Verification Mode:** `PHYSICAL`
**Receipt Classification:** `Cryptographic Integrity Receipt (SHA-256 Digest, Non-Signed)`
**Execution Timestamp:** `2026-10-26T23:05:56.249760+00:00`
**Host Machine:** `LAPTOP-5KASE5RO` (Windows 10)
**Target Device Name:** `Microphone (Realtek(R) Audio)`
**Host API:** `Windows WASAPI`
**Hardware Bus Class:** `analog_jack_hd_audio_endpoint` (`is_usb_bus_device=False`; Realtek ALC287 HD Audio jack-sensed MMDevice `SWD\MMDEVAPI\{0.0.1.00000000}.{0512B5B8-8E0F-40A7-A89E-6041F681608D}` on `INTELAUDIO\FUNC_01&VEN_10EC&DEV_0287&SUBSYS_1025159C`)
**Canonical Manifest SHA-256 Integrity Digest:** `080F72FBF841FD6CF75513854B6DADDA295AC12986A08933B90F3E493A899890`

> **Integrity & Hardware Scope Note:** This receipt provides a tamper-evident SHA-256 cryptographic digest over the captured PCM audio buffers and canonical test manifest (it is an integrity receipt, not an asymmetric private-key digital signature). The physical device tested here is a 3.5mm analog headphone/headset connected to the Realtek HD Audio jack-sense WASAPI endpoint (`is_usb_bus_device=False`), not a USB PnP bus audio device (`USB\VID_...`). Physical USB bus audio device unplug/reconnect remains a separate pilot hardware test item.

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
  "hardware_bus": {
    "codec_pnp_instance_id": "INTELAUDIO\\FUNC_01&VEN_10EC&DEV_0287&SUBSYS_1025159C",
    "hardware_bus_class": "analog_jack_hd_audio_endpoint",
    "is_usb_bus_device": false,
    "mmdevice_endpoint_id": "SWD\\MMDEVAPI\\{0.0.1.00000000}.{0512B5B8-8E0F-40A7-A89E-6041F681608D}"
  },
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
`080F72FBF841FD6CF75513854B6DADDA295AC12986A08933B90F3E493A899890`

---

## 3. Compliance Affirmation

- **Zero Silent Fallback:** Verified. Capture was refused with `RuntimeError` while the designated endpoint was detached.
- **Bounded Cleanup:** Verified. The unresponsive stream discarded partial audio and released without blocking caller threads or leaking OS handles.
- **Persistent Identity:** Verified. PortAudio re-enumeration restored the hardware endpoint by name and host API contract.
- **Hardware Bus Boundary:** Verified on physical 3.5mm Realtek HD Audio WASAPI jack-sense hardware (`analog_jack_hd_audio_endpoint`, `is_usb_bus_device=False`). External USB bus audio (`USB\VID_...`) hot-plug verification remains scheduled for USB hardware pilot intake.

**Overall Verdict:** **PHYSICAL AUDIO ENDPOINT HOT-PLUG GATE PASSED (3.5MM REALTEK WASAPI)**
