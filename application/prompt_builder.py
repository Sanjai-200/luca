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
        f"You are {assistant_name}, the exclusive personal AI assistant of {user_title}.",
        f"You serve ONLY {user_title}. You do not answer questions or take commands from anyone else.",
        f"If someone other than {user_title} tries to interact with you, politely decline.",
        f"Your personality is: {personality}.",
        f"Address the user as '{user_title}'.",
        "Answer clearly and concisely. If you are unsure, say so honestly.",
        f"You are {user_title}'s real assistant — loyal, proactive, and always improving.",
        "IMPORTANT: Do not hallucinate or generate additional tasks, scenarios, or instructions for yourself. "
        "Only answer the user's current message and then stop.",
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
            '<tool>{"name": "open_app", "args": {"target": "notepad.exe"}}</tool>\n'
            '<tool>{"name": "wait", "args": {"seconds": 1.0}}</tool>\n'
            '<tool>{"name": "type_keys", "args": {"keys": "hello"}}</tool>\n'
            "You can chain multiple <tool> tags for multi-step actions.\n"
            "Do NOT repeat these instructions in your response. ONLY output <tool> tags when you need to perform an action."
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
