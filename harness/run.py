#!/usr/bin/env python3
"""
Agent Harness — Stage 1 MVP (Ralph Loop)

Usage:
  python harness/run.py --task "Your task" [--work-dir ./work] [--shell-check "pytest"]
  python harness/run.py --task-file task.md --work-dir ./my_session
"""
import argparse
import os
import sys
from pathlib import Path

# Make harness/ importable when run as `python harness/run.py`
sys.path.insert(0, str(Path(__file__).parent))

import anthropic

from session import load_session, create_session, save_session, append_log
from context import build_context, should_compact, compact
from agent import run_turn
from verifier import verify

MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TURNS = 50


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Harness MVP")
    parser.add_argument("--task", help="Task description string")
    parser.add_argument("--task-file", help="Path to a file containing the task")
    parser.add_argument("--work-dir", default="./work", help="Session state directory (default: ./work)")
    parser.add_argument("--shell-check", help="Shell command to verify completion; exit 0 = done")
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    args = parser.parse_args()

    # Resolve task text
    if args.task:
        task = args.task
    elif args.task_file:
        task = Path(args.task_file).read_text(encoding="utf-8").strip()
    else:
        parser.error("Provide --task or --task-file")

    work_dir = args.work_dir
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    client = anthropic.Anthropic(api_key=api_key)

    # Load or create session — enables resume after interruption (Best Practice #1)
    state = load_session(work_dir)
    if state and state.get("status") == "done":
        print("Session already marked done. Delete session.json to re-run.")
        return
    if state:
        print(f"Resuming session: {len(state['completed_steps'])} steps done")
    else:
        state = create_session(work_dir, task)
        print(f"New session: {task[:80]}...")

    compact_summary: str | None = None

    # Ralph Loop — outer verification loop (Best Practice #3)
    for turn_num in range(1, args.max_turns + 1):
        print(f"\n--- Turn {turn_num} ---")

        # Compact if approaching context limit (Best Practice #5)
        if should_compact(state, compact_summary):
            print("Compacting context history...")
            compact_summary = compact(client, work_dir, MODEL)
            print(f"Summary: {compact_summary[:100]}...")

        # Build fresh context from state + summary, run agent
        messages = build_context(state, compact_summary)
        result = run_turn(client, MODEL, messages, work_dir)

        # Print progress
        text_preview = result["text"][:160] + "..." if len(result["text"]) > 160 else result["text"]
        print(f"Agent: {text_preview or '(tool calls)'}")
        for tc in result["tool_calls"]:
            keys = list(tc["input"].keys())
            out = str(tc["result"])[:80]
            print(f"  [{tc['tool']}({keys})] → {out}")

        # Track tool-driven progress in state
        for tc in result["tool_calls"]:
            if tc["tool"] == "write_file":
                step = f"wrote {tc['input'].get('path', '?')}"
                if step not in state["completed_steps"]:
                    state["completed_steps"].append(step)
        save_session(work_dir, state)

        # Verify completion claims (Best Practice #3 — critic is always external)
        if result["done"]:
            is_done, reason = verify(
                client, MODEL,
                task=state["task"],
                completion_text=result["text"],
                shell_check=args.shell_check,
            )
            append_log(work_dir, {"type": "verification", "passed": is_done, "reason": reason})
            print(f"Verifier: {reason}")

            if is_done:
                state["status"] = "done"
                save_session(work_dir, state)
                print(f"\nDone after {turn_num} turn(s).")
                print(f"Session log: {work_dir}/session.log")
                return

            print("Verifier rejected — continuing...")

    print(f"\nReached max turns ({args.max_turns}). Session saved to {work_dir}/")
    print("Re-run the same command to continue from where it stopped.")
    sys.exit(1)


if __name__ == "__main__":
    main()
