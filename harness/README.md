# Agent Harness — Stage 1 MVP

A minimal general-purpose agent harness implementing the best practices from [`report.md`](../report.md).

For a step-by-step testing guide, see **[`TESTING.md`](TESTING.md)**.

## Setup

```bash
pip install anthropic httpx
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

```bash
# Simple task
python harness/run.py --task "Write a Python function that reverses a string, save it to output.py"

# Task from a file
python harness/run.py --task-file task.md --work-dir ./my_session

# With shell-based verification (exit 0 = done — overrides model self-report)
python harness/run.py --task "Fix all failing tests" --shell-check "pytest"

# Resume an interrupted session automatically (reads ./work/session.json)
python harness/run.py --task "same task text" --work-dir ./work
```

## Architecture

```
harness/
├── run.py          # Entry point + outer Ralph Loop
├── agent.py        # Brain: model call + tool dispatch
├── tools.py        # Hands: 5 core tools
├── session.py      # Session: JSON state + append-only log
├── verifier.py     # Critic: completion verification
└── context.py      # Context compaction
```

### The Loop

```
run.py (outer Ralph Loop):
  load or create session.json
  while not verified_done:
    compact context if > 80% of window  ← context.py
    build messages from state + summary ← context.py
    call model, execute tools           ← agent.py + tools.py
    update session.json                 ← session.py
    if agent claims done:
      verify externally                 ← verifier.py
```

## Session Files

Each run writes to `--work-dir` (default `./work`):

| File | Contents |
|---|---|
| `session.json` | Current task state — resumable if interrupted |
| `session.log` | Append-only JSONL — every turn, decision, and tool call |

## The 5 Tools

| Tool | Use when | Do NOT use when |
|---|---|---|
| `read_file` | Reading any file | Target is a directory |
| `write_file` | Creating or overwriting a file | You need to append |
| `run_shell` | Running commands, tests, builds | Command is interactive or long-running |
| `web_fetch` | Fetching a public URL | Page requires login |
| `list_files` | Listing a directory | You need a deep recursive tree |

## Best Practices Implemented

| Practice | Implementation |
|---|---|
| #1 Externalize state | `session.json` + `session.log` survive restarts |
| #2 Brain/hands/session split | `agent.py` / `tools.py` / `session.py` |
| #3 Generator/critic | `verifier.py` re-prompts independently; shell check overrides |
| #4 Minimal tool set | 5 tools with routing-logic descriptions |
| #5 Context compaction | Auto-triggered at 80% of context window |
| #10 Instrument decisions | Every turn logged: decision + tools + outcome |

## Adding a Tool

Edit `tools.py`:

1. Add an entry to `TOOL_DEFINITIONS`:
```python
{
    "name": "my_tool",
    "description": "What it does. Do not use when <X>.",
    "input_schema": {
        "type": "object",
        "properties": {"arg": {"type": "string", "description": "..."}},
        "required": ["arg"],
    },
}
```

2. Add a handler in `execute_tool()`:
```python
"my_tool": _my_tool,
```

3. Implement `_my_tool(inputs: dict) -> str`.

Keep descriptions as routing logic — always include a "Do not use when" line.

## Stage 2 Upgrade Path

When you outgrow Stage 1, the next additions are:
- **Durable execution**: Replace the Ralph Loop with LangGraph checkpointers
- **Multi-agent**: Add a supervisor that routes sub-tasks to specialized agents
- **Memory at scale**: Replace state files with a vector store + episodic memory
- **Security**: Add network allowlists, sandbox isolation, credential injection

See [`report.md`](../report.md) Part III for the full solution set.
