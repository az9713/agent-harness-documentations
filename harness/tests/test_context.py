"""
Feature: Context compaction and dynamic retrieval (Best Practice #5)

Tests cover:
- build_context: message structure without / with compact summary
- build_context: state JSON is embedded in the first user message
- should_compact: returns False for small state, True when over 80% threshold
- should_compact: includes compact_summary in the token estimate
- Message sequence is a valid alternating user/assistant/user pattern
"""
import pytest

from context import COMPACTION_THRESHOLD, CONTEXT_WINDOW_TOKENS, build_context, should_compact


def minimal_state(task="do x"):
    return {"task": task, "status": "in_progress", "completed_steps": [], "plan": []}


class TestBuildContextWithoutSummary:
    def test_returns_single_message(self):
        messages = build_context(minimal_state(), None)
        assert len(messages) == 1

    def test_first_message_is_user(self):
        messages = build_context(minimal_state(), None)
        assert messages[0]["role"] == "user"

    def test_task_is_embedded_in_content(self):
        messages = build_context(minimal_state("write a haiku"), None)
        assert "write a haiku" in messages[0]["content"]

    def test_completed_steps_are_embedded(self):
        state = minimal_state()
        state["completed_steps"] = ["wrote foo.py"]
        messages = build_context(state, None)
        assert "wrote foo.py" in messages[0]["content"]

    def test_instructs_agent_to_say_task_complete(self):
        messages = build_context(minimal_state(), None)
        assert "TASK COMPLETE" in messages[0]["content"]


class TestBuildContextWithSummary:
    def test_returns_three_messages(self):
        messages = build_context(minimal_state(), "I wrote foo.py earlier")
        assert len(messages) == 3

    def test_alternating_roles(self):
        messages = build_context(minimal_state(), "summary")
        roles = [m["role"] for m in messages]
        assert roles == ["user", "assistant", "user"]

    def test_summary_appears_in_assistant_message(self):
        messages = build_context(minimal_state(), "I completed step 1")
        assert "I completed step 1" in messages[1]["content"]

    def test_state_appears_in_first_user_message(self):
        state = minimal_state("important task")
        messages = build_context(state, "some summary")
        assert "important task" in messages[0]["content"]


class TestShouldCompact:
    def test_false_for_tiny_state(self):
        assert should_compact(minimal_state(), None) is False

    def test_true_when_state_exceeds_threshold(self):
        # Need chars > CONTEXT_WINDOW_TOKENS * COMPACTION_THRESHOLD * CHARS_PER_TOKEN
        # = 180_000 * 0.8 * 4 = 576_000 chars
        big_state = minimal_state("x" * 600_000)
        assert should_compact(big_state, None) is True

    def test_false_just_below_threshold(self):
        # 180_000 * 0.8 * 4 = 576_000; use 200_000 chars → well below
        state = minimal_state("x" * 200_000)
        assert should_compact(state, None) is False

    def test_includes_summary_in_estimate(self):
        # State alone is fine; state + large summary pushes over
        state = minimal_state("x" * 300_000)
        big_summary = "y" * 300_000
        assert should_compact(state, big_summary) is True

    def test_no_summary_vs_summary_difference(self):
        # With a very large summary a previously fine state should compact
        state = minimal_state("x" * 300_000)
        assert should_compact(state, None) is False
        assert should_compact(state, "y" * 300_000) is True
