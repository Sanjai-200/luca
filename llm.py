"""Luca LLM provider system.

Contains:
  - Message / LLMResponse            — data model
  - LLMProvider                      — abstract interface (all backends implement this)
  - OllamaProvider                   — concrete Ollama backend (stdlib only, no pip deps)
  - system_prompt / task_system_prompt — centralised prompt templates
"""

from __future__ import annotations

import abc
import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Iterator

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Data model
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Message:
    role: str   # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw: Any = None


# ═══════════════════════════════════════════════════════════════════════
#  Abstract provider
# ═══════════════════════════════════════════════════════════════════════

class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate(self, messages: list[Message], *, temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse: ...

    def stream(self, messages: list[Message], *, temperature: float | None = None,
               max_tokens: int | None = None) -> Iterator[str]:
        yield self.generate(messages, temperature=temperature, max_tokens=max_tokens).content

    @abc.abstractmethod
    def is_available(self) -> bool: ...

    @property
    @abc.abstractmethod
    def name(self) -> str: ...


# ═══════════════════════════════════════════════════════════════════════
#  Ollama provider (uses only stdlib — zero pip deps)
# ═══════════════════════════════════════════════════════════════════════

class OllamaProvider(LLMProvider):
    def __init__(self, host: str, model: str, temperature: float = 0.7,
                 max_tokens: int = 1024, timeout: int = 60) -> None:
        self._host = host.rstrip("/")
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "Ollama"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5):
                return True
        except Exception:
            return False

    def generate(self, messages: list[Message], *, temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "keep_alive": -1,
            "options": {"temperature": temperature or self._temperature,
                        "num_predict": max_tokens or self._max_tokens},
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{self._host}/api/chat", data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read())
            return LLMResponse(content=body.get("message", {}).get("content", ""),
                               model=body.get("model", self._model), raw=body)
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama unavailable: {exc}") from exc

    def stream(self, messages: list[Message], *, temperature: float | None = None,
               max_tokens: int | None = None) -> Iterator[str]:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "keep_alive": -1,
            "options": {"temperature": temperature or self._temperature,
                        "num_predict": max_tokens or self._max_tokens},
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{self._host}/api/chat", data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                for line in resp:
                    if line.strip():
                        token = json.loads(line).get("message", {}).get("content", "")
                        if token:
                            yield token
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ollama unavailable: {exc}") from exc


# ═══════════════════════════════════════════════════════════════════════
#  Prompt templates
# ═══════════════════════════════════════════════════════════════════════

def system_prompt(assistant_name: str, user_title: str, personality: str,
                  *, learned_rules: str = "", memory_context: str = "", tool_instructions: str = "") -> str:
    """Build the core system prompt with identity, rules, context, and tools."""
    parts = [
        f"You are {assistant_name}, the exclusive personal AI assistant of {user_title}.",
        f"You serve ONLY {user_title}. You do not answer questions or take commands from anyone else.",
        f"If someone other than {user_title} tries to interact with you, politely decline.",
        f"Your personality is: {personality}.",
        f"Address the user as '{user_title}'.",
        "Answer clearly and concisely. If you are unsure, say so honestly.",
        f"You are {user_title}'s real assistant — loyal, proactive, and always improving.",
        "IMPORTANT: Do not hallucinate or generate additional tasks, scenarios, or instructions for yourself. Only answer the user's current message and then stop."
    ]
    if tool_instructions:
        parts.append("")
        parts.append("--- CAPABILITIES ---")
        parts.append(tool_instructions)
    if learned_rules:
        parts.append("")
        parts.append(learned_rules)
    if memory_context:
        parts.append("")
        parts.append(f"Relevant context about {user_title}:")
        parts.append(memory_context)
    return "\n".join(parts)


def task_system_prompt(assistant_name: str, user_title: str) -> str:
    return (f"You are {assistant_name}, a desktop AI assistant. "
            f"The user is '{user_title}'. "
            f"You have access to tools. Respond with structured tool calls "
            f"when the user requests actions. Do not execute commands directly.")
