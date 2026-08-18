"""
Sanity checks for the heat exposure calculations.

These verify internal consistency — that the math behaves as expected —
not medical validity of the metrics themselves. See docs/methodology.md
for what these numbers do and do not represent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from data.hdi import (
    SAFE_THRESHOLD_C,
    calculate_excess_dose,
    calculate_hdi,
    classify_risk,
)


def _point(timestamp: str, temp_c: float) -> dict:
    """Helper: builds one contract-compliant data point."""
    return {
        "worker_id": "TEST",
        "location": {"lat": 33.4484, "lng": -112.0740},
        "timestamp": timestamp,
        "temp_c": temp_c,
    }


# --- Total dose -----------------------------------------------------------


def test_constant_temperature_exact_value():
    """Standing still at 40C for 2 hours must equal exactly 80.0."""
    shift = [
        _point("2025-07-15T10:00:00", 40.0),
        _point("2025-07-15T12:00:00", 40.0),
    ]
    assert calculate_hdi(shift) == 80.0


def test_hotter_shift_scores_higher():
    """Same duration, higher temperature -> higher total dose."""
    cool = [
        _point("2025-07-15T10:00:00", 30.0),
        _point("2025-07-15T14:00:00", 30.0),
    ]
    hot = [
        _point("2025-07-15T10:00:00", 45.0),
        _point("2025-07-15T14:00:00", 45.0),
    ]
    assert calculate_hdi(hot) > calculate_hdi(cool)


def test_longer_shift_scores_higher():
    """Same temperature, longer duration -> higher total dose."""
    short = [
        _point("2025-07-15T10:00:00", 40.0),
        _point("2025-07-15T12:00:00", 40.0),
    ]
    long = [
        _point("2025-07-15T10:00:00", 40.0),
        _point("2025-07-15T16:00:00", 40.0),
    ]
    assert calculate_hdi(long) > calculate_hdi(short)


def test_single_point_returns_zero():
    """A shift with one reading has no elapsed time -> no dose."""
    assert calculate_hdi([_point("2025-07-15T10:00:00", 45.0)]) == 0.0


def test_empty_shift_returns_zero():
    """Defensive: empty input must not crash."""
    assert calculate_hdi([]) == 0.0


# --- Excess dose ----------------------------------------------------------


def test_excess_dose_exact_value():
    """
    Two hours at exactly 10C above the threshold must equal 20.0.
    Verifies the clamping subtraction is applied correctly.
    """
    temp = SAFE_THRESHOLD_C + 10.0
    shift = [
        _point("2025-07-15T10:00:00", temp),
        _point("2025-07-15T12:00:00", temp),
    ]
    assert calculate_excess_dose(shift) == 20.0


def test_excess_dose_ignores_safe_temperatures():
    """Time spent entirely below the threshold contributes nothing."""
    cool_shift = [
        _point("2025-07-15T06:00:00", 25.0),
        _point("2025-07-15T10:00:00", 28.0),
    ]
    assert calculate_excess_dose(cool_shift) == 0.0


def test_cool_time_does_not_offset_hot_time():
    """
    A cool reading must not subtract from accumulated excess.
    Exposure is monotonic — this guards against negative contributions
    if the max(0, ...) clamp is ever removed.
    """
    hot_only = [
        _point("2025-07-15T12:00:00", 45.0),
        _point("2025-07-15T14:00:00", 45.0),
    ]
    hot_then_cool = [
        _point("2025-07-15T12:00:00", 45.0),
        _point("2025-07-15T14:00:00", 45.0),
        _point("2025-07-15T16:00:00", 20.0),
    ]
    assert calculate_excess_dose(hot_then_cool) >= calculate_excess_dose(hot_only)


def test_excess_dose_separates_better_than_total():
    """
    The core justification for using excess dose in classification:
    it discriminates between exposure profiles more sharply than
    total dose does.
    """
    shaded = [
        _point("2025-07-15T09:00:00", 34.0),
        _point("2025-07-15T15:00:00", 34.0),
    ]
    exposed = [
        _point("2025-07-15T09:00:00", 44.0),
        _point("2025-07-15T15:00:00", 44.0),
    ]

    total_ratio = calculate_hdi(exposed) / calculate_hdi(shaded)
    excess_ratio = calculate_excess_dose(exposed) / calculate_excess_dose(shaded)

    assert excess_ratio > total_ratio


def test_excess_dose_empty_and_single_point():
    """Defensive: same edge-case guarantees as total dose."""
    assert calculate_excess_dose([]) == 0.0
    assert calculate_excess_dose([_point("2025-07-15T10:00:00", 45.0)]) == 0.0


# --- Risk classification --------------------------------------------------


def test_risk_levels_are_ordered():
    """Risk classification must escalate monotonically with excess dose."""
    assert classify_risk(10) == "low"
    assert classify_risk(35) == "moderate"
    assert classify_risk(55) == "high"
    assert classify_risk(80) == "extreme"


def test_risk_boundaries():
    """
    Boundary values must fall on the documented side of each band.
    Guards against off-by-one errors if thresholds are recalibrated.
    """
    assert classify_risk(24.9) == "low"
    assert classify_risk(25.0) == "moderate"
    assert classify_risk(44.9) == "moderate"
    assert classify_risk(45.0) == "high"
    assert classify_risk(64.9) == "high"
    assert classify_risk(65.0) == "extreme"
