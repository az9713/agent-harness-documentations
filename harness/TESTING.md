# Testing Guide — Agent Harness

This guide walks through every layer of testing for the harness, from fast unit tests (no API key needed) to live end-to-end runs with a real model.

---

## Prerequisites

**Python 3.11 or later**

```bash
python --version   # must be 3.11+
```

**Install dependencies**

```bash
pip install anthropic httpx pytest
```

**Verify installation**

```bash
pytest --version   # should print pytest 7.x or 8.x
```

---

## Part 1 — Automated Unit Tests (No API Key Required)

The test suite covers all five harness modules using mocked model clients. You do not need an `ANTHROPIC_API_KEY` to run these.

### Step 1 — Run the full suite

From the repo root:

```bash
python -m pytest harness/tests/ -v
```

Expected output:

```
collected 78 items

harness/tests/test_agent.py::TestBasicResponse::test_returns_text PASSED
harness/tests/test_agent.py::TestBasicResponse::test_done_is_true_on_task_complete PASSED
...
78 passed in ~12s
```

All 78 tests should pass. If any fail, see [Troubleshooting](#troubleshooting) below.

### Step 2 — Run a single module's tests

Each file targets one harness feature:

```bash
# Session state and resume
python -m pytest harness/tests/test_session.py -v

# 5 core tools
python -m pytest harness/tests/test_tools.py -v

# Context compaction
python -m pytest harness/tests/test_context.py -v

# Generator/critic verifier
python -m pytest harness/tests/test_verifier.py -v

# Brain loop (agent.py)
python -m pytest harness/tests/test_agent.py -v
```

### Step 3 — Run a specific test by name

```bash
python -m pytest harness/tests/test_tools.py::TestWriteFile::test_creates_parent_directories -v
```

### Step 4 — Run tests matching a keyword

```bash
python -m pytest harness/tests/ -k "compact" -v   # all compaction tests
python -m pytest harness/tests/ -k "shell" -v     # all shell-check tests
```

### Step 5 — Check what each test covers

```bash
python -m pytest harness/tests/ --collect-only -q
```

---

## Part 2 — What Each Test File Covers

### `test_session.py` — Externalize all state (Best Practice #1)

Tests that session state survives process restarts and the log is truly append-only.

| Class | What it verifies |
|---|---|
| `TestLoadSession` | Returns `None` when no file exists; returns saved state when it does |
| `TestCreateSession` | Creates `session.json` with correct initial fields |
| `TestSaveSession` | Mutations persist; `last_updated` timestamp changes; status change persists |
| `TestAppendLog` | Creates log file on first write; each line is valid JSON; never overwrites |
| `TestReadLog` | Returns `[]` when no file; returns all entries in order; `last_n` slicing works |

### `test_tools.py` — Minimal tool set (Best Practice #4)

Tests each of the 5 tools in isolation using a real (temporary) filesystem.

| Class | What it verifies |
|---|---|
| `TestReadFile` | Happy path; error on missing file; error on directory target; UTF-8 support |
| `TestWriteFile` | Creates file; returns confirmation; creates parent dirs; overwrites existing |
| `TestRunShell` | Captures stdout; captures stderr; enforces timeout; handles empty output |
| `TestListFiles` | Lists entries; hides dotfiles by default; shows them on request; labels dirs vs files |
| `TestExecuteToolDispatch` | Unknown tool returns error string; never raises an exception |

### `test_context.py` — Context compaction (Best Practice #5)

Tests that context is built correctly and compaction triggers at the right threshold.

| Class | What it verifies |
|---|---|
| `TestBuildContextWithoutSummary` | Single user message; task embedded; instructs agent to say "TASK COMPLETE" |
| `TestBuildContextWithSummary` | Three messages in user/assistant/user order; summary in assistant message |
| `TestShouldCompact` | False for small state; true when over 80% threshold; summary counted in estimate |

### `test_verifier.py` — Generator/critic separation (Best Practice #3)

Tests that the critic is always independent — shell exit code beats model self-report.

| Class | What it verifies |
|---|---|
| `TestShellCheckPath` | Exit 0 → done; exit 1 → not done; failure output surfaced; model never called |
| `TestModelPath` | VERIFIED prefix → done; NOT DONE → not done; ambiguous → not done; task + completion text passed to model |

### `test_agent.py` — Brain loop (Best Practice #2)

Tests the model call + multi-round tool dispatch without making real API calls.

| Class | What it verifies |
|---|---|
| `TestBasicResponse` | Text returned; done=False normally; done=True on TASK COMPLETE; case-insensitive |
| `TestToolExecution` | Tool actually runs; recorded in result; results fed back to model; multiple rounds work |
| `TestObservability` | Log entry written every turn; has type, decision, done_claimed, tools_called fields |
| `TestRobustness` | A failing tool call returns an error string — never crashes the loop |

---

## Part 3 — Manual Feature Tests (API Key Required)

These verify the harness end-to-end with a real model. Set your key first:

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Test A — Basic task completion

```bash
python harness/run.py \
  --task "List all .md files in the current directory and write their names to file_list.txt" \
  --work-dir ./test_work_a
```

**What to check:**
- `file_list.txt` is created and contains `.md` filenames
- `test_work_a/session.json` shows `"status": "done"`
- `test_work_a/session.log` has at least one entry with `"done_claimed": true`

**Cleanup:**
```bash
Remove-Item -Recurse -Force test_work_a, file_list.txt
```

---

### Test B — Resume after interruption (Best Practice #1)

Start a longer task, interrupt it, then re-run to verify it resumes.

```bash
# Start the task
python harness/run.py \
  --task "Read report.md and write a 200-word summary to exec_summary.md" \
  --work-dir ./test_work_b
# Press Ctrl+C after the first or second turn

# Check that partial state was saved
type test_work_b\session.json

# Resume — should print "Resuming session: N steps done"
python harness/run.py \
  --task "Read report.md and write a 200-word summary to exec_summary.md" \
  --work-dir ./test_work_b
```

**What to check:**
- Second run prints `Resuming session:` not `New session:`
- `exec_summary.md` is created on completion

**Cleanup:**
```bash
Remove-Item -Recurse -Force test_work_b, exec_summary.md
```

---

### Test C — Shell-check verifier overrides model (Best Practice #3)

This verifies that the critic uses exit code as ground truth, not the model's opinion.

```bash
python harness/run.py \
  --task "Write a file called add.py containing a function add(a, b) that returns a + b" \
  --shell-check "python -c \"import add; assert add.add(2, 3) == 5; print('ok')\"" \
  --work-dir ./test_work_c
```

**What to check:**
- `add.py` is created with a correct `add` function
- `test_work_c/session.log` contains a `"type": "verification"` entry with `"passed": true`
- If you manually break `add.py` and re-run, the shell check fails and the loop continues

**Cleanup:**
```bash
Remove-Item -Recurse -Force test_work_c, add.py
```

---

### Test D — Session log observability (Best Practice #10)

Run any task and inspect the decision log.

```bash
python harness/run.py \
  --task "Write hello world to hello.txt" \
  --work-dir ./test_work_d

# Inspect the log
type test_work_d\session.log
```

**What to check:**
Each line in `session.log` is a JSON object containing:
- `"type"` — either `"turn"` or `"verification"`
- `"decision"` — what the agent decided to do
- `"tools_called"` — list of tools used with inputs and results
- `"done_claimed"` — whether the agent said it was done
- `"timestamp"` — ISO timestamp

**Cleanup:**
```bash
Remove-Item -Recurse -Force test_work_d, hello.txt
```

---

### Test E — Task from a file

```bash
# Create a task file
Set-Content -Path task.md -Value "Count the number of lines in report.md and write the result to line_count.txt"

python harness/run.py --task-file task.md --work-dir ./test_work_e
```

**What to check:**
- `line_count.txt` contains a number
- That number matches: `(Get-Content report.md).Count`

**Cleanup:**
```bash
Remove-Item -Recurse -Force test_work_e, task.md, line_count.txt
```

---

## Part 4 — Testing Individual Modules in Isolation

You can import and call any module directly from a Python REPL for quick experiments.

### session.py

```python
import sys; sys.path.insert(0, "harness")
from session import create_session, append_log, read_log, load_session

s = create_session("./tmp_session", "test task")
append_log("./tmp_session", {"type": "turn", "decision": "did something"})
print(load_session("./tmp_session"))
print(read_log("./tmp_session"))
```

### tools.py

```python
import sys; sys.path.insert(0, "harness")
from tools import execute_tool

print(execute_tool("list_files", {"directory": "."}))
print(execute_tool("run_shell", {"command": "python --version"}))
print(execute_tool("read_file", {"path": "README.md"})[:200])
```

### context.py

```python
import sys; sys.path.insert(0, "harness")
from context import build_context, should_compact

state = {"task": "do x", "status": "in_progress", "completed_steps": [], "plan": []}
msgs = build_context(state, None)
print(f"Messages: {len(msgs)}, roles: {[m['role'] for m in msgs]}")
print(f"Should compact: {should_compact(state, None)}")
```

### verifier.py (shell-check path, no API key)

```python
import sys; sys.path.insert(0, "harness")
from unittest.mock import MagicMock
from verifier import verify

client = MagicMock()  # not called when shell_check is provided
is_done, reason = verify(client, "model", "task", "done", shell_check='python -c "exit(0)"')
print(f"Done: {is_done}, Reason: {reason}")
```

---

## Part 5 — Troubleshooting

### `ModuleNotFoundError: No module named 'session'`

Run pytest from the repo root, not from inside `harness/`:

```bash
# Correct
cd C:\Users\simon\Downloads\harness_docs\agent-harness-documentations
python -m pytest harness/tests/ -v

# Wrong — don't do this
cd harness && pytest tests/
```

### `ModuleNotFoundError: No module named 'anthropic'`

```bash
pip install anthropic httpx
```

### A test fails unexpectedly

Run just that test with verbose output and show local variables:

```bash
python -m pytest harness/tests/test_tools.py::TestRunShell::test_timeout_returns_error -v -l
```

### Shell commands behave differently on Windows

Tests use `python -c "..."` for cross-platform compatibility. If you see shell test failures, confirm Python is on your PATH:

```bash
python --version
```

### `ANTHROPIC_API_KEY` not set (Part 3 tests only)

```bash
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # PowerShell
```

The automated tests in Part 1 and Part 2 never need this key.

---

## Quick Reference

| What to test | Command |
|---|---|
| Full automated suite | `python -m pytest harness/tests/ -v` |
| Single module | `python -m pytest harness/tests/test_session.py -v` |
| Single test | `python -m pytest harness/tests/test_tools.py::TestWriteFile -v` |
| By keyword | `python -m pytest harness/tests/ -k "compact" -v` |
| List all tests | `python -m pytest harness/tests/ --collect-only -q` |
| Basic live run | `python harness/run.py --task "..." --work-dir ./work` |
| With shell verification | `python harness/run.py --task "..." --shell-check "pytest"` |
| Resume a session | Re-run the same command with the same `--work-dir` |
