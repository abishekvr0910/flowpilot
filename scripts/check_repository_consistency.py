"""Offline checks for release metadata, README defaults, and maintained doc links."""
import ast
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
ACTIVE_DOCS = (
    "README.md", "QUICKSTART.md", "TRUST.md", "PRIVACY.md", "SECURITY.md",
    "SUPPORT.md", "CONTRIBUTING.md", "AGENTS.md", "docs/STATUS.md",
    "docs/scope/index.md", "docs/scope/voice.md", "docs/scope/release.md",
    "docs/research/HANDY_SOURCE_REVIEW_2026-11-14.md",
    "engine/AGENTS.md", "ui/AGENTS.md", "tests/AGENTS.md",
)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def literal_assignment(path, name):
    for node in ast.parse(read(path)).body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            return ast.literal_eval(node.value)
    raise ValueError(f"{path}: missing {name}")


def check():
    errors = []
    version = literal_assignment("engine/__init__.py", "__version__")
    versions = {
        "pyproject.toml": re.search(r'^version = "([^"]+)"', read("pyproject.toml"), re.M).group(1),
        "package.json": json.loads(read("package.json"))["version"],
        "installer/flowpilot_setup.iss": re.search(r'#define MyAppVersion "([^"]+)"', read("installer/flowpilot_setup.iss")).group(1),
    }
    for path, actual in versions.items():
        if actual != version:
            errors.append(f"{path}: version {actual} differs from engine {version}")
    pe = read("version_info.txt")
    for field in ("FileVersion", "ProductVersion"):
        if f"StringStruct('{field}', '{version}.0')" not in pe:
            errors.append(f"version_info.txt: stale {field}")
    numeric_version = tuple(int(part) for part in version.split(".")) + (0,)
    for field in ("filevers", "prodvers"):
        if f"{field}={numeric_version}" not in pe:
            errors.append(f"version_info.txt: stale {field}")

    defaults = literal_assignment("engine/config.py", "DEFAULT_CONFIG")
    for block in re.findall(r"```json\s*\n(.*?)```", read("README.md"), re.S):
        for key, value in json.loads(block).items():
            if key not in defaults or defaults[key] != value:
                errors.append(f"README.md: default {key} differs from engine/config.py")

    suites = literal_assignment("tests/run_all_tests.py", "TESTS")
    paths = [path for _, path in suites]
    if len(paths) != len(set(paths)):
        errors.append("tests/run_all_tests.py: duplicate suite registration")
    for path in paths:
        if not (ROOT / path).is_file():
            errors.append(f"tests/run_all_tests.py: missing {path}")

    # Dated historical evidence keeps its original context. This check covers
    # maintained entry points, not deleted historical artifacts or remote URLs.
    for path in ACTIVE_DOCS:
        if not (ROOT / path).is_file():
            errors.append(f"Missing maintained document: {path}")
            continue
        source = re.sub(r"```.*?```", "", read(path), flags=re.S)
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", source):
            target = target.strip().strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = (ROOT / path).parent / unquote(parsed.path)
            if not resolved.exists():
                errors.append(f"{path}: missing linked path {target}")
    return version, len(suites), errors


if __name__ == "__main__":
    version, count, errors = check()
    for error in errors:
        print(f"[FAIL] {error}")
    print(f"Repository consistency: version {version}, {count} registered suites, {len(errors)} errors")
    raise SystemExit(1 if errors else 0)
