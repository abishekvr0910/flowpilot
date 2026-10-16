import sys
import subprocess
import time
from pathlib import Path

TESTS = [
    ("Microphone & Audio Capture", "tests/test_audio.py"),
    ("Local Whisper Speech-to-Text Model", "tests/test_stt.py"),
    ("Text Injection & Clipboard Safety", "tests/test_text_injector.py"),
    ("Windows Audio Ducking & Error Recovery", "tests/test_audio_ducker.py"),
    ("UI REST API & WebSocket Protocol", "tests/test_api_and_websocket.py"),
    ("Global Hotkey Resolution & Normalization", "tests/test_hotkey.py"),
    ("Win32 RegisterHotKey & Message Loop", "tests/test_win32_hotkey.py"),
    ("Native PySide6 Desktop HUD & Tray Lifecycle", "tests/test_desktop_app.py"),
    ("Multilingual Language Registry", "tests/test_language_registry.py"),
    ("Writing Intelligence & FactGuard", "tests/test_writing_intelligence.py"),
    ("FactGuard Adversarial Guardrails", "tests/test_factguard_adversarial.py"),
    ("Forensic Zero Network Egress", "tests/test_network_egress.py"),
    ("Multilingual Script Validation", "tests/test_multilingual_validation.py"),
    ("Multilingual Acoustic Reality Assessment", "tests/test_multilingual_speech_reality.py"),
    ("Personalization & Voice Snippets", "tests/test_personalization.py"),
    ("Settings Dialog & Hotkey Conflict Inspector", "tests/test_settings_dialog.py"),
    ("Extended Speech Model Benchmarks", "tests/test_model_benchmarks_extended.py"),
    ("Orchestrator 9-State Machine & Robustness", "tests/test_orchestrator_state_machine.py"),
    ("Dictation Session Lifecycle & Ownership", "tests/test_session_lifecycle.py"),
    ("FactGuard v2 Conservative Entity Guard", "tests/test_factguard_v2.py"),
    ("Application Profiles & Precedence", "tests/test_application_profiles.py"),
    ("Voice Snippets Hardening & Literal Safety", "tests/test_personalization_snippets.py"),
    ("Silero VAD ONNX Asset Resolution", "tests/test_silero_vad_resolution.py"),
    ("End-to-End 5-Cycle Notepad Dictation", "tests/test_notepad_dictation_e2e.py"),
    ("Dissected Competitive Upgrades", "tests/test_dissected_upgrades.py"),
    ("Cross-Platform Linux & macOS Adapters", "tests/test_cross_platform.py"),
    ("SondeR-Cat Pixel Kitty Companion", "tests/test_sondercat_companion.py"),
    ("Cross-Application Injection & Focus", "tests/test_cross_app_injection.py"),
    ("18-Scenario Full Specification End-to-End", "tests/test_final_specification_e2e.py"),
    ("Standalone Windows Binary Packaging Smoke", "tests/test_standalone_binary_smoke.py"),
]

def ensure_desktop_accessible():
    # Non-destructive desktop access verification (do not kill system processes like LockApp)
    pass

def run_suite():
    print("=" * 70)
    print("           FLOWPILOT AUTOMATED AUDIT SUITE EXECUTION")
    print("=" * 70)
    results = []
    start_total = time.time()

    for name, script in TESTS:
        ensure_desktop_accessible()
        print(f"\n--- Running: {name} ({script}) ---")
        t0 = time.time()
        res = subprocess.run([sys.executable, script], capture_output=True, encoding="utf-8", errors="replace")
        dur = time.time() - t0
        passed = (res.returncode == 0)
        results.append((name, passed, dur, res.stdout, res.stderr))
        status_str = "PASSED" if passed else "FAILED"
        print(f"Status: {status_str} ({dur:.2f}s)")
        if not passed:
            print("STDOUT:\n", res.stdout)
            print("STDERR:\n", res.stderr)

    total_dur = time.time() - start_total
    print("\n" + "=" * 70)
    print("                    AUDIT SUMMARY RESULTS")
    print("=" * 70)
    all_passed = True
    for name, passed, dur, _, _ in results:
        status_str = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        print(f"{status_str} {name:<45} ({dur:.2f}s)")

    print("-" * 70)
    print(f"Total Test Time: {total_dur:.2f}s | Overall Verdict: {'ALL TESTS PASSED' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
