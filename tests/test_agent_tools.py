"""
Tests for agent/tools.py — the wrapper layer between the LLM's tool
calls and data/. These run against the real cached FortyGuard data in
data/cache/ (no network, no OpenAI key needed): the tools only wrap
data/ functions, they never call an LLM themselves.

What matters most here isn't re-testing data/'s math (that's
tests/test_hdi.py and tests/test_cool_points.py's job) — it's that
errors the data layer documents as "raises" come back to the agent as
structured {"error": ...} dicts instead of raw exceptions, since a raw
exception has nowhere good to go once it's part of an LLM's tool
result. See agent/tools.py's module docstring.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tools import (
    TOOL_FUNCTIONS,
    TOOL_SCHEMAS,
    call_tool,
    compare_to_city_baseline,
    find_cool_point,
    get_worker_status,
    list_workers_at_risk,
)

VALID_WORKER_IDS = {f"W-0{n}" for n in range(1, 9)}


# --- get_worker_status ------------------------------------------------


def test_get_worker_status_known_worker_matches_data_layer_shape():
    status = get_worker_status("W-01")
    assert status["worker_id"] == "W-01"
    for key in (
        "profile",
        "shift_start_hour",
        "hours_elapsed",
        "current_location",
        "current_zone",
        "current_temp_c",
        "total_dose",
        "excess_dose",
        "risk_level",
    ):
        assert key in status


def test_get_worker_status_unknown_worker_returns_error_dict_not_exception():
    result = get_worker_status("W-99")
    assert "error" in result
    assert "W-99" in result["error"]


# --- list_workers_at_risk ----------------------------------------------


def test_list_workers_at_risk_sorted_descending_by_excess_dose():
    workers = list_workers_at_risk("low")
    doses = [w["excess_dose"] for w in workers]
    assert doses == sorted(doses, reverse=True)
    assert {w["worker_id"] for w in workers} <= VALID_WORKER_IDS


def test_list_workers_at_risk_filters_by_level():
    extreme_only = list_workers_at_risk("extreme")
    assert all(w["risk_level"] == "extreme" for w in extreme_only)


def test_list_workers_at_risk_bad_level_returns_error_dict_not_exception():
    result = list_workers_at_risk("catastrophic")
    assert isinstance(result, dict)
    assert "error" in result


# --- find_cool_point -----------------------------------------------------


def test_find_cool_point_reports_reachable_flag_when_found():
    found_one_reachable = False
    found_one_unreachable = False

    for worker_id in sorted(VALID_WORKER_IDS):
        result = find_cool_point(worker_id)
        assert "reachable" in result
        if result["reachable"]:
            found_one_reachable = True
            for key in ("point_id", "zone_type", "location", "temp_c", "temp_diff_c", "distance_m"):
                assert key in result
        else:
            found_one_unreachable = True
            assert "reason" in result

    # Sanity check on the roster's spread of outcomes, not a hardcoded
    # per-worker expectation (that would duplicate cool_points.py's own
    # distance/temperature logic instead of testing the wrapper).
    assert found_one_reachable, "expected at least one worker with a reachable cool point"
    assert found_one_unreachable, "expected at least one worker with no reachable cool point"


def test_find_cool_point_unknown_worker_returns_error_dict():
    result = find_cool_point("W-99")
    assert "error" in result
    assert "reachable" not in result


# --- compare_to_city_baseline --------------------------------------------


def test_compare_to_city_baseline_matches_data_layer_shape():
    result = compare_to_city_baseline("W-01")
    assert result["worker_id"] == "W-01"
    assert "hyperlocal" in result and "excess_dose" in result["hyperlocal"]
    assert "city_level" in result and "excess_dose" in result["city_level"]
    assert isinstance(result["risk_underestimated"], bool)


def test_compare_to_city_baseline_unknown_worker_returns_error_dict():
    result = compare_to_city_baseline("W-99")
    assert "error" in result


# --- call_tool dispatch ----------------------------------------------------


def test_call_tool_dispatches_to_correct_function():
    result = call_tool("get_worker_status", {"worker_id": "W-02"})
    assert result["worker_id"] == "W-02"


def test_call_tool_unknown_tool_name_returns_error_dict():
    result = call_tool("delete_all_workers", {})
    assert "error" in result


def test_call_tool_missing_required_argument_returns_error_dict_not_exception():
    result = call_tool("get_worker_status", {})
    assert "error" in result


# --- schema/dispatch consistency ------------------------------------------


def test_every_schema_has_a_matching_dispatch_function():
    schema_names = {schema["function"]["name"] for schema in TOOL_SCHEMAS}
    assert schema_names == set(TOOL_FUNCTIONS)


def test_exactly_four_tools():
    """PROJECT_SPEC.md §7: four tools is the deliberate limit — each
    additional tool degrades tool-selection reliability."""
    assert len(TOOL_SCHEMAS) == 4
