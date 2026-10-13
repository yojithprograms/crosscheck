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
