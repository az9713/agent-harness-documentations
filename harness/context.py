"""Context compaction — triggers at 80% of context window. (Best Practice #5)"""
import json

CHARS_PER_TOKEN = 4
CONTEXT_WINDOW_TOKENS = 180_000  # claude-sonnet-4-6
COMPACTION_THRESHOLD = 0.80

COMPACTION_PROMPT = (
    "Summarize this agent work history concisely.\n"
    "Keep: decisions made, steps completed, current plan, known issues, failed approaches.\n"
    "Discard: raw file contents, redundant tool outputs, error traces already resolved.\n\n"
    "<log>\n{log_text}\n</log>"
)


def build_context(state: dict, compact_summary: str | None) -> list[dict]:
    """Return the initial messages list for the next agent turn."""
    state_text = json.dumps(state, indent=2)

    if compact_summary:
        return [
            {
                "role": "user",
                "content": (
                    f"<session_state>\n{state_text}\n</session_state>\n\n"
                    "Review this session state and the summary of your prior work, then continue."
                ),
            },
            {
                "role": "assistant",
                "content": (
                    f"Summary of prior work:\n\n{compact_summary}\n\n"
                    "I'll continue working on the task."
                ),
            },
            {
                "role": "user",
                "content": "Continue. When the task is fully done, say 'TASK COMPLETE' followed by a brief summary.",
            },
        ]
    else:
        return [
            {
                "role": "user",
                "content": (
                    f"<session_state>\n{state_text}\n</session_state>\n\n"
                    "Work on this task using the available tools. "
                    "When fully done, say 'TASK COMPLETE' followed by a brief summary."
                ),
            },
        ]


def should_compact(state: dict, compact_summary: str | None) -> bool:
    context = build_context(state, compact_summary)
    total_chars = sum(len(str(m.get("content", ""))) for m in context)
    estimated_tokens = total_chars // CHARS_PER_TOKEN
    return estimated_tokens > CONTEXT_WINDOW_TOKENS * COMPACTION_THRESHOLD


def compact(client, work_dir: str, model: str) -> str:
    from session import read_log
    entries = read_log(work_dir, last_n=50)
    log_text = json.dumps(entries, indent=2)
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": COMPACTION_PROMPT.format(log_text=log_text),
        }],
    )
    return response.content[0].text
