"""Prompt Builder — constructs system prompts with injected context and tool specs.

Single responsibility: build the system prompt string.
Does NOT generate responses, call LLMs, or parse tool outputs.
"""

from __future__ import annotations

from core.interfaces import ToolSpec


def build_system_prompt(
    assistant_name: str,
    user_title: str,
    personality: str,
    *,
    learned_rules: str = "",
    memory_context: str = "",
    tool_specs: list[ToolSpec] | None = None,
) -> str:
    """Build Luca's system prompt with all injected context.

    This is the single source of truth for how the system prompt is structured.
    """
    parts = [
        f"You are {assistant_name}, the personal AI assistant of {user_title}.",
        f"Your personality is: {personality}.",
        f"Address the user as '{user_title}'.",
        "Answer clearly and concisely. You can answer general knowledge questions, help with coding, and control the computer.",
        "IMPORTANT: Only answer the user's current message and then stop.",
    ]

    # Inject tool capabilities
    if tool_specs:
        parts.append("")
        parts.append("--- TOOLS ---")
        parts.append("You have access to the following tools:")
        for spec in tool_specs:
            params_str = ", ".join(
                f'"{k}": {v.get("type", "string")}' for k, v in spec.parameters.items()
            ) if spec.parameters else ""
            parts.append(f"- {spec.name}: {spec.description}")

        parts.append("")
        parts.append(
            'To use a tool, output a JSON block wrapped in <tool> tags. Example:\n'
            '<tool>{"name": "open_app", "args": {"target": "notepad.exe"}}</tool>\n\n'
            "CRITICAL RULES:\n"
            "1. ONLY use tools if the user EXPLICITLY asks you to perform an action on the computer.\n"
            "2. If the user just says hello or asks a question, reply with normal text. DO NOT open notepad to write your reply.\n"
            "3. You can chain multiple <tool> tags if needed."
        )

    # Inject learned rules
    if learned_rules:
        parts.append("")
        parts.append(learned_rules)

    # Inject relevant memory context
    if memory_context:
        parts.append("")
        parts.append(f"Relevant context about {user_title}:")
        parts.append(memory_context)

    return "\n".join(parts)
