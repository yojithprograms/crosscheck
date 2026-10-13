"""Step 1.8 ★ — Score every segment and write plain-English reasons.

Run: python -m crosscheck_pipeline.s08_score
Reads:  data/interim/segments_labeled.parquet, models/risk_model.joblib
Writes: data/interim/segments_scored.parquet (adds risk_pct, risk_class, reasons, contribs)

How a score is made:
1. The model gives each segment a crash probability, using today's crash history (2022–2025).
2. Probabilities are turned into percentiles ("riskier than 92% of segments") because percentiles are
   easy to understand and don't depend on the probabilities being perfectly calibrated.
3. Each feature's push on the score is its coefficient × the segment's standardized value. These
   pushes add up (with the intercept) to exactly the model's log-odds, so they honestly explain it.
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd

from crosscheck_pipeline import config
from crosscheck_pipeline.s07_train import add_log_hist, load_labeled
from crosscheck_pipeline.utils.reasons import segment_reason_items

PIPELINE_DIR = Path(__file__).resolve().parents[1]
INTERIM_DIR = PIPELINE_DIR / "data" / "interim"
LABELED_PARQUET = INTERIM_DIR / "segments_labeled.parquet"
SCORED_PARQUET = INTERIM_DIR / "segments_scored.parquet"
MODEL_JOBLIB = PIPELINE_DIR / "models" / "risk_model.joblib"


def risk_classes(risk_pct: pd.Series) -> pd.Series:
    """high (top 10%), medium (next 20%), low (the rest), using HIGH_PCT and MEDIUM_PCT."""
    labels = np.select([risk_pct >= config.HIGH_PCT, risk_pct >= config.MEDIUM_PCT], ["high", "medium"], default="low")
    return pd.Series(labels, index=risk_pct.index)


def contributions(bundle: dict, features: pd.DataFrame) -> pd.DataFrame:
    """Each feature's push on each segment's risk: coefficient × standardized value.

    A positive number pushes the segment above an average segment; negative pushes it below.
    """
    pipeline = bundle["pipeline"]
    standardized = pipeline.named_steps["scale"].transform(features[bundle["features"]])
    pushes = standardized * pipeline.named_steps["lr"].coef_[0]
    return pd.DataFrame(pushes, columns=bundle["features"], index=features.index)


def score_segments(segments: gpd.GeoDataFrame, bundle: dict) -> gpd.GeoDataFrame:
    """Add risk_pct, risk_class, reasons (list of text), and contribs (JSON text) to the segments."""
    features = add_log_hist(segments, "hist_serve")          # today's history window, not the training one
    pipeline = bundle["pipeline"]
    probability = pipeline.predict_proba(features[bundle["features"]])[:, 1]

    out = segments.copy()
    out["risk_pct"] = pd.Series(probability, index=out.index).rank(pct=True) * 100
    out["risk_class"] = risk_classes(out["risk_pct"])

    pushes = contributions(bundle, features)
    # Sanity check: the pushes plus the intercept must reproduce the model's log-odds exactly.
    log_odds = pipeline.decision_function(features[bundle["features"]])
    rebuilt = pushes.sum(axis=1).to_numpy() + pipeline.named_steps["lr"].intercept_[0]
    assert np.allclose(rebuilt, log_odds, atol=1e-6), "contributions don't add up to the model's score"

    reasons, kinds = [], []
    row_columns = ["crashes_recent", "crashes_recent_ka", "speed_mph", "speed_imputed", "lanes", "sidewalk_cov",
                   "sidewalk_known", "highway", "length_m", "marked_crossings", "bus_stops_200m"]
    if "log_aadt" in bundle["features"]:      # traffic volume is part of this model (Step 1.9)
        row_columns += ["adt", "aadt_imputed"]
    rows = out[row_columns].to_dict("records")
    for row, push, risk_class in zip(rows, pushes.to_dict("records"), out["risk_class"]):
        items = segment_reason_items(row, push, risk_class)
        reasons.append([item.text for item in items])
        kinds.append([item.kind for item in items])
    out["reasons"] = reasons
    out["reason_kinds"] = kinds
    out["contribs"] = [json.dumps({k: round(v, 3) for k, v in row.items()}) for row in pushes.to_dict("records")]
    return out


def main() -> None:
    segments = load_labeled()
    bundle = joblib.load(MODEL_JOBLIB)
    scored = score_segments(segments, bundle)
    scored.to_parquet(SCORED_PARQUET)
    print(f"Scored {len(scored)} segments with model {bundle['model_version']} -> {SCORED_PARQUET.name}\n")

    print("Risk classes:", scored["risk_class"].value_counts().to_dict())
    shown = pd.Series([k for kinds in scored["reason_kinds"] for k in kinds]).value_counts()
    print("How often each reason is shown:", shown.to_dict())
    print(f"Segments with no reasons at all: {(scored['reasons'].str.len() == 0).mean():.1%}")
    high = scored[scored["risk_class"] == "high"]
    print(f"High-risk segments with no reasons: {(high['reasons'].str.len() == 0).mean():.1%}")
    print("Reasons among HIGH-risk segments:",
          pd.Series([k for kinds in high["reason_kinds"] for k in kinds]).value_counts().to_dict(), "\n")

    named = scored[scored["name"] != ""]
    print("Riskiest named segments:")
    top = named.sort_values("risk_pct", ascending=False).head(12)
    for _, r in top.iterrows():
        print(f"  {r['risk_pct']:5.1f} {r['risk_class']:6s} {r['name'][:28]:28s} {r['highway']:11s} "
              f"crashes {r['crashes_recent']} | {'; '.join(r['reasons']) or '-'}")

    print("\nSpot check (median risk_pct over all segments with that name):")
    # OSM spells road types out ("Pickett Road"), so search for the full names.
    for needle in ["Pickett Road", "Little River Turnpike", "Main Street", "Gallows Road", "Leesburg Pike",
                   "Chain Bridge Road", "Annandale Road", "Wolf Trap Road", "Old Courthouse Road",
                   "Pine Valley Drive", "Olley Lane", "Old Creek Drive"]:
        match = named[named["name"].str.contains(needle, case=False, regex=False)]
        if len(match):
            print(f"  {needle:20s} {len(match):4d} segments | median {match['risk_pct'].median():5.1f} | "
                  f"max {match['risk_pct'].max():5.1f} | crashes since {config.MAP_CRASHES_FROM}: {match['crashes_recent'].sum()}")
        else:
            print(f"  {needle:20s} (no segments with this name in the area)")
    quiet = scored[(scored["highway"] == "residential") & (scored["length_m"] < 150) & (scored["crashes_recent"] == 0)]
    print(f"\nShort residential streets with no crashes: median risk_pct {quiet['risk_pct'].median():.1f} "
          f"({(quiet['risk_class'] == 'low').mean():.0%} low)")


if __name__ == "__main__":
    main()
