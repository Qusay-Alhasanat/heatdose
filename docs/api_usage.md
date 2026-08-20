# FortyGuard API Usage

This document covers exactly how HeatDose uses the FortyGuard Temperature
API: which endpoint, the confirmed request/response shapes, our caching
strategy, and the quota constraints we designed around.

## Endpoint used

```
POST /v1/heatmap
```

Auth: `api-key` header (not `Authorization: Bearer`).

We use this single endpoint deliberately. `env_params`, `satellite`,
`streetview`, and `heat_intelligence` are available on our plan but are
not central to the per-worker, per-hour temperature readings the whole
project depends on — adding them would not have served the core metric,
only spent quota.

## Confirmed request shape

Confirmed against a live call, not just the docs, after debugging three
undocumented format issues (see below):

```json
{
  "polygon_aoi": {
    "type": "FeatureCollection",
    "features": [{
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [-112.092, 33.423],
          [-112.043, 33.423],
          [-112.043, 33.480],
          [-112.092, 33.480],
          [-112.092, 33.423]
        ]]
      }
    }]
  },
  "date_time": {
    "start_date": "2025-07-15",
    "start_time": "14:00",
    "filter_type": 1
  },
  "granularity": 100
}
```

Notes:

- Coordinates are `[longitude, latitude]` — the opposite of our internal
  data contract's `{"lat":..., "lng":...}`. The conversion happens only
  inside `fortyguard_client.py`.
- `start_time` must be a string in `HH:MM` format. We initially sent
  `"14"` (422 error) and integer `14` (also 422) before confirming
  `"14:00"` against the live API explorer at docs-api.fortyguard.com.
- We omit `analytic_type` entirely for our default `tcm` (raw
  temperature) use case. Including it caused a 500 Internal Server
  Error during testing; the official docs example also omits it.

## Confirmed response shape

The submit call returns:

```json
{"error": false, "status_code": 200, "message": "...",
 "data": {"activity_id": "..."}}
```

Polling `GET /v1/status/{activity_id}` returns, once complete:

```json
{"data": {"status": "Completed",
  "result": {"map_data": {...}, "stats_data": {...}}}}
```

**Important, undocumented behaviour we discovered:** a `Completed`
status can arrive with both `map_data` and `stats_data` as empty dicts
— confirmed in the official docs' own worked example, not just our own
calls. Our client keeps polling until one of them contains real content,
rather than treating the first `Completed` status as final.

Each tile in `map_data.features` looks like:

```json
{
  "properties": {
    "tile_id": 0,
    "average_temperature": 39.58,
    "min_temperature": 39.58,
    "max_temperature": 39.58
  },
  "geometry": {"type": "Polygon", "coordinates": [[...]]}
}
```

We read `properties.average_temperature` — not `temperature`, which is
what we initially (incorrectly) assumed.

**Real example from our own pull** (2025-07-15, 14:00, granularity=100,
~2,719 tiles returned for the ~9.5 sq mi study polygon): temperatures
across the grid ranged from roughly 39.6°C to 39.8°C at that hour — a
range under 0.3°C across the entire study area. This surprised us; see
`docs/methodology.md`'s "What we measured" section for what we tested
next and why the spatial signal is this small at this hour, and how it
changed our baseline comparison methodology.

## Debugging journey — three issues, in the order we hit them

1. **`n_cells: 0` with no error.** Task completed successfully but
   returned zero tiles. Root cause: an earlier `start_time` format was
   silently rejected by the parser. This was the hardest issue to spot:
   no error message, just an empty result.
2. **422 Unprocessable Entity.** Switching `start_time` to an integer
   `14` produced `"Input should be a valid string"`. Switching to the
   digit-only string `"14"` also failed with the same error.
3. **500 Internal Server Error.** With `start_time` finally correct as
   `"14:00"`, including `"analytic_type": "tcm"` in the payload caused
   a server error. Removing the key (relying on the API's own default)
   fixed it.

We resolved this by testing directly against the live API explorer
(docs-api.fortyguard.com/docs), which surfaces the official worked
example — the source of truth that resolved all three issues at once.

## Batch pulling — `pull_hours()`

`data/fortyguard_client.py` exposes `pull_hours(date, hours)`: a plain
loop over `get_temperature_grid()` for an explicit list of hours,
cache-first per hour. It takes no knowledge of workers or rosters —
deciding *which* hours are needed is business logic that stays in
`data/real_shift_builder.py`, keeping this file a generic API boundary
(see `PROJECT_SPEC.md` section 4's one-file-swap rule).

Run with:

```
uv run python data/fortyguard_client.py --pull-day
```

This pulls the full demo roster's shift envelope — 06:00 through
18:00, 13 hours — for our fixed study date in one command. Already-cached
hours are skipped automatically, so re-running it after a partial
failure only spends credits on what's still missing.

## Caching strategy

Every successful pull is saved to `data/cache/` as JSON, keyed by date,
hour, and granularity. `get_temperature_grid()` checks the cache before
making a live call. This serves two purposes:

1. **Quota protection.** The trial enforces a **30 heatmaps/day limit**,
   confirmed directly in the account dashboard's Usage tab (resets to
   0/30 each day — not documented in the API docs or FAQ). Pulling the
   full 13-hour roster envelope costs 13 calls, well inside a single
   day's quota with room for re-runs. Debugging the three issues above
   consumed a handful more; caching means we never pay twice for the
   same (date, hour) pair regardless.
2. **Judging reliability.** The live demo reads exclusively from
   `data/cache/` at runtime — it never depends on a real-time API call
   during judging. This is confirmed by FortyGuard support as the
   intended workflow, not a workaround (trial API access ends when the
   build window closes, before judging does).

## Quota budget

With a 30/day cap, pulling the full demo roster's shift envelope
(06:00–18:00, all seven zones in a single ~9.5 sq mi polygon) costs
exactly 13 calls — one per distinct hour needed, regardless of how many
workers are on the roster, since a single hourly grid covers the whole
area at once. Adding more workers to the roster costs zero additional
calls as long as their shifts fall within an already-pulled hour range.

## Which analysis layer we use

We use `tcm` (raw temperature, the API's default — `analytic_type`
omitted from the request) rather than the built-in `exceedance` or
`persistence` analytics. Those require `filter_type=4` (a multi-day
window) and are built for a fixed area accumulating over time — a
different problem shape from what we need (a moving worker's exposure
within a single shift). We compute our own accumulation
(`calculate_excess_dose()` in `data/hdi.py`) on top of raw per-hour,
per-tile readings instead. See `docs/methodology.md` for the full
reasoning.
