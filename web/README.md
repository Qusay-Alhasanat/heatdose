# web/ — HeatDose Dashboard

React + Vite + Leaflet frontend. Talks only to `api/` over HTTP — never
imports from `data/` or `agent/` directly.

**Live:** <https://heatdose.vercel.app>

## Structure

```
src/
├── api/
│   └── client.js       — single source of truth for the API base URL
├── components/
│   ├── MapView.jsx      — worker locations on a Leaflet map
│   ├── WorkerList.jsx    — roster sorted by risk
│   ├── ComparisonView.jsx — headline stat + single-check vs continuous table
│   ├── AgentPanel.jsx    — chat UI for the LLM agent, shows tool_trace
│   └── ThermalScale.jsx  — the shared low→extreme colour legend strip
└── App.jsx               — tab navigation (Dashboard / Impact / Ask)
```

## Design system

Dark navy base (`--bg-base`), thermal risk scale (`--risk-low` through
`--risk-extreme`) reused consistently across the map, list, and table —
see `src/index.css` for the full token set. Typography: Space Grotesk
(headings) + IBM Plex Sans (body) + IBM Plex Mono (all numeric data).

## Run locally

```
npm install
npm run dev
```

Talks to the live API (`https://heatdose-production.up.railway.app`)
by default — no local backend needed to develop the UI. Change
`BASE_URL` in `src/api/client.js` to point at a local `api/` instance
if needed.

## Important framing note

The comparison in `ComparisonView.jsx` is a **temporal** comparison
(single morning check vs. continuous tracking), not spatial/location.
See the root `README.md`'s "What we measured" reference before writing
any new copy that explains it.
