# HeatDose

**Continuous hyperlocal heat-exposure tracking for outdoor worker crews in Phoenix, AZ.**

> A single morning weather check tells you nothing about the 7°C a crew
> absorbs between sunrise and the afternoon peak. HeatDose tracks it —
> hour by hour, worker by worker, from real FortyGuard data.

🔗 **Live demo:** [heatdose.vercel.app](https://heatdose.vercel.app/) · **API:** [heatdose-production.up.railway.app](https://heatdose-production.up.railway.app/api/health)

---

## The headline number

**5 of 8 workers (63%)** on our demo roster show underestimated risk
under a single-check-in baseline compared to continuous hyperlocal
tracking — using real FortyGuard temperature data, not a synthetic
assumption.

| | Single Morning Check | Continuous Tracking |
| --- | --- | --- |
| W-01 | moderate (31.5) | **extreme (73.91)** |
| W-05 | moderate (43.83) | **extreme (80.25)** |
| W-07 | high (50.68) | **extreme (66.42)** |

Full breakdown: [`docs/methodology.md`](docs/methodology.md)

---

## The problem

Operations managers running outdoor crews in Phoenix typically check
the weather once — before dispatching crews in the morning — and don't
track how conditions change through the shift. Our own measured data
shows a ~7°C swing between a 06:00 start and the early-afternoon peak
on the same day. A crew that started at dawn and is still out at 3 PM
has absorbed a continuously growing thermal load that a single reading
never captures.

**What we originally believed** was that the bigger advantage was
*spatial* — that a hot industrial zone runs meaningfully hotter than a
shaded park at the same hour. We tested this directly against real
FortyGuard data, including satellite-verified extremes (an industrial
salvage yard vs. a 222-acre park), checked at five hours including
pre-dawn. The measured difference never exceeded 0.3°C — consistent
with published research showing air-temperature urban heat island
effects are far smaller than surface-temperature effects. We revised
the product's core claim from spatial to temporal on the strength of
that evidence. Full writeup: [`docs/methodology.md`](docs/methodology.md#what-we-measured-spatial-vs-temporal-resolution).

## What HeatDose does

- Pulls real hour-by-hour temperature data from the FortyGuard API for
  a Phoenix study area
- Computes a **Heat Dose Index** (total and excess exposure) for each
  worker's shift, using trapezoidal accumulation
- Classifies risk (`low` / `moderate` / `high` / `extreme`) based on
  accumulated exposure above a CDC-derived screening threshold
- Compares continuous tracking against a single-check-in baseline to
  quantify exactly how much risk a standard approach misses
- Suggests reachable cooler rest points for at-risk workers
- (In progress) An LLM agent that answers operational questions —
  "who should I pull right now?" — backed by the same real data

## Architecture

```
web/ (React + Vite + Leaflet, on Vercel)
  │  HTTP/JSON
  ▼
api/ (FastAPI, on Railway — Docker)
  │
  ├── data/    Heat Dose calculations, real FortyGuard integration,
  │            baseline comparison — see docs/data_contract.md
  └── agent/   LLM-driven operational Q&A (OpenAI) — in progress
```

Every number the frontend displays traces back to real FortyGuard data
cached in `data/cache/` — the live demo has zero dependency on a
real-time API call, by design (see [`docs/api_usage.md`](docs/api_usage.md)).

## Tech stack

| Layer | Stack |
| --- | --- |
| Data | Python, `uv`, real FortyGuard Temperature API |
| API | FastAPI, Pydantic, Docker |
| Web | React, Vite, Leaflet, deployed on Vercel |
| Agent | OpenAI function calling |
| Hosting | Railway (API), Vercel (web) |

## Running locally

```bash
git clone <repo-url>
cd heatdose
uv sync
uv run uvicorn api.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs. All
endpoints read from the committed `data/cache/` — no API key required
to run the demo.

To pull fresh data (requires a FortyGuard API key in `.env`):

```bash
uv run python data/fortyguard_client.py --pull-day
```

## Documentation

- [`docs/data_contract.md`](docs/data_contract.md) — the exact shape
  every layer builds against
- [`docs/methodology.md`](docs/methodology.md) — HDI calculation,
  the spatial-to-temporal pivot, limitations, and citations
- [`docs/api_usage.md`](docs/api_usage.md) — FortyGuard API
  integration details, debugging journey, caching strategy

## Team

Built for the FortyGuard Hackathon 2026 by a 3-person team covering
data/API, agent, and web layers.

## License

MIT
