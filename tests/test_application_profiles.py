"""
FlowPilot Application Profiles & Precedence Regression Tests
Verifies ProfileResolver precedence hierarchy:
1. Explicit Session Selection
2. Configured Per-App Mapping in config['app_profiles']
3. Window Auto-Detection (terminal, developer, chat, email)
4. Default Fallback
And verifies profile-specific formatting behavior (especially terminal mode).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.context_processor import ProfileResolver, ContextProcessor
from engine.writing_intelligence import WritingIntelligence

def test_profile_precedence_hierarchy():
    print("=" * 65)
    print("TEST: PROFILE RESOLVER PRECEDENCE HIERARCHY")
    print("=" * 65)

    base_config = {
        "active_tone_mode": "general",
        "auto_detect_active_app": True,
        "app_profiles": {
            "special_editor.exe": "developer",
            "custom_shell.exe": "terminal"
        }
    }

    # 1. Precedence 1: Explicit Session Selection
    res_session = ProfileResolver.resolve(
        config=base_config,
        active_window={"process_name": "custom_shell.exe", "category": "terminal"},
        session_mode="email"
    )
    assert res_session == "email", f"Expected 'email', got '{res_session}'"
    print("[PASS] Precedence 1: Explicit session override honored.")

    # 2. Precedence 2: Configured Per-App Mapping
    res_app_map = ProfileResolver.resolve(
        config=base_config,
        active_window={"process_name": "special_editor.exe", "category": "general"},
        session_mode=None
    )
    assert res_app_map == "developer", f"Expected 'developer', got '{res_app_map}'"
    print("[PASS] Precedence 2: Configured app_profiles mapping honored.")

    # 3. Precedence 3: Auto-detection from known processes
    res_term = ProfileResolver.resolve(
        config=base_config,
        active_window={"process_name": "powershell.exe", "category": "terminal"},
        session_mode=None
    )
    assert res_term == "terminal", f"Expected 'terminal', got '{res_term}'"

    res_dev = ProfileResolver.resolve(
        config=base_config,
        active_window={"process_name": "code.exe", "category": "developer"},
        session_mode=None
    )
    assert res_dev == "developer", f"Expected 'developer', got '{res_dev}'"

    res_chat = ProfileResolver.resolve(
        config=base_config,
        active_window={"process_name": "slack.exe", "category": "chat"},
        session_mode=None
    )
    assert res_chat == "chat", f"Expected 'chat', got '{res_chat}'"

    res_email = ProfileResolver.resolve(
        config=base_config,
        active_window={"process_name": "outlook.exe", "category": "email"},
        session_mode=None
    )
    assert res_email == "email", f"Expected 'email', got '{res_email}'"
    print("[PASS] Precedence 3: Process auto-detection correctly maps terminal, developer, chat, and email.")

    # 4. Precedence 4: Default fallback
    res_fallback = ProfileResolver.resolve(
        config=base_config,
        active_window={"process_name": "unknown_app.exe", "category": "general"},
        session_mode=None
    )
    assert res_fallback == "general", f"Expected 'general', got '{res_fallback}'"
    print("[PASS] Precedence 4: Default fallback configuration honored.")


def test_terminal_profile_formatting():
    print("\n" + "=" * 65)
    print("TEST: TERMINAL PROFILE OUTPUT CHARACTERISTICS")
    print("=" * 65)

    wi = WritingIntelligence()

    # Case 1: git command (must not capitalize 'git', must not add trailing '.')
    raw_git = "git commit -m initial release"
    res_git = wi.polish(raw_git, mode="polished", style="terminal")["text"]
    assert res_git == "git commit -m initial release", f"Got: '{res_git}'"
    assert not res_git.endswith(".")
    assert res_git.startswith("git")

    # Case 2: pytest with CLI flags
    raw_pytest = "pytest tests/test_session_lifecycle.py -v --dry-run"
    res_pytest = wi.polish(raw_pytest, mode="polished", style="terminal")["text"]
    assert res_pytest == "pytest tests/test_session_lifecycle.py -v --dry-run"
    assert not res_pytest.endswith(".")

    # Case 3: docker command with paths and port mappings
    raw_docker = "docker run -d -p 8080:80 --name webserver nginx"
    res_docker = wi.polish(raw_docker, mode="polished", style="terminal")["text"]
    assert res_docker == "docker run -d -p 8080:80 --name webserver nginx"
    assert not res_docker.endswith(".")

    print("[PASS] Terminal profile guarantees verbatim command casing and zero trailing periods.")


def test_context_processor_end_to_end_profile():
    print("\n" + "=" * 65)
    print("TEST: CONTEXT PROCESSOR PROFILE INTEGRATION")
    print("=" * 65)

    config = {
        "active_tone_mode": "general",
        "auto_detect_active_app": True,
        "app_profiles": {}
    }
    cp = ContextProcessor(config)

    # In powershell -> automatically formatted with terminal profile
    term_window = {"process_name": "powershell.exe", "category": "terminal", "title": "Windows PowerShell"}
    out = cp.process("git status", active_window=term_window)
    assert out == "git status"

    # In VS Code -> formatted with developer profile
    code_window = {"process_name": "code.exe", "category": "developer", "title": "app.py - VS Code"}
    out_code = cp.process("camel case user account id", active_window=code_window)
    assert out_code == "userAccountId"

    print("[PASS] ContextProcessor dynamically adapts output to active application.")


if __name__ == "__main__":
    test_profile_precedence_hierarchy()
    test_terminal_profile_formatting()
    test_context_processor_end_to_end_profile()
    print("\n=======================================================")
    print("ALL APPLICATION PROFILE TESTS PASSED (3/3)")
    print("=======================================================")
