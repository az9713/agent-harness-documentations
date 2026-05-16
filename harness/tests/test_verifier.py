"""
Feature: Generator/Critic separation — critic never lets agent grade its own work
(Best Practice #3)

Tests cover:
- Shell check exit 0 → verified done (ground truth overrides model)
- Shell check exit 1 → not done
- Shell check captures and surfaces failure output
- Shell check takes precedence: model client is never called when shell_check provided
- Model-based path: VERIFIED response → done=True
- Model-based path: NOT DONE response → done=False
- Model is called with task + completion text so it can evaluate independently
"""
import pytest
from unittest.mock import MagicMock

from verifier import verify


def mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = mock_resp
    return client


class TestShellCheckPath:
    def test_exit_0_returns_done_true(self):
        client = MagicMock()
        is_done, reason = verify(client, "model", "task", "done text",
                                 shell_check='python -c "exit(0)"')
        assert is_done is True

    def test_exit_0_reason_mentions_passed(self):
        client = MagicMock()
        _, reason = verify(client, "model", "task", "done text",
                           shell_check='python -c "exit(0)"')
        assert "passed" in reason.lower()

    def test_exit_1_returns_done_false(self):
        client = MagicMock()
        is_done, _ = verify(client, "model", "task", "done text",
                            shell_check='python -c "exit(1)"')
        assert is_done is False

    def test_exit_1_reason_mentions_failed(self):
        client = MagicMock()
        _, reason = verify(client, "model", "task", "done text",
                           shell_check='python -c "exit(1)"')
        assert "failed" in reason.lower()

    def test_shell_check_captures_failure_output(self):
        client = MagicMock()
        _, reason = verify(client, "model", "task", "done",
                           shell_check='python -c "import sys; sys.stdout.write(\'fail_msg\'); exit(1)"')
        assert "fail_msg" in reason

    def test_shell_check_model_never_called(self):
        """Ground truth: shell exit code beats model opinion every time."""
        client = MagicMock()
        verify(client, "model", "task", "text",
               shell_check='python -c "exit(0)"')
        client.messages.create.assert_not_called()


class TestModelPath:
    def test_verified_prefix_returns_done_true(self):
        client = mock_client("VERIFIED: The file exists and contains the function.")
        is_done, _ = verify(client, "model", "write a fn", "TASK COMPLETE")
        assert is_done is True

    def test_not_done_prefix_returns_done_false(self):
        client = mock_client("NOT DONE: output.py is missing.")
        is_done, _ = verify(client, "model", "write a fn", "TASK COMPLETE")
        assert is_done is False

    def test_ambiguous_response_returns_done_false(self):
        client = mock_client("I cannot determine if this is complete.")
        is_done, _ = verify(client, "model", "task", "done")
        assert is_done is False

    def test_reason_is_the_model_response(self):
        client = mock_client("VERIFIED: All tests pass.")
        _, reason = verify(client, "model", "task", "done")
        assert "All tests pass" in reason

    def test_model_called_with_task_and_completion_text(self):
        """Verifier must pass task + completion text so model can evaluate independently."""
        client = mock_client("NOT DONE: missing steps.")
        verify(client, "model", "my unique task", "my unique completion")
        call_args = client.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert "my unique task" in prompt
        assert "my unique completion" in prompt

    def test_no_shell_check_uses_model(self):
        client = mock_client("VERIFIED: done.")
        verify(client, "model", "task", "completion text", shell_check=None)
        client.messages.create.assert_called_once()
