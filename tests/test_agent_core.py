"""
Tests for agent/core.py's tool-calling loop, with the OpenAI client
replaced by a fake — these verify the loop mechanics (dispatch, tracing,
guardrail enforcement) without spending real API credit or requiring an
OPENAI_API_KEY. See PROJECT_SPEC.md section 7 / Agent_Brief.md section 3:
the step limit and full tracing are graded requirements, not incidental
behavior, so they get their own tests rather than relying on manual
inspection.
"""

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import agent.core as core


class _FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = types.SimpleNamespace(name=name, arguments=arguments)


class _FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _FakeCompletions:
    """Replays a fixed script of assistant messages, one per .create() call."""

    def __init__(self, script):
        self._script = script
        self.calls = 0

    def create(self, **kwargs):
        message = self._script[self.calls]
        self.calls += 1
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


class _FakeClient:
    def __init__(self, script):
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(script))


@pytest.fixture
def fake_client(monkeypatch):
    """Injects a scripted fake client via run_agent()'s lazy singleton."""

    def _install(script):
        client = _FakeClient(script)
        monkeypatch.setattr(core, "_client", client)
        return client

    return _install


def test_single_tool_call_then_final_answer(fake_client):
    fake_client(
        [
            _FakeMessage(
                tool_calls=[
                    _FakeToolCall("call_1", "get_worker_status", '{"worker_id": "W-01"}')
                ]
            ),
            _FakeMessage(content="W-01 is at extreme risk."),
        ]
    )

    answer, trace = core.run_agent("how is W-01 doing?")

    assert answer == "W-01 is at extreme risk."
    assert len(trace) == 1
    assert trace[0]["tool"] == "get_worker_status"
    assert trace[0]["args"] == {"worker_id": "W-01"}
    assert trace[0]["result"]["worker_id"] == "W-01"


def test_no_tool_calls_needed(fake_client):
    fake_client([_FakeMessage(content="I can't answer that without checking a worker ID.")])

    answer, trace = core.run_agent("what's the weather like in general?")

    assert trace == []
    assert "checking" in answer


def test_step_limit_stops_at_five_tool_calls(fake_client):
    """PROJECT_SPEC.md §7: step limit is 5, hard stop, clear message."""
    tool_round = _FakeMessage(
        tool_calls=[_FakeToolCall("call_x", "get_worker_status", '{"worker_id": "W-01"}')]
    )
    # 5 rounds that each request one more tool call, then the forced
    # tool-free wrap-up turn that fires once the limit is hit.
    fake_client([tool_round] * 5 + [_FakeMessage(content="Reached the limit.")])

    answer, trace = core.run_agent("check every worker one at a time forever")

    assert len(trace) == core.MAX_TOOL_CALLS == 5
    assert answer == "Reached the limit."


def test_unknown_worker_surfaces_as_tool_error_not_a_crash(fake_client):
    fake_client(
        [
            _FakeMessage(
                tool_calls=[
                    _FakeToolCall("call_1", "get_worker_status", '{"worker_id": "W-99"}')
                ]
            ),
            _FakeMessage(content="I don't recognize worker W-99."),
        ]
    )

    answer, trace = core.run_agent("how is W-99 doing?")

    assert "error" in trace[0]["result"]
    assert answer == "I don't recognize worker W-99."


def test_tool_trace_shape_matches_api_models_tool_trace_entry(fake_client):
    """Every entry must be exactly {tool, args, result} — api/models.py's
    ToolTraceEntry mirrors this shape and would reject anything else."""
    fake_client(
        [
            _FakeMessage(
                tool_calls=[
                    _FakeToolCall("call_1", "list_workers_at_risk", "{}")
                ]
            ),
            _FakeMessage(content="Here's who's at risk."),
        ]
    )

    _, trace = core.run_agent("who's at risk?")

    assert set(trace[0]) == {"tool", "args", "result"}
