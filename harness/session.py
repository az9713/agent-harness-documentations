"""Session state and append-only log management."""
import json
from datetime import datetime, timezone
from pathlib import Path

SESSION_FILE = "session.json"
LOG_FILE = "session.log"


def load_session(work_dir: str) -> dict | None:
    path = Path(work_dir) / SESSION_FILE
    if path.exists():
        return json.loads(path.read_text())
    return None


def create_session(work_dir: str, task: str) -> dict:
    state = {
        "task": task,
        "status": "in_progress",
        "plan": [],
        "completed_steps": [],
        "failed_attempts": [],
        "known_issues": [],
        "last_updated": _now(),
    }
    save_session(work_dir, state)
    return state


def save_session(work_dir: str, state: dict) -> None:
    state["last_updated"] = _now()
    path = Path(work_dir) / SESSION_FILE
    path.write_text(json.dumps(state, indent=2))


def append_log(work_dir: str, entry: dict) -> None:
    entry["timestamp"] = _now()
    path = Path(work_dir) / LOG_FILE
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_log(work_dir: str, last_n: int | None = None) -> list[dict]:
    path = Path(work_dir) / LOG_FILE
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    if last_n is not None:
        entries = entries[-last_n:]
    return entries


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
