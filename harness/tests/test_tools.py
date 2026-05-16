"""
Feature: 5 core tools with routing-logic descriptions (Best Practice #4 — Minimal tool set)

Tests cover:
- read_file: happy path, missing file, directory target
- write_file: creates file, creates parent dirs, overwrites
- run_shell: stdout captured, stderr captured, timeout enforced
- list_files: hides dotfiles by default, shows them on request, missing dir
- execute_tool: unknown tool returns error string (never raises)
"""
from pathlib import Path

import pytest

from tools import execute_tool


class TestReadFile:
    def test_returns_file_contents(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world", encoding="utf-8")
        result = execute_tool("read_file", {"path": str(f)})
        assert result == "hello world"

    def test_error_on_missing_file(self, tmp_path):
        result = execute_tool("read_file", {"path": str(tmp_path / "nope.txt")})
        assert result.startswith("Error")

    def test_error_on_directory_target(self, tmp_path):
        result = execute_tool("read_file", {"path": str(tmp_path)})
        assert result.startswith("Error")

    def test_reads_utf8_content(self, tmp_path):
        f = tmp_path / "unicode.txt"
        f.write_text("héllo wörld", encoding="utf-8")
        result = execute_tool("read_file", {"path": str(f)})
        assert "héllo" in result


class TestWriteFile:
    def test_creates_file_with_content(self, tmp_path):
        path = str(tmp_path / "out.txt")
        execute_tool("write_file", {"path": path, "content": "my content"})
        assert Path(path).read_text(encoding="utf-8") == "my content"

    def test_returns_confirmation_message(self, tmp_path):
        path = str(tmp_path / "out.txt")
        result = execute_tool("write_file", {"path": path, "content": "hi"})
        assert "Wrote" in result

    def test_creates_parent_directories(self, tmp_path):
        path = str(tmp_path / "a" / "b" / "deep.txt")
        execute_tool("write_file", {"path": path, "content": "nested"})
        assert Path(path).exists()

    def test_overwrites_existing_file(self, tmp_path):
        path = str(tmp_path / "file.txt")
        Path(path).write_text("old", encoding="utf-8")
        execute_tool("write_file", {"path": path, "content": "new"})
        assert Path(path).read_text(encoding="utf-8") == "new"


class TestRunShell:
    def test_captures_stdout(self):
        result = execute_tool("run_shell", {"command": "python -c \"print('hello')\"" })
        assert "hello" in result

    def test_captures_stderr(self):
        result = execute_tool("run_shell", {
            "command": "python -c \"import sys; sys.stderr.write('err_output')\"",
        })
        assert "err_output" in result

    def test_timeout_returns_error(self):
        result = execute_tool("run_shell", {
            "command": "python -c \"import time; time.sleep(10)\"",
            "timeout": 1,
        })
        assert "timed out" in result

    def test_empty_output_returns_placeholder(self):
        result = execute_tool("run_shell", {"command": "python -c \"pass\""})
        assert result  # not empty string


class TestListFiles:
    def test_lists_files_and_dirs(self, tmp_path):
        (tmp_path / "alpha.txt").write_text("a")
        (tmp_path / "beta.txt").write_text("b")
        result = execute_tool("list_files", {"directory": str(tmp_path)})
        assert "alpha.txt" in result
        assert "beta.txt" in result

    def test_hides_dotfiles_by_default(self, tmp_path):
        (tmp_path / ".hidden").write_text("h")
        (tmp_path / "visible.txt").write_text("v")
        result = execute_tool("list_files", {"directory": str(tmp_path)})
        assert ".hidden" not in result
        assert "visible.txt" in result

    def test_shows_dotfiles_when_requested(self, tmp_path):
        (tmp_path / ".hidden").write_text("h")
        result = execute_tool("list_files", {"directory": str(tmp_path), "show_hidden": True})
        assert ".hidden" in result

    def test_labels_dirs_and_files(self, tmp_path):
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("f")
        result = execute_tool("list_files", {"directory": str(tmp_path)})
        assert "dir" in result
        assert "file" in result

    def test_error_on_missing_directory(self, tmp_path):
        result = execute_tool("list_files", {"directory": str(tmp_path / "nope")})
        assert result.startswith("Error")

    def test_empty_directory_message(self, tmp_path):
        subdir = tmp_path / "empty"
        subdir.mkdir()
        result = execute_tool("list_files", {"directory": str(subdir)})
        assert "empty" in result.lower()


class TestExecuteToolDispatch:
    def test_unknown_tool_returns_error_string(self):
        result = execute_tool("totally_fake_tool", {"arg": "val"})
        assert result.startswith("Error")

    def test_unknown_tool_never_raises(self):
        # Must return a string, never raise — agent loop depends on this
        result = execute_tool("unknown", {})
        assert isinstance(result, str)
