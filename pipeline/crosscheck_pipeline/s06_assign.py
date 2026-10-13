"""Step 1.6 — Match crashes to road segments and count crashes per segment.

Run: python -m crosscheck_pipeline.s06_assign
Outputs (data/interim/): segments_labeled.parquet, crashes_matched.parquet.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

from crosscheck_pipeline import config

INTERIM_DIR = Path(__file__).resolve().parents[1] / "data" / "interim"
CRASHES_PARQUET = INTERIM_DIR / "crashes.parquet"
SEGMENTS_PARQUET = INTERIM_DIR / "segments.parquet"
STUDY_AREA_GPKG = INTERIM_DIR / "study_area.gpkg"
LABELED_PARQUET = INTERIM_DIR / "segments_labeled.parquet"
MATCHED_PARQUET = INTERIM_DIR / "crashes_matched.parquet"

COUNT_COLUMNS = [
    "hist_train", "label_count", "hist_serve", "crashes_recent", "crashes_recent_ka", "crashes_prelim",
]


def assign_crashes(
    crashes_m: gpd.GeoDataFrame, segments_m: gpd.GeoDataFrame, max_dist_m: float = config.ASSIGN_MAX_DIST_M
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Match each crash to its nearest segment within `max_dist_m`. Returns (matched, unmatched).

    Both inputs must be in a meters CRS. Ties go to the first segment found.
    """
    joined = gpd.sjoin_nearest(
        crashes_m, segments_m[["seg_id", "geometry"]], how="left", max_distance=max_dist_m, distance_col="dist_m"
    )
    joined = joined[~joined.index.duplicated(keep="first")]
    matched = joined[joined["seg_id"].notna()].drop(columns="index_right").reset_index(drop=True)
    unmatched = crashes_m.loc[joined.index[joined["seg_id"].isna()]].reset_index(drop=True)
    return matched, unmatched


def _count_between(matched: gpd.GeoDataFrame, first_year: int, last_year: int | None = None, *, ka_only: bool = False) -> pd.Series:
    mask = matched["year"] >= first_year
    if last_year is not None:
        mask &= matched["year"] <= last_year
    if ka_only:
        mask &= matched["ka"]
    return matched[mask].groupby("seg_id").size()


def add_crash_counts(segments: gpd.GeoDataFrame, matched: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add the per-segment crash counts (and the label `y`) described in DESIGN §6 Step 1.6."""
    counts = {
        "hist_train": _count_between(matched, *config.TRAIN_HIST),
        "label_count": _count_between(matched, *config.TRAIN_LABEL),
        "hist_serve": _count_between(matched, *config.SERVE_HIST),
        "crashes_recent": _count_between(matched, config.MAP_CRASHES_FROM),
        "crashes_recent_ka": _count_between(matched, config.MAP_CRASHES_FROM, ka_only=True),
        "crashes_prelim": _count_between(matched, config.PRELIM_YEAR, config.PRELIM_YEAR),
    }
    out = segments.copy()
    for column, series in counts.items():
        out[column] = out["seg_id"].map(series).fillna(0).astype(int)
    out["y"] = (out["label_count"] > 0).astype(int)
    return out


def main() -> None:
    crashes = gpd.read_parquet(CRASHES_PARQUET).to_crs(config.CRS_METERS)
    segments = gpd.read_parquet(SEGMENTS_PARQUET)
    area = gpd.read_file(STUDY_AREA_GPKG).to_crs(config.CRS_METERS).geometry.iloc[0]

    in_area = crashes[crashes.within(area)].reset_index(drop=True)
    print(f"{len(crashes)} crashes downloaded; {len(in_area)} inside the study area.")

    matched, unmatched = assign_crashes(in_area, segments)
    share = len(matched) / len(in_area)
    print(f"Matched {len(matched)} of {len(in_area)} crashes ({share:.1%}) within {config.ASSIGN_MAX_DIST_M} m of a segment.")
    print(f"Median match distance: {matched['dist_m'].median():.1f} m; "
          f"90th percentile: {matched['dist_m'].quantile(0.9):.1f} m")
    print("Matched share by mode:",
          {m: f"{(matched['mode'] == m).sum() / (in_area['mode'] == m).sum():.1%}" for m in ("ped", "bike")})
    if len(unmatched):
        print("\nMost common street names among the unmatched (usually freeways or bad locations):")
        print(unmatched["street"].fillna("(none)").value_counts().head(8).to_string())
    if share < 0.90:
        print("\nWARNING: fewer than 90% matched. Check that both layers are in meters and plot some unmatched crashes.")

    labeled = add_crash_counts(segments, matched)
    labeled.to_parquet(LABELED_PARQUET)
    matched.to_parquet(MATCHED_PARQUET)
    print(f"\nSaved {LABELED_PARQUET.name} ({len(labeled)} segments) and {MATCHED_PARQUET.name} ({len(matched)} crashes).")

    print(f"\nSegments with a crash in {config.TRAIN_LABEL[0]}–{config.TRAIN_LABEL[1]} (label y=1): "
          f"{labeled['y'].sum()} of {len(labeled)} ({labeled['y'].mean():.1%})")
    print("Crashes counted per window:", {c: int(labeled[c].sum()) for c in COUNT_COLUMNS})


if __name__ == "__main__":
    main()
