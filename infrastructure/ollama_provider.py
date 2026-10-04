"""Ollama AI Provider — infrastructure implementation of AIProvider.

This module contains ONLY the HTTP transport logic for talking to Ollama.
It implements the core.interfaces.AIProvider contract.
No business logic, no prompt building, no tool parsing lives here.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Iterator

from core.interfaces import AIProvider, LLMResponse, Message
from core.exceptions import AIProviderError, AIProviderUnavailableError

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """Ollama local LLM provider.

    Communicates with the Ollama HTTP API using only stdlib (no external deps).
    Supports both blocking generation and real-time streaming.
    """

    _DEFAULT_STOP = ["<|end|>", "<|user|>", "<|bot|>", "<|assistant|>", "<|endoftext|>", "Boss>"]

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "phi3:mini",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        timeout: int = 60,
    ) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    # ── AIProvider contract ───────────────────────────────────────────

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Ping Ollama to check connectivity."""
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    def generate(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a complete response (blocking)."""
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "keep_alive": -1,
            "options": {
                "temperature": temperature or self._temperature,
                "num_predict": max_tokens or self._max_tokens,
                "stop": self._DEFAULT_STOP,
            },
        }
        try:
            data = self._post("/api/chat", payload)
            content = data.get("message", {}).get("content", "")
            return LLMResponse(
                content=content,
                model=self._model,
                tokens_used=data.get("eval_count", 0),
            )
        except Exception as exc:
            raise AIProviderError(f"Ollama generate failed: {exc}") from exc

    def stream(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        """Stream response tokens one at a time."""
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "keep_alive": -1,
            "options": {
                "temperature": temperature or self._temperature,
                "num_predict": max_tokens or self._max_tokens,
                "stop": self._DEFAULT_STOP,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._host}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                for line in resp:
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except Exception as exc:
            raise AIProviderError(f"Ollama stream failed: {exc}") from exc

    # ── Internal HTTP ─────────────────────────────────────────────────

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to Ollama and return the parsed response."""
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._host}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise AIProviderUnavailableError("ollama") from exc
