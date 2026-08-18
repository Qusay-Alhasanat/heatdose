# data/hdi.py
"""
Calculates heat exposure metrics for a worker's shift.

Two metrics are exposed:

  calculate_hdi()          — total accumulated heat (context / display)
  calculate_excess_dose()  — heat accumulated ABOVE the safety threshold,
                             which is what drives the risk classification

Both consume data matching data_contract.md and are agnostic to whether
that data came from mock_data.py or the real FortyGuard API.
"""

from datetime import datetime

# Screening threshold from a CDC review of occupational heat-illness cases:
# a Heat Index of 85°F (29.4°C) identified hazardous workplace conditions in
# the majority of investigated incidents. We use it as the point above which
# accumulated heat begins counting toward risk.
SAFE_THRESHOLD_C = 29.4


def _elapsed_hours(point_a: dict, point_b: dict) -> float:
    """Hours between two consecutive contract-compliant points."""
    t1 = datetime.fromisoformat(point_a["timestamp"])
    t2 = datetime.fromisoformat(point_b["timestamp"])
    return (t2 - t1).total_seconds() / 3600


def calculate_hdi(shift: list[dict]) -> float:
    """
    Total cumulative heat exposure across a worker's shift.

    Method: trapezoidal accumulation — for each consecutive pair of points,
    multiply the average temperature by the time elapsed, then sum.

    Note: this counts ALL heat, including benign baseline warmth. It is
    useful for context and display, but poorly discriminating for risk —
    see calculate_excess_dose().

    Args:
        shift: list of points matching data_contract.md, sorted by timestamp.

    Returns:
        Total dose in °C·hours.
    """
    if len(shift) < 2:
        return 0.0

    total = 0.0
    for i in range(len(shift) - 1):
        avg_temp = (shift[i]["temp_c"] + shift[i + 1]["temp_c"]) / 2
        total += avg_temp * _elapsed_hours(shift[i], shift[i + 1])

    return round(total, 2)


def calculate_excess_dose(shift: list[dict]) -> float:
    """
    Cumulative heat exposure ABOVE the safety screening threshold.

    Only the portion of temperature exceeding SAFE_THRESHOLD_C contributes.
    This is what actually drives thermal strain, and it separates workers
    far more sharply than total dose: a worker in the shade and a worker on
    asphalt may differ by 15% in total dose but by 80% in excess dose.

    Args:
        shift: list of points matching data_contract.md, sorted by timestamp.

    Returns:
        Excess dose in °C·hours above SAFE_THRESHOLD_C.
    """
    if len(shift) < 2:
        return 0.0

    total = 0.0
    for i in range(len(shift) - 1):
        # Clamped at zero: time below the threshold contributes nothing and
        # does not offset time spent above it.
        e1 = max(0.0, shift[i]["temp_c"] - SAFE_THRESHOLD_C)
        e2 = max(0.0, shift[i + 1]["temp_c"] - SAFE_THRESHOLD_C)

        total += ((e1 + e2) / 2) * _elapsed_hours(shift[i], shift[i + 1])

    return round(total, 2)


def classify_risk(excess_dose: float) -> str:
    """
    Maps excess dose to an operational risk level.

    Bands are provisional — calibrated to produce meaningful separation
    across a standard 4-10 hour shift, not derived from clinical outcome
    data. See docs/methodology.md for limitations.

    Args:
        excess_dose: output of calculate_excess_dose(), NOT calculate_hdi().
    """
    if excess_dose < 25:
        return "low"
    elif excess_dose < 45:
        return "moderate"
    elif excess_dose < 65:
        return "high"
    else:
        return "extreme"


if __name__ == "__main__":
    from mock_data import generate_mock_workers

    workers = generate_mock_workers()

    print(f"{'Worker':<8} {'Total':>8} {'Excess':>8}  Risk")
    print("-" * 38)
    for worker_id, shift in workers.items():
        total = calculate_hdi(shift)
        excess = calculate_excess_dose(shift)
        print(f"{worker_id:<8} {total:>8.1f} {excess:>8.1f}  {classify_risk(excess)}")
