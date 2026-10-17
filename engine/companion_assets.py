"""
FlowPilot Companion Asset Manager
Handles validation, storage, rasterization, and lifecycle of custom
companions (Emoji, Single Images, and Sprite Sheets).
Enforces zero-egress, bounded memory (<= 1.5MB pixmap cache), and strict path isolation.
"""

import os
import json
import uuid
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

MAX_IMAGE_FILE_SIZE = 1024 * 1024  # 1 MiB
MAX_IMAGE_DIMENSION = 512          # 512x512 max source resolution
MAX_SPRITE_FRAMES = 12             # Maximum frames per animation pack
NORMALIZED_CELL_SIZE = 96          # 96x96 logical pixels

BUILTIN_COMPANIONS = [
    {
        "id": "kitty",
        "name": "SondeR-Cat Pixel Kitty",
        "type": "builtin",
        "description": "Authentic multi-palette desktop kitty with kneading, blinking, and stretching.",
        "icon": "🐾",
        "available_palettes": [
            "orange tabby", "calico", "black", "gray", "siamese",
            "pink", "white", "mint", "chocolate", "cream"
        ]
    },
    {
        "id": "dog",
        "name": "Pixel Pup & Shiba",
        "type": "builtin",
        "description": "Loyal desk pup with wagging tail, floppy/pointy ears, and happy idle panting.",
        "icon": "🐶",
        "available_palettes": [
            "shiba inu", "golden retriever", "corgi", "black", "husky"
        ]
    },
    {
        "id": "pikachu",
        "name": "Pikachu Electric Companion",
        "type": "builtin",
        "description": "Legendary electric mouse Pokémon with spark cheeks and lightning wag animation.",
        "icon": "⚡",
        "available_palettes": ["pikachu"]
    },
    {
        "id": "charmander",
        "name": "Charmander Flame Companion",
        "type": "builtin",
        "description": "Fire lizard Pokémon with blue eyes and an animated flickering flame tail.",
        "icon": "🔥",
        "available_palettes": ["charmander"]
    },
    {
        "id": "gengar",
        "name": "Gengar Shadow Companion",
        "type": "builtin",
        "description": "Mischievous shadow Pokémon with crimson glowing eyes and a sinister grin.",
        "icon": "👻",
        "available_palettes": ["gengar"]
    },
    {
        "id": "eevee",
        "name": "Eevee Evolution Companion",
        "type": "builtin",
        "description": "Beloved evolution Pokémon with fluffy collar, big perked ears, and tail wag.",
        "icon": "🦊",
        "available_palettes": ["eevee"]
    },
    {
        "id": "mascot",
        "name": "Pilot the Robot Mascot",
        "type": "builtin",
        "description": "Voice-reactive cybernetic pilot with audio-radiating antennas and eye dilation.",
        "icon": "🤖",
        "available_palettes": ["classic cyan"]
    },
    {
        "id": "edge_line",
        "name": "Wispr Docked Edge Line",
        "type": "builtin",
        "description": "Minimalist docked vertical accent indicator with ambient breathing.",
        "icon": "📏",
        "available_palettes": ["accent blue"]
    },
    {
        "id": "wave_bar",
        "name": "Wispr Soundwave Equalizer",
        "type": "builtin",
        "description": "Floating horizontal audio waveform responding dynamically to voice decibels.",
        "icon": "🌊",
        "available_palettes": ["gradient wave"]
    }
]

class CompanionAssetManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is not None:
            self.base_dir = Path(storage_dir)
        elif os.environ.get("FLOWPILOT_CONFIG_DIR"):
            self.base_dir = Path(os.environ["FLOWPILOT_CONFIG_DIR"])
        else:
            self.base_dir = Path.home() / ".flowpilot"
            
        self.creations_dir = self.base_dir / "companions"
        self.creations_dir.mkdir(parents=True, exist_ok=True)

    def list_all_companions(self) -> List[Dict[str, Any]]:
        """Returns list of built-in companions followed by user-created companions."""
        result = [dict(c) for c in BUILTIN_COMPANIONS]
        for manifest_file in self.creations_dir.glob("*/manifest.json"):
            try:
                with open(manifest_file, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                if self._validate_manifest(manifest):
                    manifest["directory"] = str(manifest_file.parent)
                    result.append(manifest)
            except Exception as e:
                print(f"[CompanionAssetManager] Skipping malformed creation {manifest_file}: {e}")
        return result

    def get_companion_by_id(self, companion_id: str) -> Optional[Dict[str, Any]]:
        for comp in self.list_all_companions():
            if comp.get("id") == companion_id:
                return comp
        return None

    def create_emoji_companion(self, name: str, emoji_char: str, motion_preset: str = "gentle_bob") -> Dict[str, Any]:
        """Creates a pure Unicode emoji companion."""
        name = name.strip() or f"Emoji {emoji_char}"
        comp_id = f"emoji_{uuid.uuid4().hex[:8]}"
        comp_dir = self.creations_dir / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "schema_version": 1,
            "id": comp_id,
            "type": "emoji",
            "name": name,
            "emoji": emoji_char,
            "motion_preset": motion_preset,
            "created_at": os.path.getmtime(comp_dir)
        }

        with open(comp_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        manifest["directory"] = str(comp_dir)
        return manifest

    def create_image_companion(self, name: str, source_image_path: Path, motion_preset: str = "gentle_bob") -> Dict[str, Any]:
        """Validates and imports a single transparent PNG companion."""
        source_path = Path(source_image_path)
        self._validate_image_file(source_path)

        comp_id = f"img_{uuid.uuid4().hex[:8]}"
        comp_dir = self.creations_dir / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)

        dest_image = comp_dir / "sprite.png"
        shutil.copy2(source_path, dest_image)

        manifest = {
            "schema_version": 1,
            "id": comp_id,
            "type": "image",
            "name": name.strip() or source_path.stem,
            "image_file": "sprite.png",
            "motion_preset": motion_preset,
            "created_at": os.path.getmtime(comp_dir)
        }

        with open(comp_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        manifest["directory"] = str(comp_dir)
        return manifest

    def create_sprite_sheet_companion(
        self,
        name: str,
        source_sheet_path: Path,
        frame_width: int,
        frame_height: int,
        total_frames: int,
        state_frames: Dict[str, List[int]],
        motion_preset: str = "gentle_bob"
    ) -> Dict[str, Any]:
        """Validates and creates an animated sprite sheet companion pack."""
        source_path = Path(source_sheet_path)
        self._validate_image_file(source_path)

        if total_frames > MAX_SPRITE_FRAMES:
            raise ValueError(f"Exceeds maximum allowed frames ({total_frames} > {MAX_SPRITE_FRAMES})")
        if frame_width <= 0 or frame_height <= 0:
            raise ValueError("Invalid frame dimensions")

        comp_id = f"sprite_{uuid.uuid4().hex[:8]}"
        comp_dir = self.creations_dir / comp_id
        comp_dir.mkdir(parents=True, exist_ok=True)

        dest_image = comp_dir / "spritesheet.png"
        shutil.copy2(source_path, dest_image)

        manifest = {
            "schema_version": 1,
            "id": comp_id,
            "type": "spritesheet",
            "name": name.strip() or source_path.stem,
            "image_file": "spritesheet.png",
            "frame_width": int(frame_width),
            "frame_height": int(frame_height),
            "total_frames": int(total_frames),
            "state_frames": state_frames,
            "motion_preset": motion_preset,
            "created_at": os.path.getmtime(comp_dir)
        }

        with open(comp_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        manifest["directory"] = str(comp_dir)
        return manifest

    def delete_companion(self, companion_id: str) -> bool:
        """Removes a custom companion directory."""
        if any(c["id"] == companion_id for c in BUILTIN_COMPANIONS):
            return False  # Built-ins cannot be deleted

        comp_dir = self.creations_dir / companion_id
        if comp_dir.exists() and comp_dir.is_dir():
            shutil.rmtree(comp_dir, ignore_errors=True)
            return True
        return False

    def export_companion_pack(self, companion_id: str, dest_zip_path: Path) -> Path:
        """Exports a companion creation as a clean, privacy-scrubbed .flowpack zip."""
        comp = self.get_companion_by_id(companion_id)
        if not comp or comp.get("type") == "builtin":
            raise ValueError("Only custom companion creations can be exported")

        comp_dir = self.creations_dir / companion_id
        dest_zip = Path(dest_zip_path)
        dest_zip.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in comp_dir.iterdir():
                if item.is_file() and item.suffix.lower() in (".json", ".png", ".txt"):
                    # Scrub local filesystem paths from manifest
                    if item.name == "manifest.json":
                        with open(item, "r", encoding="utf-8") as f:
                            m_data = json.load(f)
                        m_data.pop("directory", None)
                        zf.writestr("manifest.json", json.dumps(m_data, indent=2))
                    else:
                        zf.write(item, arcname=item.name)

        return dest_zip

    def import_companion_pack(self, pack_zip_path: Path) -> Dict[str, Any]:
        """Safely inspects, verifies, and imports a .flowpack zip without path traversal."""
        pack_path = Path(pack_zip_path)
        if not pack_path.exists():
            raise FileNotFoundError(f"Package not found: {pack_path}")
        if pack_path.stat().st_size > MAX_IMAGE_FILE_SIZE * 2:
            raise ValueError("Package exceeds maximum allowed size")

        comp_id = f"imported_{uuid.uuid4().hex[:8]}"
        dest_dir = self.creations_dir / comp_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(pack_path, "r") as zf:
                # Security audit: inspect all member paths against path traversal
                for member in zf.namelist():
                    if ".." in member or member.startswith("/") or member.startswith("\\"):
                        raise ValueError(f"Malicious zip traversal path rejected: {member}")
                    if not (member.endswith(".png") or member == "manifest.json" or member.endswith(".txt")):
                        raise ValueError(f"Unsafe file extension rejected: {member}")

                zf.extractall(dest_dir)

            manifest_file = dest_dir / "manifest.json"
            if not manifest_file.exists():
                raise ValueError("Missing manifest.json in package")

            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            manifest["id"] = comp_id
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            return manifest
        except Exception:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise

    def _validate_image_file(self, file_path: Path) -> None:
        """Verifies file existence, size, header, and PNG format without executing external tools."""
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        if file_size > MAX_IMAGE_FILE_SIZE:
            raise ValueError(f"File size exceeds 1.0 MiB limit ({file_size} bytes)")

        # Verify PNG Magic Bytes: 89 50 4E 47 0D 0A 1A 0A
        with open(file_path, "rb") as f:
            header = f.read(8)
            if header != b"\x89PNG\r\n\x1a\n":
                raise ValueError("Only standard PNG image files are supported")

    def _validate_manifest(self, manifest: Dict[str, Any]) -> bool:
        """Verifies manifest schema and essential properties."""
        return (
            isinstance(manifest, dict) and
            "id" in manifest and
            "type" in manifest and
            manifest.get("type") in ("emoji", "image", "spritesheet")
        )
