# data/worker_status.py
"""
Aggregates everything about a worker into a single call. This is the
file the Agent layer calls directly — get_worker_status() and
list_workers_at_risk() back four of the agent's tools (two directly,
find_cool_point and compare_to_city_baseline indirectly via the same
worker data). Per data_contract.md's ownership table, agent/tools.py
reads this output and never talks to hdi.py, mock_data.py, or
fortyguard_client.py directly.
"""

from __future__ import annotations

try:
    from hdi import calculate_excess_dose, calculate_hdi, classify_risk
    from mock_data import (
        ROUTE_PROFILES,
        WORKER_ROSTER,
        generate_mock_shift,
        generate_mock_workers,
    )
    from real_shift_builder import attach_real_temperatures, build_real_workers
except ModuleNotFoundError:  # pragma: no cover
    from data.hdi import calculate_excess_dose, calculate_hdi, classify_risk
    from data.mock_data import (
        ROUTE_PROFILES,
        WORKER_ROSTER,
        generate_mock_shift,
        generate_mock_workers,
    )
    from data.real_shift_builder import attach_real_temperatures, build_real_workers

# Mirrors baseline.py's risk ordering. Kept local rather than imported —
# it's a three-line lookup table, not worth a cross-module dependency.
_RISK_ORDER = {"low": 0, "moderate": 1, "high": 2, "extreme": 3}


class UnknownWorkerError(Exception):
    """Raised when a worker_id isn't in WORKER_ROSTER."""


def _status_from_shift(worker_id: str, shift: list[dict]) -> dict:
    """
    Builds the status dict for one worker from an already-bridged
    (real-temperature) shift. Shared by get_worker_status() and
    list_workers_at_risk() so the two can never drift out of sync with
    each other's output shape.
    """
    config = WORKER_ROSTER[worker_id]
    profile = config["profile"]
    zones = ROUTE_PROFILES[profile]

    # generate_mock_shift() builds one point per zone in order, so the
    # shift and the zone sequence are always the same length — the last
    # point corresponds to the last zone in the route.
    last_point = shift[-1]
    current_zone = zones[-1]

    total_dose = calculate_hdi(shift)
    excess_dose = calculate_excess_dose(shift)

    return {
        "worker_id": worker_id,
        "profile": profile,
        "shift_start_hour": config["start_hour"],
        "hours_elapsed": len(shift) - 1,
        "current_location": last_point["location"],
        "current_zone": current_zone,
        "current_temp_c": last_point["temp_c"],
        "total_dose": total_dose,
        "excess_dose": excess_dose,
        "risk_level": classify_risk(excess_dose),
    }


def get_worker_status(worker_id: str) -> dict:
    """
    Everything about one worker in a single call: profile, current
    location/zone/temperature, accumulated dose, and risk level — built
    from real FortyGuard temperatures via real_shift_builder.py.

    Args:
        worker_id: e.g. "W-01".

    Returns:
        {
          "worker_id": "W-01",
          "profile": "construction_crew",
          "shift_start_hour": 6,
          "hours_elapsed": 9,
          "current_location": {"lat": ..., "lng": ...},
          "current_zone": "industrial_yard",
          "current_temp_c": 39.8,
          "total_dose": 95.0,
          "excess_dose": 91.5,
          "risk_level": "extreme"
        }

    Raises:
        UnknownWorkerError: worker_id not in WORKER_ROSTER.
        real_shift_builder.MissingRealDataError: a required hour for
            this worker's shift is not yet cached — fails loudly rather
            than silently returning a partial or synthetic result.
    """
    if worker_id not in WORKER_ROSTER:
        raise UnknownWorkerError(
            f"Unknown worker_id: {worker_id!r}. Known workers: "
            f"{sorted(WORKER_ROSTER)}"
        )

    config = WORKER_ROSTER[worker_id]
    mock_shift = generate_mock_shift(
        worker_id,
        route_profile=config["profile"],
        start_hour=config["start_hour"],
    )
    real_shift = attach_real_temperatures(mock_shift)

    return _status_from_shift(worker_id, real_shift)


def list_workers_at_risk(min_level: str = "high") -> list[dict]:
    """
    Every worker whose risk_level is at least min_level, sorted
    descending by excess_dose — highest risk first.

    Args:
        min_level: one of "low", "moderate", "high", "extreme".
            Workers at or above this band are included.

    Returns:
        List of get_worker_status()-shaped dicts.

    Raises:
        ValueError: min_level isn't a recognised risk band.
        real_shift_builder.MissingRealDataError: any worker's shift
            needs an hour that isn't cached yet.
    """
    if min_level not in _RISK_ORDER:
        raise ValueError(
            f"min_level must be one of {list(_RISK_ORDER)}, got {min_level!r}"
        )

    mock_workers = generate_mock_workers()
    real_workers = build_real_workers(mock_workers)

    statuses = [
        _status_from_shift(worker_id, shift)
        for worker_id, shift in real_workers.items()
    ]

    threshold = _RISK_ORDER[min_level]
    at_risk = [s for s in statuses if _RISK_ORDER[s["risk_level"]] >= threshold]

    return sorted(at_risk, key=lambda s: s["excess_dose"], reverse=True)


if __name__ == "__main__":
    from real_shift_builder import missing_hours

    mock_workers = generate_mock_workers()
    missing = missing_hours(mock_workers)

    if missing:
        print(f"Missing {len(missing)} hour(s) from cache. Run:")
        print("  uv run python data/fortyguard_client.py --pull-day")
    else:
        print("=== get_worker_status('W-01') ===")
        for k, v in get_worker_status("W-01").items():
            print(f"  {k}: {v}")

        print("\n=== list_workers_at_risk('high') ===")
        at_risk = list_workers_at_risk("high")
        print(f"{'Worker':<8} {'Excess dose':>12}  Risk")
        print("-" * 34)
        for s in at_risk:
            print(f"{s['worker_id']:<8} {s['excess_dose']:>12.1f}  {s['risk_level']}")
