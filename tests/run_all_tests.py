"""Feature 32: Run the complete FlowPilot regression suite with honest skips."""

import sys
import subprocess
import time
import os
import tempfile
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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
    ("Correction Intent & Self-Correction Engine", "tests/test_correction_intent.py"),
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
    ("Companion Studio & Local Learning", "tests/test_companion_studio.py"),
    ("Context Aware Companion Visibility", "tests/test_companion_visibility.py"),
    ("Productivity Insights Engine", "tests/test_insights_engine.py"),
    ("Meeting Notetaker Engine & Extractive Summary", "tests/test_meeting_notetaker.py"),
    ("Meeting Notetaker Streaming & Library v2", "tests/test_meeting_notetaker_v2.py"),
    ("Meeting Deliberation & Intelligence", "tests/test_meeting_deliberation.py"),
    ("Retro Pixel Companions & Creator", "tests/test_pixel_companions_and_creator.py"),
    ("FlowPilot Master Dashboard & Scratchpad", "tests/test_flowpilot_dashboard.py"),
    ("Native Workspace Presentation & Bindings", "tests/test_workspace_refresh.py"),
    ("Selected-Text Transforms & Dictation History Vault", "tests/test_transforms_and_history.py"),
    ("Multilingual Workstation & Real-Time Translation", "tests/test_multilingual_workstation.py"),
    ("User-Facing Fixes (Mic Device, Dynamic Personalization & Safe Targeting)", "tests/test_user_facing_fixes.py"),
    ("STTEngine Model Lifecycle & Orchestrator Ownership", "tests/test_model_lifecycle.py"),
    ("Honest Transforms & Enforced Apply Guardrails", "tests/test_honest_transforms.py"),
    ("Multilingual Evaluation Metrics & Corpus Schema", "tests/test_evaluation_metrics.py"),
    ("Evaluation Metrics Cross-Language Regression", "tests/test_evaluation_metrics_crosslang.py"),

    ("Personalization & Bounded Prompt Budgeting (PR 3)", "tests/test_personalization_pr3.py"),
    ("Bounded Voice Editing & Atomic Transactions (PR 4)", "tests/test_voice_editor_pr4.py"),
    ("Kiki Anime Companion Prototype & States (Gemini B)", "tests/test_kiki_companion.py"),
    ("Handoff Integration & Adversarial Safety", "tests/test_review_integration.py"),
    ("Voice Command Mode & Local LLM Rewriting (PR 5)", "tests/test_voice_command_and_llm.py"),
    ("Modern UI Automation & Focus Robustness", "tests/test_target_verification_modern_apps.py"),
    ("Release Integrity Regression Guards", "tests/test_release_integrity_fixes.py"),
    ("Persistent Audio Input Identity and Resolution", "tests/test_audio_devices.py"),
    ("Benchmark Visible Delivery Observer and Latency", "tests/test_delivery_observer.py"),
    ("Pilot Capture, Integrity, and Local Metrics", "tests/test_pilot_reliability.py"),
    ("Transparent Dictation Recovery & Visual Feedback", "tests/test_recovery_feedback.py"),
]


def ensure_desktop_accessible():
    # Non-destructive desktop access verification (do not kill system processes like LockApp)
    pass

def run_suite(require_all: bool = False):
    print("=" * 70)
    print("           FLOWPILOT AUTOMATED AUDIT SUITE EXECUTION")
    print("=" * 70)
    results = []
    start_total = time.time()

    for name, script in TESTS:
        ensure_desktop_accessible()
        print(f"\n--- Running: {name} ({script}) ---", flush=True)
        t0 = time.time()
        # Every suite gets a fresh config profile. Otherwise the user's model
        # choice and settings can make the state-machine test take minutes and
        # can let tests modify the user's real profile.
        with tempfile.TemporaryDirectory(prefix="flowpilot-suite-") as profile_dir:
            suite_env = os.environ.copy()
            suite_env["FLOWPILOT_CONFIG_DIR"] = profile_dir
            suite_env["FLOWPILOT_CONFIG_FILE"] = str(Path(profile_dir) / "config.json")
            try:
                res = subprocess.run(
                    [sys.executable, "-X", "utf8", script], capture_output=True,
                    encoding="utf-8", errors="replace", env=suite_env,
                    timeout=240,
                )
                returncode, stdout, stderr = res.returncode, res.stdout, res.stderr
            except subprocess.TimeoutExpired as exc:
                returncode = 124
                stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                stderr += f"\nSuite exceeded 240 seconds: {script}"
        dur = time.time() - t0
        passed = (returncode == 0)
        is_skipped = passed and ("[RESULT] SKIPPED:" in stdout or "[SKIP]" in stdout)
        results.append((name, passed, is_skipped, dur, stdout, stderr))
        status_str = "SKIPPED" if is_skipped else ("PASSED" if passed else "FAILED")
        print(f"Status: {status_str} ({dur:.2f}s)", flush=True)
        if not passed:
            print("STDOUT:\n", stdout, flush=True)
            print("STDERR:\n", stderr, flush=True)

    total_dur = time.time() - start_total
    print("\n" + "=" * 70)
    print("                    AUDIT SUMMARY RESULTS")
    print("=" * 70)
    all_passed = True
    any_skipped = False
    for name, passed, is_skipped, dur, _, _ in results:
        if is_skipped:
            status_str = "[SKIP]"
            any_skipped = True
        elif passed:
            status_str = "[PASS]"
        else:
            status_str = "[FAIL]"
            all_passed = False
        print(f"{status_str} {name:<45} ({dur:.2f}s)")

    print("-" * 70)
    if not all_passed:
        verdict = "FAILURES DETECTED"
    elif any_skipped:
        verdict = "RELEASE GATE BLOCKED: SKIPPED SUITES" if require_all else "PASSED WITH SKIPPED SUITES"
    else:
        verdict = "ALL TESTS PASSED"
    passed_count = sum(passed and not skipped for _, passed, skipped, *_ in results)
    skipped_count = sum(skipped for _, _, skipped, *_ in results)
    failed_count = len(results) - passed_count - skipped_count
    print(f"Suites: {len(results)} total, {passed_count} passed, {skipped_count} skipped, {failed_count} failed")
    print(f"Total Test Time: {total_dur:.2f}s | Overall Verdict: {verdict}")
    print("=" * 70)
    return all_passed and (not require_all or not any_skipped)

if __name__ == "__main__":
    success = run_suite(require_all="--require-all" in sys.argv)
    sys.exit(0 if success else 1)
