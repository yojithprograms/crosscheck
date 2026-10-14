# Model notes

## Step 1.7 — Risk model (trained 2026-10-12)

**Setup.** Logistic regression on 53,131 road segments in the pilot study area (385 km² around the six pilot schools). Features: road class, speed, lanes, sidewalks, signals, crossings, bus stops, length, and crash history from 2017–2020. Target: did the segment have a pedestrian or bike crash in 2021–2024 (624 segments, 1.2%; 676 crashes). Scored with 5-fold spatial cross-validation on 2 km grid cells, so every score comes from a model that never saw that part of the map.

**Results (out-of-fold).**

| Model | ROC-AUC | PR-AUC | Top-10% capture | Lift |
|---|---|---|---|---|
| Length only | 0.650 | 0.020 | 21% | 2.1x |
| History only | 0.684 | 0.061 | 29% | 2.9x |
| Roads only | 0.876 | 0.090 | 61% | 6.1x |
| **Full** | **0.878** | **0.103** | **64%** | **6.4x** |

**What this says.** The 10% of streets the full model ranked riskiest had 64% of the 2021–2024 crashes, against 21% for "longer streets" and 29% for "streets that already had crashes". Road features do almost all of the work; adding crash history helps only a little (61% to 64%, and the log_hist coefficient is small), which makes sense because pedestrian crashes on any one street are rare and mostly don't repeat.

**Surprising signs (exposure, not danger).** Streets with sidewalks (`sidewalk_cov` +0.33), bus stops (+0.25), and signals (+0.23) show *more* crashes, because more people walk there. The model is partly measuring how many people are on the street, and it can't see foot traffic directly. `speed_mph` has a small negative coefficient: most speeds are estimates copied from the road class (75% imputed), so speed is mostly redundant with the class columns. Parking-lot service roads are the lowest risk (-0.54), and longer segments are riskier (+0.41) just by being longer.

**Limits.**
- Small sample: only 624 positive segments, about 125 per fold, so the numbers are noisy. Expect them to move if the study area grows to the whole county (`STUDY_AREA_MODE = "county"`).
- `sidewalk_cov` adds county and OSM sidewalk lengths, so a sidewalk mapped in both sources can look like two sides.
- VDOT does not guarantee its crash data is accurate or complete. Crashes on freeways were not matched to segments.

## Step 1.8 — Scores and reasons (2026-10-12)

**Scores.** Every segment gets a crash probability from the model using 2022–2025 history, turned into a percentile among all 53,131 segments in the pilot area: high is the top 10% (5,314 segments), medium the next 20% (10,626), and low the rest. Each feature's push on a score is its coefficient times the segment's standardized value, and those pushes plus the intercept add up exactly to the model's log-odds (checked in code and in a test).

**Spot checks.** The big roads come out high: Main Street (median percentile 94), Leesburg Pike (92.6), Chain Bridge Road (92.5), Gallows Road (90.3), Annandale Road (91.2), Pickett Road (88.3). Short residential streets with no crashes are low 84% of the time. Pickett Road is near Frost MS and its segments run between the 80s and 100.

**Surprises.**
- Because the weights capture exposure, the **speed reason never shows**: faster streets don't push risk up in this model, so by the "positive push" rule they can't be explained by speed. The no-sidewalk reason showed on only 136 segments for the same reason (sidewalks push risk *up*).
- With only the Appendix A reasons, 41.5% of high-risk streets had no reason at all. We added plain-words **context reasons** (road type, bus stops, crosswalks, sidewalks, length) for medium and high segments with no other reason, so every colored street has a "why". Only 18 of 15,940 colored segments fall back to the generic sentence.
- The context reasons describe what the model uses (exposure and road type), not proof of danger. S19 should keep saying the score doesn't know how many people walk each street.

## Step 1.9 — Traffic volume (2026-10-12)

VDOT's traffic-count layer (ADT, average daily traffic) matched 44.9% of segments (primary 96%, secondary 91%, tertiary 82%, trunk 83%, residential 57%, service 4%); the rest get their class's median. Matching uses the segment midpoint and requires the count line to run the same direction, so side streets that touch an arterial don't inherit its count.

| Full model | Without traffic volume | With traffic volume |
|---|---|---|
| ROC-AUC | 0.878 | 0.881 |
| PR-AUC | 0.103 | 0.105 |
| Top-10% capture | 0.641 | 0.643 |
| Lift | 6.4x | 6.4x |

By the rule in DESIGN (keep it only if capture improves) it stays on. Honestly, the gain is about two crashes out of 676, which is inside the noise. Traffic volume does become the strongest single weight (odds ratio 1.84 per standard deviation) and it adds the "About N cars a day" reason. The Step 1.7 table above was computed before this change; `models/metrics.json` now holds the numbers with traffic volume (roads-only 0.623, full 0.643).

## Steps 2.3 and 4.2 — How the two routes compare (2026-10-13)

**How we measured.** For each school, 250 random graph nodes between 300 m and 1,600 m (straight line) from the entrance were used as walking start points, and each was sent to `POST /routes` on the local server. These are spread across the map, not weighted by where students live, so treat the percentages as a rough picture.

