"""
FlowPilot Local LLM Provider
Enables optional offline AI rewriting, tone transformations, and Command Mode
using locally running Ollama, llama.cpp, or LM Studio instances (strictly localhost only).

Zero external network egress invariant is strictly enforced:
Only connects to loopback addresses (127.0.0.1, localhost).
"""

import ipaddress
import socket
import json
import logging
import time
import concurrent.futures
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, Tuple, List
from urllib.parse import urlparse

from engine.config import load_config

logger = logging.getLogger("FlowPilot.LocalLLM")

DEFAULT_ENDPOINTS = [
    "http://127.0.0.1:11434",  # Ollama default
    "http://127.0.0.1:1234",   # LM Studio default
    "http://127.0.0.1:8080",   # llama.cpp server default
]


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevents HTTP redirects to guarantee requests remain strictly on local endpoint."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        logger.warning(f"[LocalLLM] Redirect to '{newurl}' blocked to prevent egress.")
        return None


# Opener with ProxyHandler({}) ensures HTTP_PROXY / HTTPS_PROXY env vars cannot leak egress
_SECURE_LOCAL_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    _NoRedirectHandler()
)

# Dedicated worker pool for bounded LLM transformations to guarantee hard timeout cancellation
_TRANSFORM_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="FlowPilot-LocalLLM"
)


