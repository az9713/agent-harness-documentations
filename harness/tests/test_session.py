"""
Feature: Session state and append-only log (Best Practice #1 — Externalize all state)

Tests cover:
- Creating, saving, and loading session state
- Append-only log (never overwrites, adds timestamp automatically)
- last_n slicing on read_log
- Resume behaviour: load_session returns None when no file exists
"""
import json
import time
from pathlib import Path

import pytest

from session import append_log, create_session, load_session, read_log, save_session


class TestLoadSession:
    def test_returns_none_when_no_file_exists(self, tmp_path):
        assert load_session(str(tmp_path)) is None

    def test_returns_state_when_file_exists(self, tmp_path):
        create_session(str(tmp_path), "my task")
        state = load_session(str(tmp_path))
        assert state is not None
        assert state["task"] == "my task"


class TestCreateSession:
    def test_writes_session_json(self, tmp_path):
        create_session(str(tmp_path), "do something")
        assert (tmp_path / "session.json").exists()

    def test_initial_fields(self, tmp_path):
        state = create_session(str(tmp_path), "do something")
        assert state["task"] == "do something"
        assert state["status"] == "in_progress"
        assert state["plan"] == []
        assert state["completed_steps"] == []
        assert state["failed_attempts"] == []
        assert state["known_issues"] == []
        assert "last_updated" in state

    def test_file_is_valid_json(self, tmp_path):
        create_session(str(tmp_path), "task")
        raw = (tmp_path / "session.json").read_text()
        parsed = json.loads(raw)
        assert parsed["task"] == "task"


class TestSaveSession:
    def test_persists_mutations(self, tmp_path):
        state = create_session(str(tmp_path), "task")
        state["completed_steps"].append("step 1")
        save_session(str(tmp_path), state)

        loaded = load_session(str(tmp_path))
        assert loaded["completed_steps"] == ["step 1"]

    def test_updates_last_updated_timestamp(self, tmp_path):
        state = create_session(str(tmp_path), "task")
        original_ts = state["last_updated"]
        time.sleep(0.05)
        save_session(str(tmp_path), state)
        loaded = load_session(str(tmp_path))
        assert loaded["last_updated"] >= original_ts

    def test_status_change_is_persisted(self, tmp_path):
        state = create_session(str(tmp_path), "task")
        state["status"] = "done"
        save_session(str(tmp_path), state)
        assert load_session(str(tmp_path))["status"] == "done"


class TestAppendLog:
    def test_creates_log_file_on_first_write(self, tmp_path):
        append_log(str(tmp_path), {"msg": "hello"})
        assert (tmp_path / "session.log").exists()

    def test_each_line_is_valid_json(self, tmp_path):
        append_log(str(tmp_path), {"x": 1})
        append_log(str(tmp_path), {"x": 2})
        lines = (tmp_path / "session.log").read_text().strip().splitlines()
        for line in lines:
            json.loads(line)  # must not raise

    def test_appends_without_overwriting(self, tmp_path):
        append_log(str(tmp_path), {"x": 1})
        append_log(str(tmp_path), {"x": 2})
        entries = read_log(str(tmp_path))
        assert len(entries) == 2

    def test_adds_timestamp_automatically(self, tmp_path):
        append_log(str(tmp_path), {"type": "turn"})
        entries = read_log(str(tmp_path))
        assert "timestamp" in entries[0]

    def test_preserves_original_fields(self, tmp_path):
        append_log(str(tmp_path), {"type": "verification", "passed": True})
        entry = read_log(str(tmp_path))[0]
        assert entry["type"] == "verification"
        assert entry["passed"] is True


class TestReadLog:
    def test_returns_empty_list_when_no_file(self, tmp_path):
        assert read_log(str(tmp_path)) == []

    def test_returns_all_entries_in_order(self, tmp_path):
        for i in range(4):
            append_log(str(tmp_path), {"i": i})
        entries = read_log(str(tmp_path))
        assert [e["i"] for e in entries] == [0, 1, 2, 3]

    def test_last_n_returns_tail(self, tmp_path):
        for i in range(5):
            append_log(str(tmp_path), {"i": i})
        entries = read_log(str(tmp_path), last_n=3)
        assert len(entries) == 3
        assert entries[0]["i"] == 2
        assert entries[2]["i"] == 4

    def test_last_n_larger_than_log_returns_all(self, tmp_path):
        append_log(str(tmp_path), {"i": 0})
        entries = read_log(str(tmp_path), last_n=100)
        assert len(entries) == 1
