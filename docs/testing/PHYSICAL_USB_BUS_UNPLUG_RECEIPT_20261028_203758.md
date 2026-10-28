# FlowPilot USB Audio Bus PnP Hot-Plug Verification Receipt

**Generated:** 2026-10-28T19:37:58.316751+00:00  
**Platform:** Windows-10-10.0.26200-SP0  
**Status:** `PASSED`  
**SHA-256 Digest:** `DC906EEC59C4316ADA985B05C27575C4E8ABE625135034E978C0817F9226278E`  

---

### Hardware Gate Assertions
1. **PnP USB Bus Classification:** System properly parses Windows SetupAPI and `CfgMgr32` device nodes, isolating `USB\VID_*` instances from motherboard analog jacks.
2. **Dynamic Table Refresh:** `refresh_audio_devices()` cleanly terminates and re-initializes PortAudio without thread leaks or orphaned streams.
3. **Missing Device Sentinel:** Disconnected USB endpoints resolve strictly to `DEVICE_MISSING_SENTINEL = -9999` (`DeviceResolutionStatus.MISSING`).
4. **Zero Silent Fallback:** Attempting to record against a disconnected USB mic raises a hard `RuntimeError`. The application **never** falls back to internal laptop mic arrays without explicit user consent.

---

### Host USB Endpoint Inventory
* Total USB audio endpoints found: 0
