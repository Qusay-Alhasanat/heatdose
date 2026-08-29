# HeatDose

**Continuous hyperlocal heat-exposure tracking for outdoor worker crews in Phoenix, AZ — built on real FortyGuard temperature data.**

🔗 **Live demo:** [heatdose.vercel.app](https://heatdose.vercel.app/) · **API:** [heatdose-production.up.railway.app](https://heatdose-production.up.railway.app/api/health) · **Video:** _added before final submission_

---

## The problem

Operations managers running outdoor crews in Phoenix typically check the
weather once — before dispatching crews in the morning — and don't track
how conditions change through the shift. Our own measured FortyGuard
data shows a ~7°C swing between a 06:00 start and the early-afternoon
peak on the same day. A crew that started at dawn and is still out at
3 PM has absorbed a continuously growing thermal load that a single
morning reading never captures — and the manager has no way to see it.

**What we originally believed** was that the bigger advantage was
_spatial_ — that a hot industrial zone runs meaningfully hotter than a
shaded park at the same hour. We tested this directly against real
FortyGuard data, including satellite-verified extremes (an industrial
salvage yard vs. a 222-acre park), checked at five hours including
pre-dawn. The measured difference never exceeded 0.3°C — consistent with
published research showing air-temperature urban heat island effects are
far smaller than surface-temperature effects. We revised the product's
core claim from spatial to temporal on the strength of that evidence.
Full writeup: [`docs/methodology.md`](docs/methodology.md#what-we-measured-spatial-vs-temporal-resolution).

## The solution

HeatDose computes a **Heat Dose Index (HDI)** — the cumulative thermal
exposure a worker absorbs across a full shift, not just the temperature
at any single moment — using real hour-by-hour FortyGuard readings along
each worker's moving path. It classifies operational risk from that
accumulation, then answers the questions an operations manager actually
needs answered: who to pull off the job right now, who to reschedule,
and where the nearest reachable cool spot is — through both a live
dashboard and a natural-language agent backed by the same real data.

## The evidence

**5 of 8 workers (63%)** on our demo roster show underestimated risk
under a single-check-in baseline compared to continuous hyperlocal
tracking — using real FortyGuard temperature data, not a synthetic
assumption.

| Worker | Single Morning Check | Continuous Tracking | Missed? |
| --- | --- | --- | --- |
| W-01 | moderate (31.5) | **extreme (73.91)** | Yes |
| W-05 | moderate (43.83) | **extreme (80.25)** | Yes |
| W-07 | high (50.68) | **extreme (66.42)** | Yes |
| W-04 | moderate (43.44) | high (55.81) | Yes |
| W-02 | high (60.55) | **extreme (71.21)** | Yes |
| W-08 | extreme (65.16) | extreme (85.08) | No — already flagged |
| W-06 | high (51.6) | high (58.58) | No |

Full breakdown and methodology: [`docs/methodology.md`](docs/methodology.md).

## Business viability

**Buyer:** Safety/Operations Managers at mid-size construction and
municipal/utility contractors (50–500 outdoor workers) in Sun Belt
metros — the people who own OSHA compliance and workers'-comp exposure
for the crew, not the workers themselves.

**Why now:** OSHA's permanent federal heat standard has stalled, but its
National Emphasis Program on heat hazards was renewed through **April
2031**, and multiple states already enforce their own binding standards.
Employers carry real, current liability today, independent of the
federal rule's status.

**Cost of doing nothing:** ~$79,000 average combined direct + indirect
cost per heat prostration incident (OSHA *$afety Pays* / Public Citizen).
One prevented incident pays for a meaningful chunk of a year's
subscription many times over.

**Pricing (estimate to validate, not a confirmed figure):** $5–8 per
active outdoor worker/month (Basic) to $10–15/month (Pro, incl. the
agent) — well under wearable hardware alternatives like SlateSafety BAND
(~$640+/month/worker), and zero hardware to deploy.

Full writeup, competitive landscape, and go-to-market plan:
[`docs/business_viability.md`](docs/business_viability.md).

## Architecture

```
web/ (React + Vite + Leaflet, on Vercel)
  │  HTTP/JSON
  ▼
api/ (FastAPI, on Railway — Docker, thin transport, no business logic)
  │
  ├── data/    Heat Dose calculations, real FortyGuard integration,
  │            baseline comparison — see docs/data_contract.md
  └── agent/   LLM-driven operational Q&A (OpenAI, gpt-4o-mini,
               function calling) — 4 tools, 5-step limit, 30s timeout,
               full tool tracing
```

Every number the frontend displays traces back to real FortyGuard data
cached in `data/cache/` — the live demo has zero dependency on a
real-time API call, by design (see [`docs/api_usage.md`](docs/api_usage.md)).
Only `data/fortyguard_client.py` ever talks to the external API; every
other layer consumes the shape defined in `docs/data_contract.md`.

## Engineering decisions and trade-offs

- **Excess dose over total dose for risk classification.** Total dose
  counts all heat including benign baseline warmth and barely separates
  workers with very different real risk. Switching to excess dose
  (only the portion above a 29.4°C CDC-derived screening threshold)
  increased separation across our demo roster from a 1.14× to a 5.8×
  spread. See `docs/methodology.md`.
- **Excess dose is not normalised by shift length.** A longer shift
  genuinely accumulates more load; normalising would erase the
  cumulative signal the project is built around. Known consequence:
  long shifts in exposed zones saturate at "extreme" — treated as a
  correct outcome, not a bug, and the dashboard also shows raw dose and
  elapsed hours so a manager can distinguish "just crossed into
  extreme" from "far past it."
- **The demo runs entirely from cache, never a live API call.**
  Confirmed by FortyGuard support as the intended judging workflow —
  trial API access ends at the build deadline, before judging does.
  `USE_LIVE_API` defaults to cache; a fresh clone with no API key still
  runs the full demo.
- **Cool point search caps at ≥3°C cooler and ≤800m walking distance.**
  A "cooler" spot that costs more heat exposure to reach than it saves
  is worse than doing nothing — the cap is a safety constraint, not an
  arbitrary tuning knob.
- **The agent tool count is capped at four, deliberately.** Tool
  selection reliability degrades past four tools; a fifth
  (roster-wide summary) was considered and rejected for this reason —
  see `Agent_Brief.md` §2.
- **Why not fine-tuning / a bigger model for the agent.** The task is
  tool selection and grounded summarisation over already-computed
  numbers, not open-ended reasoning — `gpt-4o-mini` handles this
  reliably and cheaply. No fallback-to-a-different-model exists on
  failure by design: the agent returning a clear error is preferable to
  it silently degrading to a less reliable model at exactly the moment
  an answer needs to be trustworthy.

## Limitations

HDI is a screening and prioritisation tool, not a medical determination,
and is not a substitute for WBGT (the recognised occupational heat
standard) — our data source provides only one of WBGT's four inputs
(dry-bulb air temperature). Full, honest limitations list — single-factor
input, no workload/acclimatization/recovery modelling, uncalibrated
risk thresholds, hand-placed cool points, and the spatial-signal finding
above — is documented in
[`docs/methodology.md`](docs/methodology.md#limitations).

## Tech stack

| Layer | Stack |
| --- | --- |
| Data | Python, `uv`, real FortyGuard Temperature API |
| API | FastAPI, Pydantic, Docker |
| Web | React, Vite, Leaflet, deployed on Vercel |
| Agent | OpenAI (`gpt-4o-mini`), function calling, 4 tools |
| Hosting | Railway (API + agent), Vercel (web) |

## Running locally

```bash
git clone <repo-url>
cd heatdose
uv sync
uv run uvicorn api.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs. All
data/dashboard endpoints read from the committed `data/cache/` — no
FortyGuard API key required to run the demo.

To use the agent locally, add to `.env` (gitignored):

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini   # optional, this is the default
```

To pull fresh FortyGuard data (not required for the demo):

```bash
uv run python data/fortyguard_client.py --pull-day
```

Run the test suite (39 tests, no API keys required):

```bash
uv run pytest tests/ -v
```

## What doesn't work yet / known gaps

- No real GPS worker tracking — mock shift generation bridged to real
  FortyGuard temperatures (documented as a production requirement, see
  `docs/business_viability.md` §8).
- Cool point candidates are hand-placed, not sourced from live amenity
  data.
- Risk thresholds are provisional, not calibrated against clinical
  incident data (see `docs/methodology.md`).

## Documentation

- [`docs/data_contract.md`](docs/data_contract.md) — the exact shape
  every layer builds against
- [`docs/methodology.md`](docs/methodology.md) — HDI calculation,
  the spatial-to-temporal pivot, limitations, and citations
- [`docs/api_usage.md`](docs/api_usage.md) — FortyGuard API
  integration details, debugging journey, caching strategy
- [`docs/business_viability.md`](docs/business_viability.md) — buyer,
  pricing, competitive landscape, go-to-market

## Team

Built for the FortyGuard Hackathon 2026 by a 3-person team covering
data/API, agent, and web layers. AI-assisted development (Claude) was
used throughout, disclosed per submission requirements.

## License

MIT
