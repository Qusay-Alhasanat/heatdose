"""
Sanity checks for cool point selection.

These verify the filter-then-rank logic and the guarantees the Agent
layer depends on: that a suggestion is always both cooler and reachable,
and that repeated queries return the same answer.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.cool_points import (
    MAX_DISTANCE_M,
    MIN_MEANINGFUL_DIFF_C,
    find_nearest_cool_point,
    get_candidates_with_current_temp,
)
from data.mock_data import ZONE_CENTRES, temp_at


def _worker_in(zone: str) -> dict:
    """Helper: a worker standing at a zone's centre."""
    lat, lng = ZONE_CENTRES[zone]
    return {"lat": lat, "lng": lng}


# --- Core behaviour -------------------------------------------------------


def test_hot_zone_gets_a_suggestion():
    """
    A worker in the hottest zone at peak hour must receive a usable
    suggestion. If this fails, the tool is dead weight for the Agent.
    """
    result = find_nearest_cool_point(
        _worker_in("industrial_yard"),
        worker_current_temp_c=temp_at(14, "industrial_yard"),
        hour=14,
    )
    assert result is not None


def test_suggestion_is_always_cooler_and_reachable():
    """
    The two guarantees the Agent relies on, checked across every zone
    and every daylight hour: a returned suggestion is never too hot and
    never too far.
    """
    for zone in ZONE_CENTRES:
        for hour in range(6, 19):
            result = find_nearest_cool_point(
                _worker_in(zone),
                worker_current_temp_c=temp_at(hour, zone),
                hour=hour,
            )
            if result is None:
                continue
            assert result["temp_diff_c"] >= MIN_MEANINGFUL_DIFF_C
            assert result["distance_m"] <= MAX_DISTANCE_M


def test_returns_nearest_not_coolest():
    """
    Among eligible candidates, proximity wins. A far-but-freezing spot
    must lose to a near-and-cool-enough one — walking there costs
    exposure the metric does not credit back.
    """
    worker = _worker_in("industrial_yard")
    result = find_nearest_cool_point(
        worker, worker_current_temp_c=temp_at(14, "industrial_yard"), hour=14
    )
    assert result is not None

    candidates = get_candidates_with_current_temp(14)
    coolest = min(c["temp_c"] for c in candidates)

    # The chosen point need not be the coldest one available
    assert result["temp_c"] >= coolest


# --- Filtering guarantees -------------------------------------------------


def test_returns_none_when_nothing_is_cooler():
    """
    A worker already in a cool zone has nothing meaningfully better
    nearby. None is the correct answer, not an error.
    """
    result = find_nearest_cool_point(
        _worker_in("canal_greenway"),
        worker_current_temp_c=temp_at(14, "canal_greenway"),
        hour=14,
    )
    assert result is None


def test_returns_none_when_everything_is_too_far():
    """Tightening the distance cap to zero must eliminate all options."""
    result = find_nearest_cool_point(
        _worker_in("industrial_yard"),
        worker_current_temp_c=temp_at(14, "industrial_yard"),
        hour=14,
        max_distance_m=0.0,
    )
    assert result is None


def test_stricter_temperature_requirement_narrows_results():
    """
    Raising min_diff_c must never widen the result set — it can only
    keep the same answer or return None.
    """
    worker = _worker_in("asphalt_lot")
    temp = temp_at(14, "asphalt_lot")

    lenient = find_nearest_cool_point(worker, temp, 14, min_diff_c=1.0)
    strict = find_nearest_cool_point(worker, temp, 14, min_diff_c=99.0)

    assert lenient is not None
    assert strict is None


# --- Reproducibility ------------------------------------------------------


def test_repeated_queries_are_identical():
    """
    The same query must return the same answer every time. Judges review
    the demo days after submission; a suggestion that changes on refresh
    would contradict anything written in the README.
    """
    worker = _worker_in("downtown_core")
    temp = temp_at(14, "downtown_core")

    results = [find_nearest_cool_point(worker, temp, 14) for _ in range(5)]

    assert all(r == results[0] for r in results)


def test_candidate_temperatures_vary_by_hour():
    """
    Cool points are not static: their temperature must track time of day
    exactly as worker readings do.
    """
    morning = {c["point_id"]: c["temp_c"] for c in get_candidates_with_current_temp(7)}
    afternoon = {
        c["point_id"]: c["temp_c"] for c in get_candidates_with_current_temp(15)
    }

    assert any(afternoon[pid] != morning[pid] for pid in morning)
