# data/mock_data.py
"""
Generates fake worker shift data matching data_contract.md exactly.

Design note
-----------
Temperature here is a function of BOTH time and location. This models the
urban heat island effect: within a single city at a single hour, asphalt
industrial zones run several degrees hotter than shaded parks or greenways.

That spatial variation is the entire premise of this project. City-level
weather data collapses it to one number; FortyGuard's 20m resolution
preserves it. Our mock data must reproduce that structure, otherwise every
worker accumulates an identical Heat Dose and the system has nothing to say.

Used to build and test all layers (Data, Agent, Web) before real API access.
"""

import random
from datetime import datetime, timedelta

# Urban heat island offsets, in °C relative to the city-wide average.
# These approximate documented intra-city variation in desert cities:
# exposed asphalt and low-albedo industrial surfaces retain heat, while
# vegetated and shaded corridors stay measurably cooler at the same hour.
ZONE_OFFSETS = {
    "industrial_yard": 4.5,
    "asphalt_lot": 3.5,
    "downtown_core": 2.0,
    "residential": 0.0,
    "tree_lined_street": -2.5,
    "park_shaded": -4.0,
    "canal_greenway": -5.5,
}

# Approximate centres for each zone within the Phoenix bounding box.
# Coordinates are illustrative, not surveyed locations.
ZONE_CENTRES = {
    "industrial_yard": (33.4250, -112.0900),
    "asphalt_lot": (33.4350, -112.0750),
    "downtown_core": (33.4484, -112.0740),
    "residential": (33.4600, -112.0600),
    "tree_lined_street": (33.4650, -112.0500),
    "park_shaded": (33.4720, -112.0450),
    "canal_greenway": (33.4780, -112.0550),
}

# Route archetypes. Each worker follows one, which determines both the mix
# of zones they pass through AND the length of their shift.
#
# Shift length is not cosmetic — it is a primary driver of accumulated dose.
# A construction crew working a 10-hour summer day accumulates fundamentally
# differently from a 5-hour inspection round, even in identical zones.
# Lengths here reflect typical outdoor shift patterns in hot-climate US cities.
ROUTE_PROFILES = {
    # 10-hour day, almost entirely on exposed surfaces
    "construction_crew": [
        "industrial_yard",
        "industrial_yard",
        "asphalt_lot",
        "industrial_yard",
        "asphalt_lot",
        "industrial_yard",
        "asphalt_lot",
        "industrial_yard",
        "asphalt_lot",
        "industrial_yard",
    ],
    # 8-hour route, mixed exposure, spans the afternoon peak
    "delivery_rider": [
        "residential",
        "downtown_core",
        "asphalt_lot",
        "downtown_core",
        "asphalt_lot",
        "residential",
        "downtown_core",
        "tree_lined_street",
    ],
    # 5-hour inspection round, mostly shaded corridors
    "utility_inspector": [
        "residential",
        "tree_lined_street",
        "canal_greenway",
        "park_shaded",
        "tree_lined_street",
    ],
    # 7-hour mixed field work
    "mixed_field_tech": [
        "downtown_core",
        "asphalt_lot",
        "park_shaded",
        "downtown_core",
        "residential",
        "asphalt_lot",
        "downtown_core",
    ],
}

# The demo roster. Start times matter as much as route composition: a crew
# starting at 06:00 works through the full heat build-up, while a rider
# starting at 11:00 hits the afternoon peak immediately but finishes as it
# subsides. Same city, same day — very different accumulated exposure.
WORKER_ROSTER = {
    "W-01": {"profile": "construction_crew", "start_hour": 6},
    "W-02": {"profile": "delivery_rider", "start_hour": 11},
    "W-03": {"profile": "utility_inspector", "start_hour": 8},
    "W-04": {"profile": "mixed_field_tech", "start_hour": 9},
    "W-05": {"profile": "construction_crew", "start_hour": 7},
}


def _city_average_temp_c(hour: int) -> float:
    """
    The city-wide temperature curve for a Phoenix summer day.

    This is the value a standard weather API would report for the whole
    city. It peaks mid-afternoon and drops off either side.
    """
    peak_hour = 15
    peak_temp = 43.0
    floor_temp = 30.0

    distance_from_peak = abs(hour - peak_hour)
    temp = peak_temp - (distance_from_peak * 1.6)
    return max(temp, floor_temp)


