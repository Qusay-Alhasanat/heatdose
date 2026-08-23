# agent/core.py
"""
The agent's tool-calling loop: turns one natural-language question into
zero or more tool calls and a final grounded answer.

Integration point (Agent_Brief.md section 0): api/main.py's
agent_query() stub calls run_agent(request.question) and returns the
result in AgentQueryResponse's shape. That one-line swap is the only
change api/ needs — nothing here reaches into api/ or data/ beyond the
tool wrappers in agent/tools.py.

Guardrails enforced here, not just requested in the system prompt
(PROJECT_SPEC.md section 7 / Agent_Brief.md section 3):
  - Step limit: 5 tool calls per query, hard stop.
  - Timeout: 30s wall-clock per query.
  - Full tracing: every tool call, its arguments, and its result are
    returned alongside the answer, in api/models.py's ToolTraceEntry
    shape ({"tool": ..., "args": ..., "result": ...}).
"""

from __future__ import annotations

import json
import os
import time

from dotenv import load_dotenv
from openai import APITimeoutError, OpenAI, OpenAIError

load_dotenv()

try:
    from prompts import SYSTEM_PROMPT
    from tools import TOOL_SCHEMAS, call_tool
except ModuleNotFoundError:  # pragma: no cover
    from agent.prompts import SYSTEM_PROMPT
    from agent.tools import TOOL_SCHEMAS, call_tool

MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
MAX_TOOL_CALLS = 5
TIMEOUT_SECONDS = 30.0

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Lazy singleton so importing this module never requires an API key
    (e.g. running agent/tools.py's own tests)."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client


def run_agent(question: str) -> tuple[str, list[dict]]:
    """
    Answers one operations-manager question, calling tools as needed.

    Args:
        question: free-text question from the manager.

    Returns:
        (answer, tool_trace) where tool_trace is an ordered list of
        {"tool": str, "args": dict, "result": ...} — one entry per tool
        call actually executed, in call order.
    """
    client = _get_client()
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_trace: list[dict] = []
    tool_calls_made = 0
    start = time.monotonic()

    while True:
        remaining = TIMEOUT_SECONDS - (time.monotonic() - start)
        if remaining <= 0:
            return _timeout_answer(tool_trace), tool_trace

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                timeout=remaining,
            )
        except APITimeoutError:
            return _timeout_answer(tool_trace), tool_trace
        except OpenAIError as exc:
            return (
                f"I hit an error calling the language model and can't "
                f"answer right now ({exc}).",
                tool_trace,
            )

        choice = response.choices[0].message

        if not choice.tool_calls:
            return choice.content or "", tool_trace

        messages.append(
            {
                "role": "assistant",
                "content": choice.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.tool_calls
                ],
            }
        )

        limit_hit = False
        for tc in choice.tool_calls:
            if tool_calls_made >= MAX_TOOL_CALLS:
                limit_hit = True
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(
                            {"error": "Step limit reached (5 tool calls). Not executed."}
                        ),
                    }
                )
                continue

            args = _parse_arguments(tc.function.arguments)
            result = call_tool(tc.function.name, args)
            tool_trace.append({"tool": tc.function.name, "args": args, "result": result})
            tool_calls_made += 1

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                }
            )

        if limit_hit or tool_calls_made >= MAX_TOOL_CALLS:
            return _step_limit_answer(client, messages, tool_trace)


def _parse_arguments(raw: str) -> dict:
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {}


def _step_limit_answer(
    client: OpenAI, messages: list[dict], tool_trace: list[dict]
) -> tuple[str, list[dict]]:
    """
    Hard stop at the 5-tool-call limit. One final tool-free turn lets the
    model summarize what it already gathered instead of returning a bare
    canned string, while guaranteeing no further tool calls happen.
    """
    messages.append(
        {
            "role": "system",
            "content": (
                "You have reached the 5-tool-call limit for this query. Do "
                "not request any more tools. Answer now using only the "
                "information already gathered above. If that isn't enough "
                "to fully answer, say so plainly rather than guessing."
            ),
        }
    )
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tool_choice="none", timeout=10
        )
        content = response.choices[0].message.content or ""
    except OpenAIError:
        content = (
            "I reached the 5-tool-call limit for this question before I "
            "could finish answering. Here's what I checked before stopping: "
            + "; ".join(f"{t['tool']}({t['args']})" for t in tool_trace)
        )
    return content, tool_trace


def _timeout_answer(tool_trace: list[dict]) -> str:
    if tool_trace:
        checked = "; ".join(f"{t['tool']}({t['args']})" for t in tool_trace)
        return (
            f"This query took too long (30s limit) and was stopped before "
            f"finishing. Here's what was checked before the timeout: {checked}"
        )
    return "This query took too long (30s limit) and was stopped before any results came back."


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "Who is at risk right now?"
    answer, trace = run_agent(question)

    print(f"Q: {question}\n")
    print(f"A: {answer}\n")
    print(f"Tool calls ({len(trace)}):")
    for t in trace:
        print(f"  {t['tool']}({t['args']}) -> {t['result']}")
