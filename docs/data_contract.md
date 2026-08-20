# Data Contract — HeatDose

This document defines the exact shape of a single data point used across
the entire project. Whether the data comes from mock data (before we have
API access) or from the real FortyGuard API (after we get access), it
**must** match this structure exactly.

Every layer (Data, Agent, Web) builds against this contract, not against
the API directly — except `data/fortyguard_client.py`, which is the only
file responsible for producing data in this shape from a real source.

## Shape

```json
{
  "worker_id": "W-01",
  "location": {
    "lat": 33.4484,
    "lng": -112.0740
  },
  "timestamp": "2025-07-15T14:00:00",
  "temp_c": 46.2
}
```

## Field Reference

| Field | Type | Description |
| --- | --- | --- |
| `worker_id` | string | Unique identifier for a worker (e.g. `"W-01"`, `"W-02"`) |
| `location.lat` | float | Latitude in decimal degrees |
| `location.lng` | float | Longitude in decimal degrees |
| `timestamp` | string | ISO 8601 format (`YYYY-MM-DDTHH:MM:SS`) |
| `temp_c` | float | Ambient temperature in **Celsius** |

## Fixed Rules

- Temperature is **always Celsius**. No component converts to Fahrenheit
  internally — conversion (if ever needed) happens only at the display
  layer in `web/`.
- A worker's full shift is represented as an **ordered list** of these
  objects, sorted chronologically by `timestamp`.
- Field names never change between mock data and real API data. If the
  real FortyGuard API returns a different shape, `fortyguard_client.py`
  is responsible for transforming it into this exact contract before
  passing it to any other layer.
- Coordinates always use `lat` / `lng` (not `latitude` / `longitude`,
  not `lon`).

## Example — one worker's shift (3 points)

```json
[
  {
    "worker_id": "W-01",
    "location": {"lat": 33.4484, "lng": -112.0740},
    "timestamp": "2025-07-15T10:00:00",
    "temp_c": 38.5
  },
  {
    "worker_id": "W-01",
    "location": {"lat": 33.4501, "lng": -112.0712},
    "timestamp": "2025-07-15T12:00:00",
    "temp_c": 43.1
  },
  {
    "worker_id": "W-01",
    "location": {"lat": 33.4522, "lng": -112.0688},
    "timestamp": "2025-07-15T14:00:00",
    "temp_c": 46.2
  }
]
```

## Ownership

| File | Responsible for |
| --- | --- |
| `data/mock_data.py` | Generating fake worker shifts in this exact shape (temp_c is synthetic and discarded after bridging — see `real_shift_builder.py`) |
| `data/fortyguard_client.py` | Producing this exact shape from the real API (owned by Qusay) |
| `data/real_shift_builder.py` | Replacing `mock_data.py`'s synthetic `temp_c` with a real FortyGuard reading, per point, via nearest-tile lookup. Output is contract-compliant and is what every downstream file actually uses |
| `data/hdi.py` | Consuming a list of these objects, returning Heat Dose Index scores (total and excess) |
| `data/baseline.py` | Consuming bridged (real-temperature) shifts to compare continuous hyperlocal tracking against a single-check-in baseline |
| `data/worker_status.py` | Aggregating one worker's bridged shift into a single status dict for the Agent layer |
| `agent/tools.py` | Reading `worker_status.py`/`baseline.py`/`cool_points.py` output, never talking to the API or `fortyguard_client.py` directly |
| `web/` | Rendering this shape on the dashboard |

## Cool Point (rest / shade candidate location)

Used by `data/cool_points.py` and consumed by the Agent's
"suggest a cooler spot" tool. Represents a candidate rest location a
worker could be routed to.

### Shape

```json
{
  "point_id": "CP-01",
  "zone_type": "park_shaded",
  "location": {
    "lat": 33.4720,
    "lng": -112.0450
  },
  "temp_c": 39.8
}
```

### Field Reference

| Field | Type | Description |
| --- | --- | --- |
| `point_id` | string | Unique identifier for a candidate location (e.g. `"CP-01"`) |
| `zone_type` | string | One of the zone keys defined in `mock_data.py` (e.g. `"park_shaded"`, `"canal_greenway"`) |
| `location.lat` | float | Latitude in decimal degrees |
| `location.lng` | float | Longitude in decimal degrees |
| `temp_c` | float | Current ambient temperature at this point, in Celsius — time-dependent, computed for a specific hour |

### Fixed Rules

- Same coordinate and temperature conventions as the worker data point
  above: `lat`/`lng`, Celsius, no exceptions.
- `temp_c` is not static — it must be computed for the hour being
  queried, using the same zone-based model as worker shifts
  (`temp_at()` in `mock_data.py`). A cool point's temperature changes
  throughout the day exactly like a worker's does.
- `find_nearest_cool_point()` output additionally includes `temp_diff_c`
  and `distance_m`, which are derived at query time and are not part of
  the stored candidate shape above.

### Ownership

| File | Responsible for |
| --- | --- |
| `data/cool_points.py` | Defining candidate points and finding the nearest eligible one for a given worker |
| `agent/tools.py` | Calling `find_nearest_cool_point()`, never computing distances or eligibility itself |
