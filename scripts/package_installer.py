#!/usr/bin/env python3
"""
FlowPilot Windows Installer Packaging Script
Compiles the Inno Setup script into a 1-click Windows installer:
FlowPilot-Setup-v<version>.exe (plus .sha256 sidecar and optional Authenticode signing)
"""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / "dist"
BUNDLE_DIR = DIST_DIR / "FlowPilot"
ISS_PATH = REPO_ROOT / "installer" / "flowpilot_setup.iss"

COMMON_ISCC_PATHS = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Users") / os.environ.get("USERNAME", "") / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe"
]


def find_iscc() -> Path:
    cmd = shutil.which("iscc") or shutil.which("ISCC")
    if cmd:
        return Path(cmd)
    for p in COMMON_ISCC_PATHS:
        if p.exists():
            return p
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    print("=" * 70)
    print("       FLOWPILOT 1-CLICK WINDOWS INSTALLER BUILDER")
    print("=" * 70)

    if not (BUNDLE_DIR / "FlowPilot.exe").exists():
        print(f"[Error] Frozen binary bundle missing at: {BUNDLE_DIR}")
        print("Please compile the binary first via: python -m PyInstaller flowpilot.spec --noconfirm")
        sys.exit(1)

    iscc_exe = find_iscc()
    if not iscc_exe:
        print("[Warning] Inno Setup 6 compiler (ISCC.exe) not found on system.")
        print("To compile the installer:")
        print("  1. Download and install Inno Setup 6 (https://jrsoftware.org/isdl.php)")
        print(f"  2. Run: ISCC.exe {ISS_PATH}")
        print("\nThe Inno Setup script is prepared at: installer/flowpilot_setup.iss")
        return 0

    print(f"Found Inno Setup Compiler: {iscc_exe}")
    print(f"Compiling installer from: {ISS_PATH} ...")

    cmd = [str(iscc_exe), str(ISS_PATH)]
    res = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")

    if res.returncode != 0:
        print("[Error] ISCC failed with code", res.returncode)
        print("STDOUT:\n", res.stdout)
        print("STDERR:\n", res.stderr)
        sys.exit(res.returncode)

    sys.path.insert(0, str(REPO_ROOT))
    from engine import __version__
    installer_path = DIST_DIR / f"FlowPilot-Setup-v{__version__}.exe"
    if not installer_path.exists():
        print(f"[Error] Expected installer output missing: {installer_path}")
        sys.exit(1)

    # Sign outer Setup.exe if signing secrets/certificates are configured in environment
    if any(os.environ.get(k) for k in ("FLOWPILOT_SIGN_PFX_PATH", "FLOWPILOT_SIGN_CERT_BASE64", "FLOWPILOT_SIGN_THUMBPRINT")):
        from scripts.sign_authenticode import main as sign_main
        rc = sign_main(["--target", str(installer_path)])
        if rc != 0:
            print("[Error] Requested Authenticode signing of Setup installer failed.")
            sys.exit(rc)

    size_mb = installer_path.stat().st_size / (1024 * 1024)
    file_hash = sha256_file(installer_path)
    sidecar = Path(str(installer_path) + ".sha256")
    sidecar.write_text(f"{file_hash.lower()}  {installer_path.name}\n", encoding="utf-8")

    print("\n" + "=" * 70)
    print("SUCCESS: Installer built successfully!")
    print(f"Path: {installer_path}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"SHA-256: {file_hash}")
    print(f"Sidecar: {sidecar}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
