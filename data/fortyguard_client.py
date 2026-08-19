# data/fortyguard_client.py
"""
Real FortyGuard Temperature API client.

Per docs/data_contract.md, this is the ONLY file in the project allowed
to talk to the FortyGuard API directly. Every other layer consumes the
contract shape this module produces — never the API's native response.

Confirmed against a live call during the hackathon (not guessed):
  - Base URL: https://api.fortyguard.com
  - Auth: `api-key` header (NOT Authorization: Bearer)
  - POST /v1/heatmap submits a job, returns {"activity_id": "..."}
    wrapped under a top-level "data" key on the raw HTTP response.
  - GET /v1/status/{activity_id} polls status. When Completed, the raw
    response's "data" contains {"status": ..., "result": {"map_data":
    ..., "stats_data": ...}}.
  - polygon_aoi is a GeoJSON FeatureCollection, coordinates in
    [longitude, latitude] order (opposite of our internal contract),
    with a closed ring (first point == last point).
  - analytic_type="tcm" (default) heatmap tiles carry
    properties.temperature (°C) directly usable per-tile.
  - Basic-tier area cap is 10 sq mi — the polygon below is sized to
    stay under that.

Credit-efficient strategy (see PROJECT_SPEC.md section 5.1): one
filter_type=1 (single-hour) call per DISTINCT hour needed across the
whole worker roster, covering all seven zones in a single polygon —
not one call per worker or per point. filter_type=3 (single day)
deliberately avoided: it returns one daily aggregate per tile, not an
hourly series, and would silently give the wrong shape of data for
this project's per-hour, per-location needs.
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

import requests

BASE_URL = os.environ.get("FORTYGUARD_BASE_URL", "https://api.fortyguard.com")
API_KEY = os.environ.get("FORTYGUARD_API_KEY", "")

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Bounding polygon covering all seven zones defined in mock_data.py
# (industrial_yard through canal_greenway), tightly fitted with almost
# no buffer.
#
# Coordinates in [lng, lat] order per the API's requirement — the
# OPPOSITE order from our internal {"lat":..., "lng":...} contract.
#
# Sized deliberately to stay under the Basic-tier ~10 sq mi cap: an
# earlier, more generously padded version of this box measured ~17 sq
# mi and the API returned a "Completed" status with n_cells: 0 — a
# silent empty response rather than an explicit error. This tighter
# box measures ~9.5 sq mi. If a real call still returns zero cells,
# split the study area into two smaller polygons instead of widening
# this one.
PHOENIX_STUDY_AREA = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-112.092, 33.423],
                        [-112.043, 33.423],
                        [-112.043, 33.480],
                        [-112.092, 33.480],
                        [-112.092, 33.423],
                    ]
                ],
            },
        }
    ],
}


class FortyGuardError(Exception):
    """Raised for API errors, failed tasks, or timeouts."""


def _headers() -> dict:
    if not API_KEY:
        raise FortyGuardError(
            "FORTYGUARD_API_KEY is not set. Copy .env.example to .env "
            "and paste your key in."
        )
    return {"api-key": API_KEY, "Content-Type": "application/json"}


def submit_heatmap(
    polygon_geojson: dict,
    start_date: str,
    start_time: str,
    filter_type: int = 1,
    granularity: int = 100,
    analytic_type: str = "tcm",
) -> str:
    """
    Submits a heatmap request. Returns the activity_id.

    Failed submissions do not consume credits, so a submit that raises
    here is safe to retry after fixing the payload.
    """
    payload = {
        "polygon_aoi": polygon_geojson,
        "date_time": {
            "start_date": start_date,
            # Confirmed from the official API docs example: "14:00" string
            # (HH:MM format). "14" caused 422, integer 14 caused 422,
            # "14:00" is the correct format per the live API explorer.
            "start_time": (
                start_time if ":" in str(start_time) else f"{int(start_time):02d}:00"
            ),
            "filter_type": filter_type,
        },
        "granularity": granularity,
    }
    # analytic_type is optional — the official docs example omits it.
    # Including it with an unrecognised value may cause 500 errors.
    if analytic_type and analytic_type != "tcm":
        payload["analytic_type"] = analytic_type
    resp = requests.post(
        f"{BASE_URL}/v1/heatmap", headers=_headers(), json=payload, timeout=30
    )
    resp.raise_for_status()
    body = resp.json()
    activity_id = body.get("data", {}).get("activity_id") or body.get("activity_id")
    if not activity_id:
        raise FortyGuardError(f"No activity_id in response: {body}")
    return activity_id


def poll_status(activity_id: str) -> dict:
    """Single status check. Raises on HTTP error, does not poll/wait."""
    resp = requests.get(
        f"{BASE_URL}/v1/status/{activity_id}", headers=_headers(), timeout=30
    )
    resp.raise_for_status()
    body = resp.json()
    return body.get("data", body)


def wait_for(activity_id: str, timeout_s: int = 300) -> dict:
    """
    Polls until the task completes with real data, fails, or times out.

    The API may return status=Completed with empty map_data/stats_data
    on early polls — confirmed by the official API docs example which
    shows both as empty dicts on first completion. Keep polling until
    map_data or stats_data contains actual content.

    Backoff: 3s -> 6s -> 12s -> 24s -> capped at 30s.

    Returns:
        The completed result dict: {"map_data": ..., "stats_data": ...}

    Raises:
        FortyGuardError: task failed or did not return data in time.
    """
    delay = 3
    elapsed = 0
    while elapsed < timeout_s:
        status = poll_status(activity_id)
        state = str(status.get("status", "")).lower()

        if state == "failed":
            raise FortyGuardError(f"Task {activity_id} failed: {status}")

        if state == "completed":
            result = status.get("result", status)
            if result.get("map_data") or result.get("stats_data"):
                return result

        time.sleep(delay)
        elapsed += delay
        delay = min(delay * 2, 30)

    raise FortyGuardError(f"Task {activity_id} did not return data within {timeout_s}s")


# --------------------------------------------------------------------
# Caching — every successful pull is saved so the live demo never
# depends on a real-time API call during judging.
# --------------------------------------------------------------------


def _cache_key(date: str, hour: int, granularity: int) -> str:
    raw = f"{date}:{hour}:{granularity}:{PHOENIX_STUDY_AREA}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(date: str, hour: int, granularity: int) -> Path:
    return (
        CACHE_DIR
        / f"heatmap_{date}_{hour:02d}_{_cache_key(date, hour, granularity)}.json"
    )


def _load_cache(date: str, hour: int, granularity: int) -> list[dict] | None:
    path = _cache_path(date, hour, granularity)
    if path.exists():
        return json.loads(path.read_text())
    return None


def _save_cache(date: str, hour: int, granularity: int, points: list[dict]) -> None:
    path = _cache_path(date, hour, granularity)
    path.write_text(json.dumps(points, indent=2))


# --------------------------------------------------------------------
# Contract transform — the one place raw API tiles become our shape
# --------------------------------------------------------------------


def _tile_center(feature: dict) -> dict:
    """
    Computes a tile's centre point from its GeoJSON geometry, converting
    from the API's [lng, lat] order to our contract's {"lat", "lng"}.
    Works for Polygon geometries by averaging ring coordinates.
    """
    coords = feature["geometry"]["coordinates"][0]
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return {
        "lat": round(sum(lats) / len(lats), 4),
        "lng": round(sum(lngs) / len(lngs), 4),
    }


def get_temperature_grid(
    date: str, hour: int, granularity: int = 100, use_cache: bool = True
) -> list[dict]:
    """
    Fetches (or replays from cache) tile-level temperatures across the
    full study area for one specific hour.

    Returns:
        List of contract-compliant points (missing worker_id — this is
        a grid snapshot, not a worker shift): each has "location"
        {"lat","lng"} and "temp_c".
    """
    if use_cache:
        cached = _load_cache(date, hour, granularity)
        if cached is not None:
            return cached

    start_time = f"{hour:02d}:00"
    activity_id = submit_heatmap(
        PHOENIX_STUDY_AREA,
        start_date=date,
        start_time=start_time,
        filter_type=1,
        granularity=granularity,
        analytic_type="tcm",
    )
    result = wait_for(activity_id)

    features = result.get("map_data", {}).get("features", [])
    points = [
        {
            "location": _tile_center(f),
            "temp_c": f["properties"]["average_temperature"],
        }
        for f in features
        if "average_temperature" in f.get("properties", {})
    ]

    _save_cache(date, hour, granularity, points)
    return points


def nearest_temperature(lat: float, lng: float, grid: list[dict]) -> float:
    """
    Looks up the temperature of the grid tile nearest a given point.
    Used to get a specific worker's or cool point's temperature from a
    full-area grid pulled once per hour (see PROJECT_SPEC.md 5.1 for
    why we pull per-hour grids rather than per-point calls).
    """

    def _dist2(p):
        return (p["location"]["lat"] - lat) ** 2 + (p["location"]["lng"] - lng) ** 2

    nearest = min(grid, key=_dist2)
    return nearest["temp_c"]


if __name__ == "__main__":
    # Clean smoke test — debugging is done, this is the real usage pattern.
    # Cache-first: first run per (date, hour) spends one real API call and
    # saves it; every run after that is free and instant.
    STUDY_DATE = "2025-07-15"
    STUDY_HOUR = 14

    print(f"Fetching Phoenix grid for {STUDY_DATE} {STUDY_HOUR:02d}:00 ...")
    grid = get_temperature_grid(STUDY_DATE, STUDY_HOUR, use_cache=True)
    print(f"Points returned: {len(grid)}")
    if grid:
        temps = [p["temp_c"] for p in grid]
        print(f"Temp range: {min(temps):.1f}C - {max(temps):.1f}C")
        print(f"Sample point: {grid[0]}")
