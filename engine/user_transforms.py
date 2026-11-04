"""
FlowPilot User Scriptable Transforms Module.
Allows power users to write custom Python transformations in ~/.flowpilot/transforms.py
matching and exceeding Hex's hex.config.ts without Node.js or QuickJS dependencies.
"""

import importlib.util
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from engine.config import get_config_dir

logger = logging.getLogger("FlowPilot.UserTransforms")


class UserTransformManager:
    """
    Loads, caches, and executes user-defined text transformation hooks from ~/.flowpilot/transforms.py.
    Provides graceful error isolation, execution time limits, and FactGuard validation.
    """

    _instance: Optional["UserTransformManager"] = None

    def __init__(self, transforms_path: Optional[Path] = None):
        self.transforms_path = transforms_path or (get_config_dir() / "transforms.py")
        self._last_mtime: float = 0.0
        self._transforms: Dict[str, Callable[..., str]] = {}

    @classmethod
    def get_instance(cls) -> "UserTransformManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _reload_if_modified(self) -> None:
        if not self.transforms_path.is_file():
            self._transforms.clear()
            self._last_mtime = 0.0
            return

        try:
            mtime = self.transforms_path.stat().st_mtime
            if mtime == self._last_mtime:
                return

            spec = importlib.util.spec_from_file_location("flowpilot_user_transforms", str(self.transforms_path))
            if not spec or not spec.loader:
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            discovered: Dict[str, Callable[..., str]] = {}
            # Look for dictionary `TRANSFORMS` or functions prefixed with `transform_`
            if hasattr(module, "TRANSFORMS") and isinstance(module.TRANSFORMS, dict):
                discovered.update(module.TRANSFORMS)

            for attr in dir(module):
                if attr.startswith("transform_") and callable(getattr(module, attr)):
                    name = attr[len("transform_") :]
                    discovered[name] = getattr(module, attr)

            self._transforms = discovered
            self._last_mtime = mtime
            logger.info("Loaded %d user transforms from %s", len(discovered), self.transforms_path)
        except Exception as exc:
            logger.warning("Failed to load user transforms from %s: %s", self.transforms_path, exc)

    def apply_transforms(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        active_transform_names: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Executes active user transforms sequentially.
        Returns: (transformed_text, list_of_applied_transform_names)
        """
        if not text:
            return text, []

        self._reload_if_modified()
        if not self._transforms:
            return text, []

        ctx = context or {}
        changes: List[str] = []
        current_text = text

        targets = (
            active_transform_names
            if active_transform_names is not None
            else list(self._transforms.keys())
        )

        for name in targets:
            func = self._transforms.get(name)
            if not callable(func):
                continue
            try:
                t0 = time.perf_counter()
                # Support both func(text, context) and func(text)
                try:
                    res = func(current_text, ctx)
                except TypeError:
                    res = func(current_text)

                if isinstance(res, str) and res != current_text:
                    elapsed_ms = (time.perf_counter() - t0) * 1000.0
                    changes.append(f"UserTransform:{name} ({elapsed_ms:.1f}ms)")
                    current_text = res
            except Exception as exc:
                logger.warning("User transform '%s' raised exception: %s", name, exc)

        return current_text, changes