| School | Same route | Lower-risk has fewer high-risk spots | Equal | **More** | Lower-risk has lower mean risk | Median extra time | Mean spots, fastest → lower-risk |
|---|---|---|---|---|---|---|---|
| Frost MS | 13% | 6% | 66% | 15% | 86% | 2 min | 1.12 → 1.22 |
| Woodson HS | 5% | 4% | 72% | 19% | 92% | 2 min | 1.37 → 1.52 |
| Olde Creek ES | 42% | 4% | 52% | 3% | 58% | 1 min | 0.31 → 0.30 |
| Marshall HS | 0% | 6% | 37% | **56%** | 99% | 2 min | 1.65 → 2.18 |
| Kilmer MS | 3% | 50% | 40% | 7% | 97% | 3 min | 2.12 → 1.29 |
| Lemon Road ES | 13% | 48% | 26% | 12% | 77% | 1 min | 1.38 → 0.99 |

Every percentage is a share of all 250 starts, so "Same route" + "fewer" + "Equal" + "More" adds up to 100%. "Lower mean risk" counts the starts where the two routes differ and the lower-risk one has the lower length-weighted mean risk.

**What it means.**
- The lower-risk route almost always lowers the *length-weighted mean risk* of the streets walked (77–99% of the time at the five schools with real arterials). It does what the cost function in DESIGN §7.6 asks for.
- It does **not** reliably lower the *count of high-risk spots* shown on the route cards. Only at Kilmer MS and Lemon Road ES does the count clearly drop. At Marshall HS the lower-risk route shows *more* spots than the fastest one in 56% of starts.
- Why: a "spot" is one group of hazards within 40 m along the path (DESIGN §7.7). Walking 800 m along a high-risk road is **one** spot. Crossing three high-risk roads is **three** spots. The route cost charges by meters spent on risky streets, so it will happily swap one long walk along Leesburg Pike for several crossings. Example at Marshall HS (start 38.89652, -77.20251): mean risk 84 → 48 and 2 → 5 spots, for 2,298 m → 3,246 m. Marshall HS itself is on Leesburg Pike (98th–100th percentile), so every route to it touches a high-risk road.
- The server's note already says only what is true ("…spends less of the trip on risky streets" instead of "avoids spots" when the spot count didn't drop), but the two route cards can show a bigger spot count on the lower-risk card.

**Options (not decided).**
1. Leave it. The notes are honest, and S19 explains lower-risk isn't risk-free.
2. Add an exposure number to each route (for example, the share of the route on high-risk streets) and show it on the cards next to the spot count. It matches what the route search actually optimizes. It needs one new field in the `Route` response.
3. Raise `BETA_CROSSING_M` and `GAMMA_INTERSECTION_M` so crossing risky roads costs more, which cuts spots at the price of longer detours. Re-run this comparison after any change.

## Step 4.3 — The circle shows more than we can route from (2026-10-13)

The pin picker (S7) draws a circle of `radius_m` around the school and says that is the area CrossCheck covers. The walk graph behind it (Step 1.10) is clipped to what can be reached within `radius_m` of **walking**, not **straight-line** distance. Walking routes are longer than straight lines, so the graph covers only part of the circle. We checked by sending a start point from every cell of a 200 m grid inside each circle to `POST /routes`:

| School | Radius | Routable within 0–25% of the radius | 25–50% | 50–75% | 75–100% | Whole circle |
|---|---|---|---|---|---|---|
| Frost MS | 2,400 m | 100% | 96% | 80% | 13% | 55% |
| Woodson HS | 2,400 m | 100% | 98% | 90% | 31% | 67% |
| Olde Creek ES | 1,600 m | 100% | 83% | 64% | 32% | 55% |
| Marshall HS | 2,400 m | 96% | 82% | 66% | 19% | 51% |
| Kilmer MS | 2,400 m | 100% | 96% | 67% | 16% | 53% |
| Lemon Road ES | 1,600 m | 100% | 89% | 78% | 43% | 66% |

Near the school almost everything works (82–100% within half the radius). In the outer quarter of the circle only 13–43% does. For the refused points at Marshall HS, 399 of 402 are 250 m or more from any street in the graph, so it is a coverage gap and not a snapping problem. A student who drops a pin there gets "We couldn't find a sidewalk or street near there. Try moving the pin," even in the middle of a neighborhood.

**Options (not decided).**
1. Clip each walk graph to **straight-line** distance (for example `radius_m × 1.2`, so detours can leave the circle) and keep the largest connected component. Every point in the circle can then start a route. The graphs would be about 2–3 times bigger (still under `MAX_GRAPH_EDGES`, but about 15 MB in the repo and more server memory). Re-run `python -m crosscheck_pipeline.run_all --from s10` after fixing the entrance coordinates in `schools_pilot.csv`, which needs that re-run anyway.
2. Draw the area we can really route from (for example, everything within 250 m of a graph street) instead of a circle, and disable **Start here** outside it. Honest, but the covered area is much smaller than the circle.
3. Shrink `radius_m` until the whole circle is routable. Simplest, but it covers only about 1 mile around a high school.
