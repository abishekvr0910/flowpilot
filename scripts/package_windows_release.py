"""Feature 13: Package and verify an offline Windows release candidate."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Optional
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


def find_signtool() -> Optional[Path]:
    """Finds signtool.exe in PATH or standard Windows SDK install locations."""
    import shutil
    which_path = shutil.which("signtool.exe")
    if which_path:
        return Path(which_path)
    sdk_root = Path("C:/Program Files (x86)/Windows Kits/10/bin")
    if sdk_root.is_dir():
        for candidate in sorted(sdk_root.glob("*/x64/signtool.exe"), reverse=True):
            if candidate.is_file():
                return candidate
    return None


def sign_executable(
    executable_path: Path,
    cert_path: Optional[Path] = None,
    cert_password: Optional[str] = None,
    thumbprint: Optional[str] = None,
    subject: Optional[str] = None,
    cert_store: str = "My",
    use_machine_store: bool = False,
    signtool_path: Optional[Path] = None,
    timestamp_url: str = "http://timestamp.digicert.com"
) -> dict:
    """Signs the Windows executable using signtool.exe if a certificate or thumbprint is provided."""
    has_cert_file = bool(cert_path and cert_path.is_file())
    has_thumbprint = bool(thumbprint and thumbprint.strip())
    has_subject = bool(subject and subject.strip())

    if not (has_cert_file or has_thumbprint or has_subject):
        return {
            "signed": False,
            "status": "UNSIGNED_PILOT",
            "message": "No code signing certificate supplied; binary remains unsigned (Windows SmartScreen warning expected in pilot)."
        }
    tool = signtool_path or find_signtool()
    if not tool or not tool.is_file():
        return {
            "signed": False,
            "status": "SIGNTOOL_MISSING",
            "message": "signtool.exe not found in PATH or Windows Kits. Install Windows SDK to enable Authenticode signing."
        }
    cmd = [
        str(tool), "sign", "/fd", "SHA256",
        "/tr", timestamp_url, "/td", "SHA256",
    ]
    if has_cert_file:
        cmd.extend(["/f", str(cert_path)])
        if cert_password:
            cmd.extend(["/p", cert_password])
    elif has_thumbprint:
        cmd.extend(["/sha1", thumbprint.strip(), "/s", cert_store])
        if use_machine_store:
            cmd.append("/sm")
    elif has_subject:
        cmd.extend(["/n", subject.strip(), "/s", cert_store])
        if use_machine_store:
            cmd.append("/sm")

    cmd.append(str(executable_path))
    try:
        res = subprocess.run(
            cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"signed": False, "status": "SIGN_FAILED", "error": "signtool timed out"}
    if res.returncode == 0:
        verify_cmd = [str(tool), "verify", "/pa", "/v", str(executable_path)]
        try:
            res_v = subprocess.run(
                verify_cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=30,
            )
            verified = (res_v.returncode == 0)
        except Exception:
            verified = False

        return {
            "signed": True,
            "status": "AUTHENTICODE_SIGNED",
            "signtool": str(tool),
            "timestamp_url": timestamp_url,
            "verified": verified
        }
    return {
        "signed": False,
        "status": "SIGN_FAILED",
        "error": res.stderr.strip() or res.stdout.strip()
    }


def main(argv=None) -> dict:
    """Package an unsigned pilot or fail closed when signing was requested."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--cert", type=Path, default=None, help="Path to Authenticode .pfx certificate")
    parser.add_argument("--cert-password-env", metavar="NAME", help="Environment variable holding the .pfx password")
    parser.add_argument("--thumbprint", type=str, default=None, help="SHA-1 thumbprint of certificate in Windows Certificate Store or HSM")
    parser.add_argument("--subject", type=str, default=None, help="Subject name substring of certificate in Windows Certificate Store")
    parser.add_argument("--cert-store", type=str, default="My", help="Certificate store name (default 'My')")
    parser.add_argument("--use-machine-store", action="store_true", help="Use Local Machine certificate store instead of Current User")
    parser.add_argument("--signtool", type=Path, default=None, help="Explicit path to signtool.exe")
    parser.add_argument("--timestamp-url", type=str, default="http://timestamp.digicert.com", help="RFC 3161 timestamp server URL")
    args = parser.parse_args(argv)

    if args.cert_password_env and not args.cert:
        parser.error("--cert-password-env requires --cert")

    cert_path = args.cert
    cert_password = None
    if args.cert_password_env:
        cert_password = os.environ.get(args.cert_password_env)
        if cert_password is None:
            parser.error(f"Signing password environment variable {args.cert_password_env} is not set")
    elif not cert_password and os.environ.get("FLOWPILOT_SIGN_PASSWORD"):
        cert_password = os.environ.get("FLOWPILOT_SIGN_PASSWORD")

    temp_cert_file = None
    if not cert_path and os.environ.get("FLOWPILOT_SIGN_PFX_PATH"):
        env_pfx = Path(os.environ["FLOWPILOT_SIGN_PFX_PATH"])
        if env_pfx.is_file():
            cert_path = env_pfx
    elif not cert_path and os.environ.get("FLOWPILOT_SIGN_CERT_BASE64"):
        import base64
        import tempfile
        try:
            cert_bytes = base64.b64decode(os.environ["FLOWPILOT_SIGN_CERT_BASE64"])
            temp_cert_file = tempfile.NamedTemporaryFile(suffix=".pfx", delete=False)
            temp_cert_file.write(cert_bytes)
            temp_cert_file.close()
            cert_path = Path(temp_cert_file.name)
        except Exception:
            pass

    thumbprint = args.thumbprint or os.environ.get("FLOWPILOT_SIGN_THUMBPRINT")
    subject = args.subject or os.environ.get("FLOWPILOT_SIGN_SUBJECT")

    signing_requested = bool(args.cert or cert_path or thumbprint or subject)

    try:
        signing_info = sign_executable(
            args.bundle / "FlowPilot.exe",
            cert_path=cert_path,
            cert_password=cert_password,
            thumbprint=thumbprint,
            subject=subject,
            cert_store=args.cert_store,
            use_machine_store=args.use_machine_store,
            signtool_path=args.signtool,
            timestamp_url=args.timestamp_url,
        )
        if signing_requested and not signing_info["signed"]:
            raise RuntimeError(f"Requested signing failed: {signing_info['status']}")
        result = package(args.bundle, args.archive)
        result["code_signing"] = signing_info
        return result
    finally:
        if temp_cert_file and os.path.exists(temp_cert_file.name):
            try:
                os.unlink(temp_cert_file.name)
            except Exception:
                pass


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))
