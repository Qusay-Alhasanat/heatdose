# Methodology — Heat Dose Index (HDI)

## What HDI measures

The project computes two related metrics for each worker's shift: **total
dose** and **excess dose**. Both quantify **cumulative** thermal exposure
across a full shift, rather than the temperature at any single moment —
but they answer different questions, and only one drives risk
classification.

Both use trapezoidal accumulation. For each consecutive pair of readings
in a worker's shift, we take the average of the two values and multiply
by the time elapsed between them. Summing these segments across the shift
produces the score.

```
Total dose   = Σ [ (T_i + T_i+1) / 2 × (t_i+1 − t_i) ]
Excess dose  = Σ [ (E_i + E_i+1) / 2 × (t_i+1 − t_i) ],  E_i = max(0, T_i − 29.4)

where T is temperature in °C and t is time in hours
```

Both are expressed in **°C·hours**.

**Total dose** counts all heat the worker was exposed to, including
benign baseline warmth. It is useful as context and for display, but it
is a poor basis for risk classification: a worker who spent a shift at a
mild 33 °C accumulates a large number that has little to do with actual
danger.

**Excess dose** counts only the portion of temperature above a 29.4 °C
screening threshold (see *Relationship to existing standards* below).
Time spent below the threshold contributes nothing, and does not offset
time spent above it — exposure is monotonic. This is what drives
`classify_risk()`, because it isolates the part of the signal that
actually corresponds to thermal strain.

In early testing, using total dose for classification produced almost no
separation between workers with very different exposure profiles — a
construction worker on asphalt and an inspector in shaded corridors
landed in the same risk band, because most of their accumulated heat was
harmless baseline warmth shared by both. Switching the classification
input to excess dose increased separation across our demo roster from a 1.14× spread to 5.8×.

Implementation: `data/hdi.py`
Verification: `tests/test_hdi.py`

## Why cumulative exposure

Existing occupational heat standards evaluate **instantaneous
conditions**: what is the environmental heat right now, and does it
exceed a threshold? This works well for a fixed worksite.

It works poorly for a mobile worker. A delivery rider or a maintenance
crew moves through many microclimates during a single shift — shaded
residential streets, exposed asphalt lots, industrial zones. Street-level
temperature can vary substantially across a single city at the same hour.

Two workers on the same day, in the same city, under the same forecast,
can accumulate very different thermal loads. An operations manager
looking at a single city-wide number has no way to distinguish them.

HDI addresses that gap. It is a **per-worker, per-shift** measure that
accounts for where the worker was, how hot it was there, and how long
they stayed.

This is only computable with hyperlocal, time-resolved temperature data —
in our case FortyGuard's 2-meter ambient air temperature at roughly
20-meter resolution, available hour by hour.

## Relationship to existing standards

HDI is **not** a replacement for established heat-stress metrics, and we
do not present it as one.

The recognised standard for occupational heat assessment is **WBGT**
(Wet Bulb Globe Temperature), recommended by OSHA and NIOSH. WBGT
combines four environmental factors: air temperature, humidity, radiant
heat, and air movement. A WBGT instrument uses three separate
thermometers to capture these.

Our data source provides **one of those four factors** — dry-bulb ambient
air temperature. We therefore cannot compute a true WBGT value, and we do
not claim to.

Two consequences follow, and both matter:

1. **Our temperature values are not comparable to WBGT thresholds.**
   Published WBGT limits for continuous work fall roughly in the
   25–30 °C range. Phoenix dry-bulb readings of 45 °C are a different
   quantity entirely — in arid climates, WBGT typically sits well below
   air temperature because of low humidity. Comparing the two numbers
   directly would be a methodological error.

2. **NIOSH acknowledges WBGT is often unavailable in practice**, and
   accepts Heat Index as a working alternative. A CDC review of
   occupational heat-illness cases suggests a Heat Index screening
   threshold of 85 °F (29.4 °C) can identify potentially hazardous
   workplace conditions. We use this threshold as the basis for excess
   dose — the portion of exposure that *is* meaningfully computable from
   our data.