class LocalLLMProvider:
    """
    Offline local LLM adapter for AI rewriting and Command Mode.
    Strictly restricted to localhost endpoints.
    Requires explicit opt-in (enable_local_llm: True) and explicit model configuration.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        enabled: Optional[bool] = None
    ):
        try:
            cfg = load_config()
        except Exception:
            cfg = {}
        self.enabled = enabled if enabled is not None else cfg.get("enable_local_llm", False)
        self.base_url = (base_url or cfg.get("local_llm_endpoint", "http://127.0.0.1:11434")).rstrip("/")
        self.preferred_model = model if model is not None else cfg.get("local_llm_model", "")
        self.timeout = timeout if timeout is not None else float(cfg.get("local_llm_timeout", 3.0))
        self._cached_available: Optional[bool] = None
        self._cache_timestamp: float = 0.0
        self._active_model: Optional[str] = None
        self._cache_ttl = 15.0  # Check health every 15s

    def _is_loopback(self, url: str) -> bool:
        """
        Enforces zero external network egress invariant.
        Rejects any external host immediately without emitting outbound DNS requests.
        Only allows loopback IP literals (127.0.0.0/8, ::1) or 'localhost' / '*.localhost'.
        """
        try:
            parsed = urlparse(url)
            host = parsed.hostname
            if not host:
                return False
            host_clean = host.strip().lower()

            # 1. Standard localhost names (RFC 6761: guaranteed local, no external DNS needed)
            if host_clean == "localhost" or host_clean.endswith(".localhost"):
                return True

            # 2. IP address literal check (IPv4 / IPv6)
            try:
                ip = ipaddress.ip_address(host_clean)
                return ip.is_loopback
            except ValueError:
                # Host is not an IP literal and not localhost -> reject to prevent outbound DNS query
                return False
        except Exception:
            return False

    def is_available(self, force_refresh: bool = False) -> bool:
        """
        Non-blocking health check against local LLM endpoint.
        Returns True if a local model server is reachable AND configured model is installed.
        """
        if not self.enabled:
            self._cached_available = False
            self._active_model = None
            return False

        now = time.time()
        if not force_refresh and self._cached_available is not None:
            if now - self._cache_timestamp < self._cache_ttl:
                return self._cached_available

        if not self._is_loopback(self.base_url):
            logger.warning(f"[LocalLLM] Non-loopback URL rejected for security: {self.base_url}")
            self._cached_available = False
            self._cache_timestamp = now
            return False

        if not self.preferred_model or not self.preferred_model.strip():
            # Explicit model identity required per PR 5 specification; no silent guessing
            logger.info("[LocalLLM] No explicit local_llm_model configured; local writing model inactive.")
            self._cached_available = False
            self._cache_timestamp = now
            return False

        target_model = self.preferred_model.strip()
        available = False
        detected_model = None

        # 1. Try Ollama tags endpoint
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"User-Agent": "FlowPilot/LocalLLM"},
                method="GET"
            )
            with _SECURE_LOCAL_OPENER.open(req, timeout=0.6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    matching = [m for m in models if m == target_model or m.startswith(target_model + ":") or target_model.startswith(m + ":")]
                    if matching:
                        available = True
                        detected_model = matching[0]
                    else:
                        logger.info(f"[LocalLLM] Requested model '{target_model}' not found in Ollama models: {models}")
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
                with _SECURE_LOCAL_OPENER.open(req, timeout=0.6) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        models = [m.get("id") for m in data.get("data", []) if m.get("id")]
                        matching = [m for m in models if m == target_model or m.startswith(target_model + ":") or target_model.startswith(m + ":")]
                        if matching:
                            available = True
                            detected_model = matching[0]
                        else:
                            logger.info(f"[LocalLLM] Requested model '{target_model}' not found in /v1/models: {models}")
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

    def transform(self, text: str, instruction: str, system_prompt: Optional[str] = None, timeout: Optional[float] = None) -> Optional[str]:
        """
        Executes a bounded local prompt transformation on text.
        Returns the transformed text, or None if unavailable, timed out, or failed.
        Enforces a strict total wall-clock deadline; leaves text unchanged on timeout.
        """
        if not text or not text.strip():
            return text

        if not self.is_available():
            return None

        model = self._active_model
        if not model:
            return None

        # Bounded wall-clock deadline across request
        wall_start = time.monotonic()
        max_duration = min(timeout if timeout is not None else self.timeout, 5.0)
        deadline = wall_start + max_duration

        if max_duration <= 0.0 or time.monotonic() >= deadline:
            return None

        # Bounded input length to prevent resource lock
        text_bounded = text[:4000]
        instruction_bounded = instruction[:500]

        sys_msg = (
            system_prompt or
            "You are FlowPilot's local writing assistant. "
            "Rewrite the provided text according to the user instruction. "
            "Preserve all facts, numbers, dates, code identifiers, and negations exactly. "
            "Output ONLY the final rewritten text, without conversational prefixes, quotes, or explanations."
        )

        # Enforce strict wall-clock deadline containment via worker executor
        future = _TRANSFORM_EXECUTOR.submit(
            self._execute_transform_call,
            text_bounded,
            instruction_bounded,
            sys_msg,
            model,
            deadline
        )
        try:
            remaining = max(0.01, deadline - time.monotonic())
            result = future.result(timeout=remaining)
            if time.monotonic() > deadline:
                logger.warning(f"[LocalLLM] Request exceeded deadline ({time.monotonic() - wall_start:.2f}s > {max_duration}s); dropping late result.")
                return None
            return result
        except concurrent.futures.TimeoutError:
            logger.warning(f"[LocalLLM] Wall-clock deadline reached ({max_duration}s); transform timed out.")
            return None
        except Exception as e:
            logger.debug(f"[LocalLLM] Transform execution failed: {e}")
            return None

    def _execute_transform_call(
        self,
        text_bounded: str,
        instruction_bounded: str,
        sys_msg: str,
        model: str,
        deadline: float
    ) -> Optional[str]:
        user_content = f"Instruction: {instruction_bounded}\n\nText:\n{text_bounded}"

        # 1. Try Ollama native /api/generate
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0.05:
                return None

            payload = json.dumps({
                "model": model,
                "prompt": f"{sys_msg}\n\n{user_content}\n\nRewritten text:",
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_predict": max(64, min(512, len(text_bounded.split()) * 3))
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "FlowPilot/LocalLLM"},
                method="POST"
            )
            with _SECURE_LOCAL_OPENER.open(req, timeout=remaining) as resp:
                if time.monotonic() > deadline:
                    return None
                if resp.status == 200:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    out = res_data.get("response", "").strip()
                    if out and time.monotonic() <= deadline:
                        logger.info(f"[LocalLLM] Generated transform via Ollama ({model})")
                        return self._clean_llm_output(out)
        except Exception:
            pass

        # 2. Try OpenAI-compatible /v1/chat/completions (LM Studio, llama.cpp, Ollama)
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0.05:
                return None

            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.2,
                "max_tokens": max(64, min(512, len(text_bounded.split()) * 3))
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "FlowPilot/LocalLLM"},
                method="POST"
            )
            with _SECURE_LOCAL_OPENER.open(req, timeout=remaining) as resp:
                if time.monotonic() > deadline:
                    return None
                if resp.status == 200:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    choices = res_data.get("choices", [])
                    if choices:
                        out = choices[0].get("message", {}).get("content", "").strip()
                        if out and time.monotonic() <= deadline:
                            logger.info(f"[LocalLLM] Generated transform via OpenAI endpoint ({model})")
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
