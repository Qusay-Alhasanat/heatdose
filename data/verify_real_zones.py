# data/verify_real_zones.py
"""
One-time check — uses ONLY already-cached data, zero new API calls.

Compares our current (wrong) park_shaded/canal_greenway coordinates
against Encanto Park's real, verified coordinates, which happen to fall
inside the already-pulled study-area polygon. If real spatial variance
exists at all, it should show up between the genuinely industrial point
(already confirmed accurate) and the genuinely park point.
"""

from fortyguard_client import get_temperature_grid, nearest_temperature

STUDY_DATE = "2025-07-15"
HOURS = [6, 10, 14, 18]

# Confirmed-accurate extremes (verified against satellite imagery)
INDUSTRIAL_REAL = (33.4250, -112.0900)  # Reeve's Auto salvage yard, Esquipulas Trucking
ENCANTO_PARK_REAL = (33.4746, -112.0895)  # 222-acre park, lagoon, golf courses

# Our current (unverified) mock_data.py points, for comparison
PARK_SHADED_OLD = (33.4720, -112.0450)  # confirmed WRONG — lands on a nursery/houses
CANAL_GREENWAY_OLD = (33.4780, -112.0550)  # confirmed WRONG — lands on a school/houses

for hour in HOURS:
    grid = get_temperature_grid(STUDY_DATE, hour, use_cache=True)

    industrial = nearest_temperature(*INDUSTRIAL_REAL, grid)
    encanto = nearest_temperature(*ENCANTO_PARK_REAL, grid)
    park_old = nearest_temperature(*PARK_SHADED_OLD, grid)
    canal_old = nearest_temperature(*CANAL_GREENWAY_OLD, grid)

    print(f"\n=== {STUDY_DATE} {hour:02d}:00 ===")
    print(f"  industrial_yard (verified):     {industrial:.1f}C")
    print(
        f"  Encanto Park (verified real):   {encanto:.1f}C   diff: {industrial - encanto:+.1f}C"
    )
    print(
        f"  park_shaded (old, unverified):  {park_old:.1f}C   diff: {industrial - park_old:+.1f}C"
    )
    print(
        f"  canal_greenway (old, unverified): {canal_old:.1f}C   diff: {industrial - canal_old:+.1f}C"
    )
