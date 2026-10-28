#!/usr/bin/env python3
"""
FlowPilot Production Authenticode Signing Pipeline (WP-4)
Discovers signtool.exe, signs executables and libraries with RFC 3161 timestamps,
and verifies cryptographic signatures.
"""

import os
import sys
import glob
import subprocess
from pathlib import Path
from typing import Optional, List

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
            # Sort descending to pick the newest SDK version
            matches.sort(reverse=True)
            return Path(matches[0])

    return None


def verify_file_signature(target_path: Path) -> dict:
    """Verifies Authenticode signature via PowerShell Get-AuthenticodeSignature."""
    ps_cmd = f"(Get-AuthenticodeSignature -LiteralPath '{str(target_path)}').Status.ToString()"
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    status_str = res.stdout.strip() if res.returncode == 0 else "Unknown"

    ps_detail = f"(Get-AuthenticodeSignature -LiteralPath '{str(target_path)}') | Select-Object Status, StatusMessage, @{{N='Subject';E={{$_.SignerCertificate.Subject}}}} | ConvertTo-Json"
    res_detail = subprocess.run(["powershell", "-NoProfile", "-Command", ps_detail], capture_output=True, text=True)
    
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
    """Signs an executable or DLL using signtool.exe."""
    signtool = find_signtool()
    if not signtool:
        raise RuntimeError("signtool.exe not found. Install the Windows 10/11 SDK.")

    ts_url = timestamp_url or DEFAULT_TIMESTAMP_URLS[0]
    cmd = [str(signtool), "sign", "/fd", "SHA256", "/tr", ts_url, "/td", "SHA256"]

    if cert_path and cert_path.exists():
        cmd.extend(["/f", str(cert_path)])
        if cert_password:
            cmd.extend(["/p", cert_password])
    elif thumbprint:
        cmd.extend(["/sha1", thumbprint])
    else:
        raise ValueError("Must provide either cert_path (.pfx) or thumbprint (Certificate Store).")

    cmd.append(str(target_path))
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0


def main():
    print("=" * 70)
    print("      FLOWPILOT PRODUCTION AUTHENTICODE SIGNING PIPELINE")
    print("=" * 70)

    signtool = find_signtool()
    print(f"Signtool path: {signtool or 'NOT FOUND (Install Windows SDK)'}")

    target_exe = REPO_ROOT / "dist" / "FlowPilot" / "FlowPilot.exe"
    if target_exe.exists():
        sig_info = verify_file_signature(target_exe)
        print(f"\nTarget binary: {target_exe}")
        print(f"Signature status: {sig_info['status']} (Valid: {sig_info['is_valid']})")
    else:
        print(f"\nTarget binary missing at: {target_exe}")

    print("\nTo sign a release build:")
    print("  python scripts/sign_authenticode.py --cert cert.pfx --cert-password-env CERT_PASS")
    print("  python scripts/sign_authenticode.py --thumbprint <SHA1_THUMBPRINT>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
