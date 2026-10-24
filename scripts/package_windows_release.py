"""Feature 13: Package and verify an offline Windows release candidate."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_ROOT_FILES = ("LICENSE", "THIRD_PARTY_LICENSES.md", "PRIVACY.md", "README.md")
REQUIRED_NOTICES = (
    "licenses/qt/LGPL-3.0-only.txt",
    "licenses/qt/GPL-3.0-only.txt",
    "licenses/models/OpenAI-Whisper-LICENSE.txt",
    "licenses/models/Silero-VAD-LICENSE.txt",
    "licenses/companions/SondeR-Cat-LICENSE.txt",
    "licenses/companions/SondeR-Cat-NOTICE.txt",
    "licenses/python/MANIFEST.json",
)
FORBIDDEN = ("wispr_renderer", "wispr_bridge", "flow.sqlite", "access_token", ".env", "private/")
UNUSED_QT = ("qt6virtualkeyboard.dll", "qtvirtualkeyboardplugin.dll", "qt6pdf.dll", "qpdf.dll")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def package(bundle: Path, archive: Path) -> dict:
    bundle = bundle.resolve()
    archive = archive.resolve()
    release_root = (ROOT / "dist").resolve()
    if not bundle.is_relative_to(release_root) or not archive.is_relative_to(release_root):
        raise ValueError("Bundle and archive must stay inside dist/")
    if archive.is_relative_to(bundle):
        raise ValueError("Archive must not be inside the bundle being packaged")
    if not (bundle / "FlowPilot.exe").is_file():
        raise FileNotFoundError("The bundle has no FlowPilot.exe")
    if archive.exists():
        raise FileExistsError(f"Refusing to replace existing archive: {archive}")

    entries = [(path, "FlowPilot/" + path.relative_to(bundle).as_posix())
               for path in sorted(bundle.rglob("*")) if path.is_file()]
    entries.extend((ROOT / name, name) for name in REQUIRED_ROOT_FILES)
    entries.extend((path, path.relative_to(ROOT).as_posix())
                   for path in sorted((ROOT / "licenses").rglob("*")) if path.is_file())
    names = [name for _, name in entries]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate ZIP member names")
    if any(any(term in name.lower() for term in FORBIDDEN) for name in names):
        raise ValueError("Forbidden competitor, credential, or private path")
    if any(Path(name).name.lower() in UNUSED_QT for name in names):
        raise ValueError("Unused Qt module remains in the bundle")
    if not set(REQUIRED_NOTICES).issubset(names):
        raise ValueError("Required license notice is missing")
    if not all(path.is_file() for path, _ in entries):
        raise FileNotFoundError("A release notice or documentation file is missing")

    archive.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as zipped:
        for source, name in entries:
            zipped.write(source, name)

    with ZipFile(archive) as zipped:
        bad = zipped.testzip()
        if bad is not None:
            raise ValueError(f"ZIP CRC failed: {bad}")
        executable_hash = hashlib.sha256(zipped.read("FlowPilot/FlowPilot.exe")).hexdigest().upper()
    if executable_hash != sha256_file(bundle / "FlowPilot.exe"):
        raise ValueError("Embedded executable differs from the tested bundle")

    return {
        "archive": str(archive),
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": sha256_file(archive),
        "executable_bytes": (bundle / "FlowPilot.exe").stat().st_size,
        "executable_sha256": executable_hash,
        "members": len(names),
        "notice_files": sum(name.startswith("licenses/") for name in names),
        "crc_passed": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.bundle, args.archive), indent=2))
