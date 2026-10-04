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
        f"Address the user as '{user_title}'. ALWAYS call the user '{user_title}'. NEVER use any other name.",
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
            '- Search YouTube or Google:\n'
            '  <tool>{"name": "search_web", "args": {"query": "foods", "site": "youtube"}}</tool>\n'
            '  <tool>{"name": "search_web", "args": {"query": "what is database", "site": "google"}}</tool>\n'
            '- Open application, file, or website:\n'
            '  <tool>{"name": "open_app", "args": {"target": "notepad.exe"}}</tool>\n'
            '  <tool>{"name": "open_app", "args": {"target": "code D:\\\\PASS\\\\print_hi.py"}}</tool>\n'
            '  <tool>{"name": "open_app", "args": {"target": "explorer"}}</tool>\n'
            '- Close application:\n'
            '  <tool>{"name": "close_app", "args": {"target": "notepad"}}</tool>\n'
            '- Create directory, create file, or write file content:\n'
            '  <tool>{"name": "run_shell", "args": {"command": "New-Item -ItemType Directory -Path \'D:\\\\AAA\' -Force"}}</tool>\n'
            '  <tool>{"name": "run_shell", "args": {"command": "Set-Content -Path \'D:\\\\PASS\\\\print_hi.py\' -Value \'print(\\\"Hi\\\")\'"}}</tool>\n'
            '- Type keys into active GUI window:\n'
            '  <tool>{"name": "type_keys", "args": {"keys": "hello"}}</tool>\n'
            '- Press special key (enter, tab, esc, space, up, down):\n'
            '  <tool>{"name": "press_key", "args": {"key": "enter"}}</tool>\n\n'
            "CRITICAL RULES:\n"
            "1. For general conversation, questions, or greetings, reply directly with normal text. DO NOT use tools.\n"
            "2. When asked to perform an action on the computer, you MUST output the actual <tool> tags. NEVER just describe what you are doing in text without the <tool> tags. If you only write text, nothing will happen.\n"
            "3. ONLY use tools that are registered above. NEVER invent or hallucinate non-existent tools (e.g. do not invent select_option).\n"
            "4. DO NOT use search_web unless the user explicitly asks you to search for something on Google or YouTube.\n"
            "5. To write code or text into a file, ALWAYS use run_shell with Set-Content. DO NOT use type_keys to write files.\n"
            "6. First give a brief friendly response acknowledging the task (e.g. 'I will execute the task for you, Boss. Please wait a moment...' or 'On it, Boss!'), followed immediately by the <tool> tags.\n"
            "7. Output <tool> tags directly. DO NOT wrap <tool> tags in markdown code fences.\n"
            "8. You can chain multiple <tool> tags if a task requires multiple steps."
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
