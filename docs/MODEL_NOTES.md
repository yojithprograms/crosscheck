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
