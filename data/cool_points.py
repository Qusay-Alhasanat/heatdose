# data/cool_points.py
"""
Finds the nearest meaningfully cooler location for a worker, given a set
of candidate rest points. This is the data-layer function behind the
Agent's "suggest a cooler spot" tool — the Agent calls this, it never
computes distances or eligibility itself.

⚠️ Data source note (added 20 Aug, see mock_data.py's docstring for full
context): candidate point temperatures come from mock_data.temp_at() —
a synthetic zone model, NOT real FortyGuard data. This is a deliberate
scope decision (PROJECT_SPEC.md §12: hand-placed candidates, not real
amenity/temperature data), not an oversight. It does mean a cool point's
apparent temp_diff_c is illustrative rather than measured. If asked
directly, be upfront about this rather than implying the suggestion is
backed by the same real data as a worker's dose/risk numbers.
"""

import math

# Import works both when run directly (python data/cool_points.py) and when
# imported as part of the package (from data.cool_points import ...), which
# is how the tests and the Agent layer will reach it.
try:
    from mock_data import ZONE_OFFSETS, temp_at
except ModuleNotFoundError:  # pragma: no cover
    from data.mock_data import ZONE_OFFSETS, temp_at

# Candidate rest points: specific locations a worker could realistically
# walk to and shelter at — a shaded park corner, a tree-lined side street,
# a canal path.
#
# These are deliberately NOT the zone centres from mock_data.py. Zone
# centres are far apart by construction (1.8-6.7 km), so using them as
# candidates meant no worker in a hot zone ever had a reachable option.
# Real cities are not like that: shade exists close to exposed ground.
# Each candidate here sits within a few hundred metres of a hot zone.
#
# zone_type determines the candidate's temperature via the same model used
# for worker shifts, so a park corner behaves like a park.
CANDIDATE_POINTS = [
    {
        "point_id": "CP-01",
        "zone_type": "park_shaded",
        "location": {"lat": 33.4283, "lng": -112.0898},
    },
    {
        "point_id": "CP-02",
        "zone_type": "tree_lined_street",
        "location": {"lat": 33.4252, "lng": -112.0855},
    },
    {
        "point_id": "CP-03",
        "zone_type": "tree_lined_street",
        "location": {"lat": 33.4378, "lng": -112.0752},
    },
    {
        "point_id": "CP-04",
        "zone_type": "park_shaded",
        "location": {"lat": 33.4340, "lng": -112.0705},
    },
    {
        "point_id": "CP-05",
        "zone_type": "park_shaded",
        "location": {"lat": 33.4512, "lng": -112.0752},
    },
    {
        "point_id": "CP-06",
        "zone_type": "canal_greenway",
        "location": {"lat": 33.4462, "lng": -112.0692},
    },
    {
        "point_id": "CP-07",
        "zone_type": "canal_greenway",
        "location": {"lat": 33.4628, "lng": -112.0600},
    },
    {
        "point_id": "CP-08",
        "zone_type": "park_shaded",
        "location": {"lat": 33.4672, "lng": -112.0512},
    },
]

# Below this temperature difference, moving isn't worth it — the walk
# itself adds exposure that could exceed the benefit.
MIN_MEANINGFUL_DIFF_C = 3.0

# Above this distance, walking there likely costs more heat exposure than
# staying put would save. ~800m is roughly a 10-minute walk.
MAX_DISTANCE_M = 800.0


def get_candidates_with_current_temp(hour: int) -> list[dict]:
    """
    Builds the candidate list with temperature attached for a specific
    hour, matching the Cool Point contract in data_contract.md.

    Args:
        hour: hour of day (24h clock), used to compute time-dependent
            temperature via the same zone model used for worker shifts.

    Returns:
        List of candidate points with point_id, zone_type, location, temp_c.
    """
    return [
        {**point, "temp_c": temp_at(hour, point["zone_type"])}
        for point in CANDIDATE_POINTS
    ]


def _haversine_distance_m(loc_a: dict, loc_b: dict) -> float:
    """
    Great-circle distance between two lat/lng points, in meters.
    Standard haversine formula — accurate enough at city scale.
    """
    R = 6371000  # Earth radius in meters
    lat1, lng1 = math.radians(loc_a["lat"]), math.radians(loc_a["lng"])
    lat2, lng2 = math.radians(loc_b["lat"]), math.radians(loc_b["lng"])

    dlat = lat2 - lat1
    dlng = lng2 - lng1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def find_nearest_cool_point(
    worker_location: dict,
    worker_current_temp_c: float,
    hour: int,
    min_diff_c: float = MIN_MEANINGFUL_DIFF_C,
    max_distance_m: float = MAX_DISTANCE_M,
) -> dict | None:
    """
    Finds the nearest candidate point that is both meaningfully cooler
    than the worker's current location AND within walking distance, at
    the given hour.

    Design: filter by temperature benefit AND distance cap first, then
    rank the survivors by distance. A cooler point 5 km away costs more
    heat to reach than it saves, so it must never be recommended — this
    is enforced here, not left to the caller.

    Returning None is a valid and meaningful outcome, not a failure: it
    means no shelter is reachable, and the correct response is on-site
    rest or a shift change rather than sending the worker walking.

    Args:
        worker_location: {"lat": ..., "lng": ...}
        worker_current_temp_c: worker's current ambient temperature
        hour: hour of day, used to compute candidate temperatures
        min_diff_c: minimum temperature drop to be worth recommending
        max_distance_m: maximum walking distance to consider

    Returns:
        Dict with point_id, zone_type, location, temp_c, temp_diff_c,
        distance_m — or None if nothing is both cool enough and close
        enough.
    """
    candidates = get_candidates_with_current_temp(hour)

    scored = []
    for c in candidates:
        diff = worker_current_temp_c - c["temp_c"]
        if diff < min_diff_c:
            continue
        distance = _haversine_distance_m(worker_location, c["location"])
        if distance > max_distance_m:
            continue
        scored.append((distance, diff, c))

    if not scored:
        return None

    distance, diff, nearest = min(scored, key=lambda s: s[0])

    return {
        "point_id": nearest["point_id"],
        "zone_type": nearest["zone_type"],
        "location": nearest["location"],
        "temp_c": nearest["temp_c"],
        "temp_diff_c": round(diff, 1),
        "distance_m": round(distance),
    }


if __name__ == "__main__":
    from mock_data import ZONE_CENTRES

    print(f"{'Worker zone':<20} {'Temp':>6}  Suggestion")
    print("-" * 68)

    for zone in sorted(ZONE_OFFSETS, key=lambda z: -ZONE_OFFSETS[z]):
        lat, lng = ZONE_CENTRES[zone]
        temp = temp_at(14, zone)
        result = find_nearest_cool_point(
            {"lat": lat, "lng": lng}, worker_current_temp_c=temp, hour=14
        )

        if result:
            note = (
                f"{result['point_id']} — {result['temp_diff_c']}C cooler, "
                f"{result['distance_m']}m"
            )
        else:
            note = "none reachable — recommend on-site rest / shift change"

        print(f"{zone:<20} {temp:>5.1f}C  {note}")
