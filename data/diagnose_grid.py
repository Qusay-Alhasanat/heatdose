# data/diagnose_grid.py
"""
One-time diagnostic — NOT part of the pipeline.

Answers: does our real cached FortyGuard data actually contain the kind
of spatial heat variance the whole project's story depends on? And is
our zone-centre-based "hyperlocal" reading landing on the genuinely
hot/cool parts of the real grid, or somewhere near the middle?

Run this once after pulling real data, read the numbers, then delete it
or leave it — it never runs as part of the real pipeline.
"""

from fortyguard_client import get_temperature_grid, nearest_temperature
from mock_data import ZONE_CENTRES

STUDY_DATE = "2025-07-15"
HOURS_TO_CHECK = [6, 10, 14, 18]  # morning, mid-morning, peak, evening


def _stats(temps: list[float]) -> dict:
    n = len(temps)
    mean = sum(temps) / n
    variance = sum((t - mean) ** 2 for t in temps) / n
    return {
        "n": n,
        "min": round(min(temps), 2),
        "max": round(max(temps), 2),
        "mean": round(mean, 2),
        "std": round(variance**0.5, 2),
        "range": round(max(temps) - min(temps), 2),
    }


for hour in HOURS_TO_CHECK:
    grid = get_temperature_grid(STUDY_DATE, hour, use_cache=True)
    temps = [p["temp_c"] for p in grid]
    s = _stats(temps)

    print(f"\n=== {STUDY_DATE} {hour:02d}:00 — {s['n']} tiles ===")
    print(
        f"Grid stats: min={s['min']}  max={s['max']}  mean={s['mean']}  "
        f"std={s['std']}  range={s['range']}"
    )

    print(f"{'Zone':<20} {'Nearest tile temp':>18}  Diff from grid mean")
    print("-" * 62)
    for zone, (lat, lng) in ZONE_CENTRES.items():
        temp = nearest_temperature(lat, lng, grid)
        diff = round(temp - s["mean"], 2)
        print(f"{zone:<20} {temp:>18.1f}  {diff:+.2f}")