def temp_at(hour: int, zone: str) -> float:
    """
    Temperature at a specific zone and hour.

    Combines the city-wide curve with the zone's heat island offset, then
    adds small sensor-level noise. The offset is scaled by time of day:
    surface heating differences are strongest in the afternoon and nearly
    vanish before sunrise.
    """
    base = _city_average_temp_c(hour)
    offset = ZONE_OFFSETS[zone]

    # Offsets peak mid-afternoon, shrink toward early morning
    intensity = max(0.35, 1.0 - (abs(hour - 15) * 0.09))

    # Noise is seeded from (zone, hour) rather than drawn from the global
    # random stream. The same zone at the same hour therefore always returns
    # the same temperature, whoever asks and in whatever order. Cool point
    # lookups depend on this: without it, querying the same rest spot twice
    # gives two different temperatures.
    rng = random.Random(f"{zone}:{hour}")

    temp = base + (offset * intensity) + rng.uniform(-0.4, 0.4)
    return round(temp, 1)


def _location_in_zone(zone: str) -> dict:
    """Picks a point near a zone's centre, with slight scatter."""
    lat, lng = ZONE_CENTRES[zone]
    return {
        "lat": round(lat + random.uniform(-0.004, 0.004), 4),
        "lng": round(lng + random.uniform(-0.004, 0.004), 4),
    }


def generate_mock_shift(
    worker_id: str,
    route_profile: str = "delivery_rider",
    start_hour: int = 9,
    interval_hours: int = 1,
    shift_date: str = "2025-07-15",
) -> list[dict]:
    """
    Generates one worker's full shift as a list of data points,
    matching data_contract.md exactly.

    Args:
        worker_id: identifier, e.g. "W-01"
        route_profile: key from ROUTE_PROFILES, determines the zone sequence
        start_hour: hour the shift begins (24h clock)
        interval_hours: sampling interval between readings
        shift_date: ISO date string

    Returns:
        List of contract-compliant points, ordered chronologically.
    """
    if route_profile not in ROUTE_PROFILES:
        raise ValueError(
            f"Unknown route profile: {route_profile!r}. "
            f"Expected one of {list(ROUTE_PROFILES)}"
        )

    zones = ROUTE_PROFILES[route_profile]
    base_time = datetime.fromisoformat(f"{shift_date}T{start_hour:02d}:00:00")

    shift = []
    for i, zone in enumerate(zones):
        timestamp = base_time + timedelta(hours=i * interval_hours)
        shift.append(
            {
                "worker_id": worker_id,
                "location": _location_in_zone(zone),
                "timestamp": timestamp.isoformat(),
                "temp_c": temp_at(timestamp.hour, zone),
            }
        )

    return shift


def generate_mock_workers(seed: int | None = 42) -> dict[str, list[dict]]:
    """
    Generates the demo roster, using WORKER_ROSTER as the single source
    of truth for who works which route and when.

    A seed is set by default so the demo produces identical output on every
    run. Reproducibility matters here: judges review the live demo days
    after submission, and the numbers quoted in the README must still match
    what they see on screen.

    Returns:
        {"W-01": [...], "W-02": [...], ...}
    """
    if seed is not None:
        random.seed(seed)

    return {
        worker_id: generate_mock_shift(
            worker_id,
            route_profile=config["profile"],
            start_hour=config["start_hour"],
        )
        for worker_id, config in WORKER_ROSTER.items()
    }


if __name__ == "__main__":
    # Quick manual check — run this file directly to inspect the spread.
    from hdi import calculate_excess_dose, calculate_hdi, classify_risk

    workers = generate_mock_workers()

    print(f"{'Worker':<7} {'Profile':<19} {'Hrs':>4} {'Total':>7} {'Excess':>7}  Risk")
    print("-" * 60)

    for worker_id, shift in workers.items():
        config = WORKER_ROSTER[worker_id]
        hours = len(shift) - 1
        print(
            f"{worker_id:<7} {config['profile']:<19} {hours:>4} "
            f"{calculate_hdi(shift):>7.1f} "
            f"{calculate_excess_dose(shift):>7.1f}  "
            f"{classify_risk(calculate_excess_dose(shift))}"
        )