The contribution of HDI is the **temporal and spatial dimension**, not a
better instantaneous reading. Standards tell you whether conditions are
currently unsafe. HDI tells you how much heat a specific worker has
already absorbed, and where it came from.

## Risk thresholds

Current classification bands in `classify_risk()`, applied to **excess
dose**, not total dose:

| Excess dose (°C·h) | Level |
| --- | --- |
| < 25 | low |
| 25 – 45 | moderate |
| 45 – 65 | high |
| ≥ 65 | extreme |

**These thresholds are provisional.** They were chosen to produce a
usable operational spread across a standard 4–10 hour shift, not derived
from clinical outcome data. They are exposed as constants specifically so
they can be recalibrated.

Calibrating them properly would require correlating excess dose scores
against recorded heat-illness incidents — data we do not have access to
within the scope of this project.

**Known saturation behaviour.** Excess dose is intentionally *not*
normalised by shift length — a longer shift genuinely accumulates more
thermal load, and collapsing that back to a rate would erase the
cumulative signal the whole project is built around. One consequence: in
our Phoenix summer demo scenario, workers on 8–10 hour shifts in exposed
zones reach "extreme" regardless of which exposed zone specifically. We
treat this as a correct outcome of the metric, not a calibration bug —
but it does mean the risk band alone is coarse for long shifts. The
dashboard also surfaces raw excess dose and elapsed hours, not just the
band, so an operations manager can distinguish "just crossed into
extreme" from "far past it."

## Limitations

We consider it more useful to state these plainly than to overclaim.

- **Single-factor input.** Dry-bulb air temperature only. No humidity,
  radiant load, wind, or clothing insulation.
- **No workload adjustment.** Occupational standards scale limits by
  metabolic rate — light, moderate, or heavy work. A worker digging and
  a worker driving generate very different internal heat at identical
  ambient temperature. HDI treats them the same.
- **No acclimatization modelling.** Standards distinguish acclimatized
  from unacclimatized workers, with meaningfully different limits. HDI
  does not.
- **No recovery modelling.** Real thermal strain partially dissipates
  during rest and in cooler conditions. Our accumulation is monotonic —
  it only ever increases across a shift.
- **Uncalibrated thresholds.** See above.
- **Not normalised by shift length.** See *Known saturation behaviour*
  above — a deliberate design choice with a known consequence for long
  shifts.
- **Location sampling granularity.** HDI accuracy depends on how
  frequently a worker's position is sampled. Sparse sampling will miss
  short exposures in extreme microclimates.
- **Cool point candidates are hand-placed.** Rest locations are a fixed
  set of coordinates chosen to sit within walking distance of exposed
  zones. A production system would derive them from real amenity data
  (parks, covered structures, public buildings) rather than a static list.

## Intended use

HDI is a **screening and prioritisation tool**, not a medical
determination. Its purpose is to help an operations manager answer a
question they currently cannot answer at all: *which of my workers, right
now, has accumulated the most heat today, and how far past a safe
threshold are they?*

It should complement — never replace — established safety protocols,
on-site monitoring, and supervisor judgement.

## References

- [OSHA — Heat Hazard Recognition](https://www.osha.gov/heat-exposure/hazards)
- [OSHA Technical Manual — Section III, Chapter 4: Heat Stress](https://www.osha.gov/otm/section-3-health-hazards/chapter-4)
- [LegalClarity — OSHA Heat Work/Rest Chart: WBGT Limits and Schedules](https://legalclarity.org/how-to-use-the-osha-heat-work-rest-chart/)
- [CDC/NIOSH — Heat Safety Tool App](https://www.cdc.gov/niosh/heat-stress/communication-resources/app.html)
- [CDC MMWR — Evaluation of Occupational Exposure Limits for Heat Stress in Outdoor Workers, United States 2011–2016](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6048976/)
- [PerryWeather — OSHA Heat Safety Standard for Outdoor Workers: New Rules](https://perryweather.com/resources/osha-heat-safety-rules/)
