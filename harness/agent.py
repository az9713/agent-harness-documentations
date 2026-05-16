"""Brain: model call + tool dispatch loop. (Best Practice #2)"""
from tools import TOOL_DEFINITIONS, execute_tool
from session import append_log

SYSTEM_PROMPT = """\
You are a general-purpose AI agent. You complete tasks step by step using the tools available.

Rules:
- Read the session state at the start to understand what has been done and what remains.
- Work one step at a time. After each tool call, decide what to do next.
- When you have fully completed the task, say "TASK COMPLETE" followed by a brief summary of what you did.
- Do not claim completion unless you have verified your work (e.g., read back the file you wrote, ran the tests).
- If you encounter an error, record it as a failed attempt and try an alternative approach.
- Prefer read_file over run_shell for reading files. Prefer specific tools over run_shell when possible.
"""

MAX_TOOL_ROUNDS = 20


def run_turn(client, model: str, messages: list[dict], work_dir: str) -> dict:
    """
    Run one full agent turn, including all tool call rounds, until end_turn.

    Returns:
        text: str — final text output from the model
        tool_calls: list — all tool calls made this turn (for logging)
        messages: list — updated messages including tool results (for inspection)
        done: bool — whether the agent claimed task completion
    """
    messages = list(messages)
    all_tool_calls = []
    final_text = ""

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        text_parts = []
        tool_use_blocks = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_use_blocks.append(block)

        final_text = "\n".join(text_parts)

        if response.stop_reason == "end_turn" or not tool_use_blocks:
            break

        # Execute all tool calls and feed results back
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in tool_use_blocks:
            inputs = block.input if isinstance(block.input, dict) else {}
            result = execute_tool(block.name, inputs)
            log_result = result[:500] + "…" if len(result) > 500 else result
            all_tool_calls.append({"tool": block.name, "input": inputs, "result": log_result})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    done = "TASK COMPLETE" in final_text.upper()

    append_log(work_dir, {
        "type": "turn",
        "decision": final_text[:300] if final_text else "(tool calls only)",
        "tools_called": all_tool_calls,
        "done_claimed": done,
    })

    return {
        "text": final_text,
        "tool_calls": all_tool_calls,
        "messages": messages,
        "done": done,
    }
