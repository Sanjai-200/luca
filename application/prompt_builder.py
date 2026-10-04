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

        parts.append(
            'To perform an action on the computer, output a JSON block wrapped in <tool> tags.\n\n'
            'ACTION EXAMPLES:\n'
            '- Open application or website:\n'
            '  <tool>{"name": "open_app", "args": {"target": "notepad.exe"}}</tool>\n'
            '  <tool>{"name": "open_app", "args": {"target": "https://www.google.com/search?q=what+is+database"}}</tool>\n'
            '  <tool>{"name": "open_app", "args": {"target": "explorer"}}</tool>\n'
            '- Close application:\n'
            '  <tool>{"name": "close_app", "args": {"target": "notepad"}}</tool>\n'
            '- Create folders, files, or run commands:\n'
            '  <tool>{"name": "run_shell", "args": {"command": "New-Item -ItemType Directory -Path \'D:\\\\AAA\' -Force"}}</tool>\n'
            '  <tool>{"name": "run_shell", "args": {"command": "New-Item -ItemType File -Path \'helle.py\' -Force"}}</tool>\n'
            '- Type keys:\n'
            '  <tool>{"name": "type_keys", "args": {"keys": "hello"}}</tool>\n\n'
            "CRITICAL RULES:\n"
            "1. For general conversation, questions, or greetings, reply directly with normal text. DO NOT use tools.\n"
            "2. When asked to perform an action on the computer, you MUST output the actual <tool> tags. NEVER just describe what you are doing in text without the <tool> tags. If you only write text, nothing will happen.\n"
            "3. First give a brief friendly response acknowledging the task (e.g. 'I will execute the task for you, Boss. Please wait a moment...' or 'On it, Boss!'), followed immediately by the <tool> tags.\n"
            "4. Output <tool> tags directly. DO NOT wrap <tool> tags in markdown code fences.\n"
            "5. You can chain multiple <tool> tags if a task requires multiple steps."
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
