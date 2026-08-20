# data/real_shift_builder.py
"""
Bridges simulated worker movement (mock_data.py) with real FortyGuard
temperature readings (fortyguard_client.py).

Why this file exists
---------------------
FortyGuard has no concept of a "worker." It is a pure environmental API:
give it a polygon and an hour, it returns a temperature grid for that
area. Workers, their routes, and their shift timing are entirely our own
simulation (mock_data.py) — built to demonstrate the product with a
realistic roster during a 10-day hackathon, without real GPS/wearable
integration.

This module is the seam between the two. It takes a worker's simulated
route (locations + timestamps, contract-compliant except for temp_c) and
replaces the synthetic temp_c from mock_data.temp_at() with a real
reading from FortyGuard's cache, looked up by nearest grid tile.

Production note (for methodology.md / business viability): in a real
deployment, only the LEFT side of this seam changes — location and
timestamp would come from a GPS or wearable feed instead of mock_data.py.
Everything downstream of this file (hdi.py, baseline.py, worker_status.py,
the agent tools) runs completely unmodified.
"""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    from fortyguard_client import _load_cache, get_temperature_grid, nearest_temperature
except ModuleNotFoundError:  # pragma: no cover
    from data.fortyguard_client import (
        _load_cache,
        get_temperature_grid,
        nearest_temperature,
    )


class MissingRealDataError(Exception):
    """
    Raised when a shift needs an hour that is not yet in the cache and
    strict=True. This is a deliberate guard, not a bug: it stops the
    pipeline from silently making a live API call (and spending quota)
    just because a shift generator produced a new timestamp.
    """


def _round_to_cached_hour(timestamp: str) -> tuple[str, int]:
    """
    Splits an ISO timestamp into (date, hour), rounding to the nearest
    hour. Cached grids are pulled per-hour (see fortyguard_client.py),
    so every shift point must map onto exactly one cached (date, hour).
    """
    dt = datetime.fromisoformat(timestamp)
    if dt.minute >= 30:
        dt = dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        dt = dt.replace(minute=0, second=0, microsecond=0)
    return dt.strftime("%Y-%m-%d"), dt.hour


def attach_real_temperatures(
    shift: list[dict],
    granularity: int = 100,
    strict: bool = True,
) -> list[dict]:
    """
    Returns a NEW shift (same contract shape as the input) with every
    point's temp_c replaced by a real FortyGuard reading — the nearest
    grid tile for that point's hour. The input list is not mutated.

    Args:
        shift: contract-compliant points from mock_data.py. worker_id,
            location, and timestamp are kept as-is; temp_c is replaced.
        granularity: must match whatever granularity the hour was
            originally pulled and cached with.
        strict: if True (default), raise MissingRealDataError instead of
            triggering a live API call when an hour isn't cached yet.
            Set False only when you deliberately want to backfill the
            cache as part of running this function.

    Returns:
        A new list of contract-compliant points with real temperatures.

    Raises:
        MissingRealDataError: a required hour is not cached and
            strict=True.
    """
    real_shift = []

    for point in shift:
        date, hour = _round_to_cached_hour(point["timestamp"])

        if strict:
            grid = _load_cache(date, hour, granularity)
            if grid is None:
                raise MissingRealDataError(
                    f"No cached grid for {date} {hour:02d}:00 "
                    f"(granularity={granularity}). Pull it first with "
                    f"get_temperature_grid('{date}', {hour}), or pass "
                    f"strict=False to allow attach_real_temperatures() "
                    f"to fetch it live."
                )
        else:
            grid = get_temperature_grid(date, hour, granularity=granularity)

        real_temp = nearest_temperature(
            point["location"]["lat"], point["location"]["lng"], grid
        )

        real_shift.append({**point, "temp_c": real_temp})

    return real_shift


def build_real_workers(
    mock_workers: dict[str, list[dict]],
    granularity: int = 100,
    strict: bool = True,
) -> dict[str, list[dict]]:
    """
    Applies attach_real_temperatures() across an entire roster.

    Args:
        mock_workers: output of mock_data.generate_mock_workers().

    Returns:
        {"W-01": [...real shift...], "W-02": [...], ...}
    """
    return {
        worker_id: attach_real_temperatures(
            shift, granularity=granularity, strict=strict
        )
        for worker_id, shift in mock_workers.items()
    }


def hours_needed_for(mock_workers: dict[str, list[dict]]) -> set[tuple[str, int]]:
    """
    Returns the distinct (date, hour) pairs a roster needs. Used to check
    what's already cached vs. what still needs to be pulled, without
    spending any API calls.
    """
    needed = set()
    for shift in mock_workers.values():
        for point in shift:
            needed.add(_round_to_cached_hour(point["timestamp"]))
    return needed


def missing_hours(
    mock_workers: dict[str, list[dict]], granularity: int = 100
) -> list[tuple[str, int]]:
    """Which needed hours are NOT yet in the cache, sorted for readability."""
    needed = hours_needed_for(mock_workers)
    return sorted(h for h in needed if _load_cache(*h, granularity) is None)


if __name__ == "__main__":
    from hdi import calculate_excess_dose, classify_risk
    from mock_data import generate_mock_workers

    mock_workers = generate_mock_workers()
    needed = hours_needed_for(mock_workers)
    missing = missing_hours(mock_workers)

    print(f"Hours needed across the roster: {len(needed)}")

    if missing:
        print(f"\nMissing {len(missing)} hour(s) from cache:")
        for date, hour in missing:
            print(f"  {date} {hour:02d}:00")
        print(
            "\nPull them first with:\n"
            "  uv run python data/fortyguard_client.py --pull-day"
        )
    else:
        print("All needed hours are cached. Building real shifts...\n")
        real_workers = build_real_workers(mock_workers)

        print(f"{'Worker':<8} {'Mock excess':>12} {'Real excess':>12}  Risk (real)")
        print("-" * 52)
        for worker_id in mock_workers:
            mock_excess = calculate_excess_dose(mock_workers[worker_id])
            real_excess = calculate_excess_dose(real_workers[worker_id])
            print(
                f"{worker_id:<8} {mock_excess:>12.1f} {real_excess:>12.1f}  "
                f"{classify_risk(real_excess)}"
            )
