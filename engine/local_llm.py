"""
FlowPilot Local LLM Provider
Enables optional offline AI rewriting, tone transformations, and Command Mode
using locally running Ollama, llama.cpp, or LM Studio instances (strictly localhost only).

Zero external network egress invariant is strictly enforced:
Only connects to loopback addresses (127.0.0.1, localhost).
"""

import json
import logging
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("FlowPilot.LocalLLM")

DEFAULT_ENDPOINTS = [
    "http://127.0.0.1:11434",  # Ollama default
    "http://127.0.0.1:1234",   # LM Studio default
    "http://127.0.0.1:8080",   # llama.cpp server default
]


class LocalLLMProvider:
    """
    Offline local LLM adapter for AI rewriting and Command Mode.
    Strictly restricted to localhost endpoints.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None, timeout: float = 2.0):
        self.base_url = (base_url or "http://127.0.0.1:11434").rstrip("/")
        self.preferred_model = model
        self.timeout = timeout
        self._cached_available: Optional[bool] = None
        self._cache_timestamp: float = 0.0
        self._active_model: Optional[str] = None
        self._cache_ttl = 15.0  # Check health every 15s

    def _is_loopback(self, url: str) -> bool:
        """Enforces zero external network egress invariant."""
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            return host in ("127.0.0.1", "localhost", "::1")
        except Exception:
            return False

    def is_available(self, force_refresh: bool = False) -> bool:
        """
        Non-blocking health check against local LLM endpoint.
        Returns True if a local model server is reachable.
        """
        now = time.time()
        if not force_refresh and self._cached_available is not None:
            if now - self._cache_timestamp < self._cache_ttl:
                return self._cached_available

        if not self._is_loopback(self.base_url):
            logger.warning(f"[LocalLLM] Non-loopback URL rejected for security: {self.base_url}")
            self._cached_available = False
            self._cache_timestamp = now
            return False

        # Attempt Ollama /api/tags or OpenAI /v1/models
        available = False
        detected_model = None

        # 1. Try Ollama tags endpoint
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"User-Agent": "FlowPilot/LocalLLM"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=0.6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    if models:
                        available = True
                        detected_model = self.preferred_model if self.preferred_model in models else models[0]
        except Exception:
            pass

        # 2. Try standard OpenAI /v1/models endpoint (LM Studio / llama.cpp / Ollama)
        if not available:
            try:
                req = urllib.request.Request(
                    f"{self.base_url}/v1/models",
                    headers={"User-Agent": "FlowPilot/LocalLLM"},
                    method="GET"
                )
                with urllib.request.urlopen(req, timeout=0.6) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                        if models:
                            available = True
                            detected_model = self.preferred_model if self.preferred_model in models else models[0]
            except Exception:
                pass

        self._cached_available = available
        self._active_model = detected_model
        self._cache_timestamp = now
        return available

    def get_active_model(self) -> Optional[str]:
        if not self._cached_available:
            self.is_available()
        return self._active_model

    def transform(self, text: str, instruction: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """
        Executes a local prompt transformation on text.
        Returns the transformed text, or None if unavailable or failed.
        """
        if not text or not text.strip():
            return text

        if not self.is_available():
            return None

        model = self._active_model or "llama3.2"
        sys_msg = (
            system_prompt or
            "You are FlowPilot's local writing assistant. "
            "Rewrite the provided text according to the user instruction. "
            "Preserve all facts, numbers, dates, code identifiers, and negations exactly. "
            "Output ONLY the final rewritten text, without conversational prefixes, quotes, or explanations."
        )

        user_content = f"Instruction: {instruction}\n\nText:\n{text}"

        # 1. Try Ollama native /api/generate
        try:
            payload = json.dumps({
                "model": model,
                "prompt": f"{sys_msg}\n\n{user_content}\n\nRewritten text:",
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_predict": max(128, len(text.split()) * 3)
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "FlowPilot/LocalLLM"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    out = res_data.get("response", "").strip()
                    if out:
                        return self._clean_llm_output(out)
        except Exception:
            pass

        # 2. Try OpenAI-compatible /v1/chat/completions (LM Studio, llama.cpp, Ollama)
        try:
            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.2,
                "max_tokens": max(128, len(text.split()) * 3)
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "FlowPilot/LocalLLM"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    choices = res_data.get("choices", [])
                    if choices:
                        out = choices[0].get("message", {}).get("content", "").strip()
                        if out:
                            return self._clean_llm_output(out)
        except Exception as e:
            logger.debug(f"[LocalLLM] Request failed: {e}")

        return None

    def _clean_llm_output(self, text: str) -> str:
        """Strips conversational intro phrases and markdown fences from LLM responses."""
        cleaned = text.strip()

        # 1. Strip common AI preamble prefixes
        prefixes = [
            "Here is the rewritten text:",
            "Here is the revised text:",
            "Here's the rewritten version:",
            "Here is the translated text:",
            "Rewritten text:",
            "Revised text:",
            "Result:"
        ]
        for p in prefixes:
            if cleaned.lower().startswith(p.lower()):
                cleaned = cleaned[len(p):].strip()

        # 2. Strip wrapping markdown code blocks if model wrapped its output
        if cleaned.startswith('```') and cleaned.endswith('```'):
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()
            elif len(lines) == 2:
                cleaned = lines[0].replace('```', '').strip()
            elif len(lines) == 1:
                cleaned = cleaned.replace('```', '').strip()
        elif cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1].strip()

        return cleaned


# Global singleton instance
_GLOBAL_LOCAL_LLM: Optional[LocalLLMProvider] = None

def get_local_llm() -> LocalLLMProvider:
    global _GLOBAL_LOCAL_LLM
    if _GLOBAL_LOCAL_LLM is None:
        _GLOBAL_LOCAL_LLM = LocalLLMProvider()
    return _GLOBAL_LOCAL_LLM
