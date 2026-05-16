"""Critic: checks completion claims. Never lets the agent grade its own work. (Best Practice #3)"""
import subprocess

_VERIFY_PROMPT = """\
The agent has claimed the task is complete.

Task:
{task}

Agent's completion statement:
{completion_text}

Evaluate whether the task is truly complete:
1. Is there verifiable evidence that each part of the task has been accomplished?
2. Are there obvious gaps, errors, or unmet requirements?

Respond with exactly one of:
  VERIFIED: <one sentence of evidence>
  NOT DONE: <what is still missing or wrong>
"""


def verify(
    client,
    model: str,
    task: str,
    completion_text: str,
    shell_check: str | None = None,
) -> tuple[bool, str]:
    """
    Return (is_done, reason).

    If shell_check is provided, exit code 0 is treated as ground truth —
    this takes precedence over the model's own assessment.
    """
    if shell_check:
        result = subprocess.run(
            shell_check, shell=True, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return True, f"Shell check passed: {shell_check}"
        output = (result.stdout + result.stderr).strip()
        return False, f"Shell check failed (exit {result.returncode}): {output[:300]}"

    prompt = _VERIFY_PROMPT.format(task=task, completion_text=completion_text)
    response = client.messages.create(
        model=model,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response.content[0].text.strip()
    is_done = answer.upper().startswith("VERIFIED")
    return is_done, answer
