# agent/tools.py
"""
The four tools the agent may call, plus their OpenAI function-calling
schemas (TOOL_SCHEMAS) and a single dispatch entry point (call_tool()).

Per docs/data_contract.md's ownership table: this file reads
worker_status.py / cool_points.py / baseline.py output and never talks
to fortyguard_client.py or the FortyGuard API directly.

Every wrapper here catches the data layer's documented exceptions and
turns them into a plain {"error": "..."} dict instead of letting them
propagate. That's deliberate: the result of a tool call becomes part of
the LLM's context (serialized to JSON), so a raw exception has nowhere
good to go. The system prompt (agent/prompts.py) tells the model that an
"error" key means the tool could not answer — not a number to report.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# agent/ sits one level below repo root, same as tests/ — this mirrors
# tests/test_hdi.py's convention so `python agent/tools.py` works
# directly, without requiring data/ to already be on sys.path the way
# data/*.py's own sibling-import try/except assumes.
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.cool_points import find_nearest_cool_point
from data.mock_data import WORKER_ROSTER, generate_mock_shift
from data.real_shift_builder import MissingRealDataError, attach_real_temperatures
from data.baseline import compare_worker
from data.worker_status import UnknownWorkerError
from data.worker_status import get_worker_status as _get_worker_status
from data.worker_status import list_workers_at_risk as _list_workers_at_risk


def get_worker_status(worker_id: str) -> dict:
    """Tool 1 — full status for one worker. See data/worker_status.py."""
    try:
        return _get_worker_status(worker_id)
    except UnknownWorkerError as exc:
        return {"error": str(exc)}
    except MissingRealDataError as exc:
        return {"error": f"Internal data error, not a normal 'unavailable' case: {exc}"}


def list_workers_at_risk(min_level: str = "high") -> list[dict] | dict:
    """Tool 2 — every worker at or above min_level, highest risk first."""
    try:
        return _list_workers_at_risk(min_level)
    except ValueError as exc:
        return {"error": str(exc)}
    except MissingRealDataError as exc:
        return {"error": f"Internal data error, not a normal 'unavailable' case: {exc}"}


def find_cool_point(worker_id: str) -> dict:
    """
    Tool 3 — nearest reachable cool spot for a worker's CURRENT location
    and hour.

    Design note: the underlying data/cool_points.find_nearest_cool_point()
    takes raw worker_location/worker_current_temp_c/hour, per
    Agent_Brief.md's "call this right after get_worker_status()". Rather
    than exposing those raw fields to the LLM (which would have to
    invent or copy coordinates — a fabrication risk this project
    explicitly guards against), this wrapper does that chaining itself:
    it looks the worker up, derives the current hour from
    shift_start_hour + hours_elapsed (one shift point per hour, see
    mock_data.generate_mock_shift()'s default interval_hours=1), and
    calls the real function with real values.

    Returns:
        On success: the find_nearest_cool_point() dict, with
        "reachable": True added.
        If nothing qualifies: {"reachable": False, "reason": "..."} —
        this is Agent_Brief.md's documented valid outcome (a worker in
        an exposed zone may genuinely have nowhere better to go), not
        an error.
    """
    status = get_worker_status(worker_id)
    if "error" in status:
        return status

    hour = status["shift_start_hour"] + status["hours_elapsed"]
    result = find_nearest_cool_point(
        worker_location=status["current_location"],
        worker_current_temp_c=status["current_temp_c"],
        hour=hour,
    )

    if result is None:
        return {
            "reachable": False,
            "reason": (
                "No candidate point is both at least 3C cooler and within "
                "800m walking distance of this worker's current location."
            ),
        }

    return {"reachable": True, **result}


def compare_to_city_baseline(worker_id: str) -> dict:
    """
    Tool 4 — hyperlocal continuous tracking vs. a single-morning-check
    baseline for one worker. See data/baseline.compare_worker().

    Reconstructs the worker's real-temperature shift exactly as
    Agent_Brief.md section 2 (Tool 4) specifies, since compare_worker()
    takes a full shift, not a worker_id.
    """
    if worker_id not in WORKER_ROSTER:
        return {
            "error": (
                f"Unknown worker_id: {worker_id!r}. "
                f"Known workers: {sorted(WORKER_ROSTER)}"
            )
        }

    config = WORKER_ROSTER[worker_id]
    mock_shift = generate_mock_shift(
        worker_id, route_profile=config["profile"], start_hour=config["start_hour"]
    )

    try:
        real_shift = attach_real_temperatures(mock_shift)
    except MissingRealDataError as exc:
        return {"error": f"Internal data error, not a normal 'unavailable' case: {exc}"}

    return compare_worker(real_shift)


TOOL_FUNCTIONS = {
    "get_worker_status": get_worker_status,
    "list_workers_at_risk": list_workers_at_risk,
    "find_cool_point": find_cool_point,
    "compare_to_city_baseline": compare_to_city_baseline,
}


def call_tool(name: str, arguments: dict) -> Any:
    """Single dispatch point — agent/core.py never calls a tool function directly."""
    if name not in TOOL_FUNCTIONS:
        return {"error": f"Unknown tool: {name!r}. Available: {sorted(TOOL_FUNCTIONS)}"}
    try:
        return TOOL_FUNCTIONS[name](**arguments)
    except TypeError as exc:
        return {"error": f"Invalid arguments for {name}: {exc}"}


# --------------------------------------------------------------------
# OpenAI function-calling schemas — JSON Schema per
# https://platform.openai.com/docs/guides/function-calling
# --------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_worker_status",
            "description": (
                "Get full current status for one worker: location, zone, "
                "temperature, accumulated heat dose, and risk level. Use "
                "this whenever the manager asks about a specific worker by ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "worker_id": {
                        "type": "string",
                        "description": "Worker identifier, e.g. 'W-01' through 'W-08'.",
                    }
                },
                "required": ["worker_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_workers_at_risk",
            "description": (
                "List every worker at or above a given risk level, sorted "
                "by excess heat dose descending (worst first). Use this for "
                "questions like 'who should I pull right now?' or 'show me "
                "everyone at high risk.'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "min_level": {
                        "type": "string",
                        "enum": ["low", "moderate", "high", "extreme"],
                        "description": (
                            "Minimum risk band to include. Defaults to "
                            "'high' if omitted."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_cool_point",
            "description": (
                "Find the nearest reachable cool/shaded spot for a worker's "
                "current location and hour, if one exists. May report that "
                "nothing is reachable — that is a valid, expected outcome, "
                "not an error."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "worker_id": {
                        "type": "string",
                        "description": "Worker identifier, e.g. 'W-01' through 'W-08'.",
                    }
                },
                "required": ["worker_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_to_city_baseline",
            "description": (
                "Compare a worker's real, continuously tracked heat exposure "
                "against what a single check-in at shift start would have "
                "shown. Use this to answer questions about whether standard "
                "weather monitoring would have missed this worker's risk. "
                "This is a TIME comparison (one check vs. continuous "
                "tracking), not a location/spatial comparison."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "worker_id": {
                        "type": "string",
                        "description": "Worker identifier, e.g. 'W-01' through 'W-08'.",
                    }
                },
                "required": ["worker_id"],
            },
        },
    },
]


if __name__ == "__main__":
    print("=== get_worker_status('W-01') ===")
    print(get_worker_status("W-01"))

    print("\n=== get_worker_status('W-99') [expect error] ===")
    print(get_worker_status("W-99"))

    print("\n=== find_cool_point('W-01') ===")
    print(find_cool_point("W-01"))

    print("\n=== compare_to_city_baseline('W-01') ===")
    print(compare_to_city_baseline("W-01"))
