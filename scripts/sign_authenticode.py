#!/usr/bin/env python3
"""
FlowPilot Production Authenticode Signing Pipeline (WP-4)
Discovers signtool.exe, signs executables and installers with RFC 3161 timestamps,
and verifies cryptographic signatures.
"""

import argparse
import base64
import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

COMMON_SIGNTOOL_GLOBS = [
    r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe",
    r"C:\Program Files\Windows Kits\10\bin\*\x64\signtool.exe",
    r"C:\Program Files (x86)\Microsoft SDKs\Windows\*\bin\signtool.exe"
]

DEFAULT_TIMESTAMP_URLS = [
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
    "http://tsa.starfieldtech.com"
]


def find_signtool() -> Optional[Path]:
    """Locates signtool.exe via PATH or Windows 10/11 SDK installations."""
    from shutil import which
    path_hit = which("signtool.exe") or which("signtool")
    if path_hit:
        return Path(path_hit)

    for pattern in COMMON_SIGNTOOL_GLOBS:
        matches = glob.glob(pattern)
        if matches:
            matches.sort(reverse=True)
            return Path(matches[0])

    return None


def verify_file_signature(target_path: Path) -> dict:
    """Verifies Authenticode signature via PowerShell Get-AuthenticodeSignature."""
    escaped = str(target_path).replace("'", "''")
    ps_cmd = f"(Get-AuthenticodeSignature -LiteralPath '{escaped}').Status.ToString()"
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    status_str = res.stdout.strip() if res.returncode == 0 else "Unknown"

    ps_detail = (
        f"(Get-AuthenticodeSignature -LiteralPath '{escaped}') | "
        "Select-Object Status, StatusMessage, @{N='Subject';E={$_.SignerCertificate.Subject}} | ConvertTo-Json"
    )
    res_detail = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_detail],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )

    return {
        "file": str(target_path),
        "status": status_str,
        "is_valid": status_str == "Valid",
        "detail": res_detail.stdout.strip() if res_detail.returncode == 0 else ""
    }


def sign_artifact(
    target_path: Path,
    cert_path: Optional[Path] = None,
    cert_password: Optional[str] = None,
    thumbprint: Optional[str] = None,
    timestamp_url: Optional[str] = None
) -> bool:
    """Signs an executable or DLL using signtool.exe with RFC 3161 timestamp fallback."""
    signtool = find_signtool()
    if not signtool:
        raise RuntimeError("signtool.exe not found. Install the Windows 10/11 SDK.")

    urls = [timestamp_url] if timestamp_url else list(DEFAULT_TIMESTAMP_URLS)
    for ts_url in urls:
        cmd = [str(signtool), "sign", "/fd", "SHA256", "/tr", ts_url, "/td", "SHA256"]
        if cert_path and cert_path.exists():
            cmd.extend(["/f", str(cert_path)])
            if cert_password:
                cmd.extend(["/p", cert_password])
        elif thumbprint:
            cmd.extend(["/sha1", thumbprint.strip()])
        else:
            raise ValueError("Must provide either cert_path (.pfx) or thumbprint (Certificate Store).")

        cmd.append(str(target_path))
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if res.returncode == 0:
            verify_res = subprocess.run(
                [str(signtool), "verify", "/pa", "/v", str(target_path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
            if verify_res.returncode == 0:
                return True
    return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="FlowPilot Authenticode Signing & Verification CLI")
    parser.add_argument(
        "--target",
        type=Path,
        default=REPO_ROOT / "dist" / "FlowPilot" / "FlowPilot.exe",
        help="Executable or installer file to sign or inspect",
    )
    parser.add_argument("--cert", type=Path, default=None, help="Path to Authenticode .pfx certificate")
    parser.add_argument("--cert-password-env", type=str, default=None, help="Environment variable holding .pfx password")
    parser.add_argument("--thumbprint", type=str, default=None, help="SHA-1 certificate thumbprint in Windows Cert Store")
    parser.add_argument("--timestamp-url", type=str, default=None, help="Explicit RFC 3161 timestamp server URL")
    parser.add_argument("--verify-only", action="store_true", help="Inspect signature status without signing")
    args = parser.parse_args(argv)

    print("=" * 70)
    print("      FLOWPILOT PRODUCTION AUTHENTICODE SIGNING PIPELINE")
    print("=" * 70)

    signtool = find_signtool()
    print(f"Signtool path: {signtool or 'NOT FOUND (Install Windows SDK)'}")

    target_exe = args.target
    if not target_exe.exists():
        print(f"\nTarget binary missing at: {target_exe}")
        return 1 if (args.cert or args.thumbprint or args.verify_only) else 0

    cert_path = args.cert
    temp_cert_file = None
    if not cert_path and os.environ.get("FLOWPILOT_SIGN_PFX_PATH"):
        cert_path = Path(os.environ["FLOWPILOT_SIGN_PFX_PATH"])
    elif not cert_path and os.environ.get("FLOWPILOT_SIGN_CERT_BASE64"):
        cert_bytes = base64.b64decode(os.environ["FLOWPILOT_SIGN_CERT_BASE64"], validate=True)
        tf = tempfile.NamedTemporaryFile(suffix=".pfx", delete=False)
        tf.write(cert_bytes)
        tf.close()
        temp_cert_file = Path(tf.name)
        cert_path = temp_cert_file

    cert_password = None
    if args.cert_password_env:
        cert_password = os.environ.get(args.cert_password_env)
    elif os.environ.get("FLOWPILOT_SIGN_PASSWORD"):
        cert_password = os.environ.get("FLOWPILOT_SIGN_PASSWORD")

    thumbprint = args.thumbprint or os.environ.get("FLOWPILOT_SIGN_THUMBPRINT")
    signing_requested = bool((cert_path or thumbprint) and not args.verify_only)

    try:
        if signing_requested:
            print(f"\nSigning artifact: {target_exe} ...")
            ok = sign_artifact(
                target_exe,
                cert_path=cert_path,
                cert_password=cert_password,
                thumbprint=thumbprint,
                timestamp_url=args.timestamp_url,
            )
            if not ok:
                print("[ERROR] Authenticode signing or verification failed.")
                return 1

        sig_info = verify_file_signature(target_exe)
        print(f"\nTarget binary: {target_exe}")
        print(f"Signature status: {sig_info['status']} (Valid: {sig_info['is_valid']})")
        if args.verify_only and not sig_info["is_valid"]:
            return 1
        return 0
    finally:
        if temp_cert_file is not None:
            temp_cert_file.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
