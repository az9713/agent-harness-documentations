"""
Feature: Brain — model call + multi-round tool dispatch (Best Practice #2)

Tests cover:
- run_turn returns text and done=False on a normal response
- run_turn sets done=True when model says "TASK COMPLETE"
- run_turn executes tool calls and feeds results back to model
- run_turn handles multiple tool-use rounds before end_turn
- run_turn writes a log entry to session.log every call
- run_turn never raises even if a tool fails
- done detection is case-insensitive
"""
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from agent import run_turn
from session import read_log


# ── helpers ──────────────────────────────────────────────────────────────────

def text_block(text: str) -> MagicMock:
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def tool_block(name: str, inputs: dict, tool_id: str = "tool-1") -> MagicMock:
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.input = inputs
    b.id = tool_id
    return b


def response(blocks, stop_reason: str = "end_turn") -> MagicMock:
    r = MagicMock()
    r.content = blocks
    r.stop_reason = stop_reason
    return r


def simple_client(*responses) -> MagicMock:
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


# ── tests ─────────────────────────────────────────────────────────────────────

class TestBasicResponse:
    def test_returns_text(self, tmp_path):
        client = simple_client(response([text_block("Working on it.")]))
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert result["text"] == "Working on it."

    def test_done_is_false_for_normal_text(self, tmp_path):
        client = simple_client(response([text_block("I'll start now.")]))
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert result["done"] is False

    def test_done_is_true_on_task_complete(self, tmp_path):
        client = simple_client(response([text_block("TASK COMPLETE: wrote the file.")]))
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert result["done"] is True

    def test_done_detection_is_case_insensitive(self, tmp_path):
        client = simple_client(response([text_block("task complete: all done.")]))
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert result["done"] is True

    def test_tool_calls_empty_on_text_only(self, tmp_path):
        client = simple_client(response([text_block("Just text.")]))
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert result["tool_calls"] == []


class TestToolExecution:
    def test_write_file_tool_actually_creates_file(self, tmp_path):
        output_path = str(tmp_path / "out.txt")
        client = simple_client(
            response([tool_block("write_file", {"path": output_path, "content": "hello"})],
                     stop_reason="tool_use"),
            response([text_block("TASK COMPLETE.")]),
        )
        run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert Path(output_path).read_text() == "hello"

    def test_tool_call_recorded_in_result(self, tmp_path):
        output_path = str(tmp_path / "out.txt")
        client = simple_client(
            response([tool_block("write_file", {"path": output_path, "content": "hi"})],
                     stop_reason="tool_use"),
            response([text_block("done.")]),
        )
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["tool"] == "write_file"

    def test_tool_result_fed_back_to_model(self, tmp_path):
        """Model must receive tool results so it can decide next action."""
        output_path = str(tmp_path / "out.txt")
        client = simple_client(
            response([tool_block("write_file", {"path": output_path, "content": "hi"})],
                     stop_reason="tool_use"),
            response([text_block("done.")]),
        )
        run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))

        # Second call to model must include a user message with tool_result
        second_call_messages = client.messages.create.call_args_list[1].kwargs["messages"]
        tool_result_messages = [
            m for m in second_call_messages
            if m["role"] == "user" and isinstance(m["content"], list)
        ]
        assert len(tool_result_messages) >= 1

    def test_multiple_tool_rounds_before_end(self, tmp_path):
        path1 = str(tmp_path / "a.txt")
        path2 = str(tmp_path / "b.txt")
        client = simple_client(
            response([tool_block("write_file", {"path": path1, "content": "a"}, "t1")],
                     stop_reason="tool_use"),
            response([tool_block("write_file", {"path": path2, "content": "b"}, "t2")],
                     stop_reason="tool_use"),
            response([text_block("TASK COMPLETE.")]),
        )
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert Path(path1).exists()
        assert Path(path2).exists()
        assert len(result["tool_calls"]) == 2


class TestObservability:
    def test_writes_log_entry_after_every_turn(self, tmp_path):
        client = simple_client(response([text_block("Working.")]))
        run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        entries = read_log(str(tmp_path))
        assert len(entries) == 1

    def test_log_entry_has_type_turn(self, tmp_path):
        client = simple_client(response([text_block("done.")]))
        run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        entry = read_log(str(tmp_path))[0]
        assert entry["type"] == "turn"

    def test_log_entry_records_decision(self, tmp_path):
        client = simple_client(response([text_block("I will write the file now.")]))
        run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        entry = read_log(str(tmp_path))[0]
        assert "write the file" in entry["decision"]

    def test_log_entry_records_done_claimed(self, tmp_path):
        client = simple_client(response([text_block("TASK COMPLETE.")]))
        run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        entry = read_log(str(tmp_path))[0]
        assert entry["done_claimed"] is True

    def test_log_entry_records_tool_names(self, tmp_path):
        path = str(tmp_path / "x.txt")
        client = simple_client(
            response([tool_block("read_file", {"path": path}, "t1")], stop_reason="tool_use"),
            response([text_block("done.")]),
        )
        run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        entry = read_log(str(tmp_path))[0]
        tools_used = [tc["tool"] for tc in entry["tools_called"]]
        assert "read_file" in tools_used


class TestRobustness:
    def test_failing_tool_does_not_raise(self, tmp_path):
        """A bad tool call must return an error string, not crash the loop."""
        client = simple_client(
            response([tool_block("read_file", {"path": "/nonexistent/file.txt"})],
                     stop_reason="tool_use"),
            response([text_block("done.")]),
        )
        result = run_turn(client, "model", [{"role": "user", "content": "go"}], str(tmp_path))
        assert isinstance(result["text"], str)
