"""Step 1.9 (optional) — Traffic volume (D5) as an extra model feature.

Run: python -m crosscheck_pipeline.s09_aadt
Output: data/interim/aadt.parquet (seg_id, adt, log_aadt, aadt_imputed).
It also retrains with and without the feature and tells you whether to turn config.USE_AADT on:
keep it only if top-10% capture improves (DESIGN §6 Step 1.9).

Matching: a traffic-count line only counts for a segment if it passes within AADT_SNAP_M of the
segment's midpoint AND runs roughly the same direction. Without the direction check, a quiet side
street that merely touches a busy road would inherit that road's traffic count.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from crosscheck_pipeline import config
from crosscheck_pipeline.s05_segments import impute_by_class
from crosscheck_pipeline.utils.arcgis import fetch_all_features

INTERIM_DIR = Path(__file__).resolve().parents[1] / "data" / "interim"
SEGMENTS_PARQUET = INTERIM_DIR / "segments.parquet"
STUDY_AREA_GPKG = INTERIM_DIR / "study_area.gpkg"
AADT_PARQUET = INTERIM_DIR / "aadt.parquet"
LABELED_PARQUET = INTERIM_DIR / "segments_labeled.parquet"


def download_adt(area) -> gpd.GeoDataFrame:
    """Traffic-count lines (ADT = average daily traffic) inside the study area's bounding box."""
    minx, miny, maxx, maxy = area.bounds
    params = {
        "where": "ADT IS NOT NULL",
        "outFields": "ADT,ROUTE_COMMON_NAME",
        "outSR": 4326,
        "geometry": f"{minx},{miny},{maxx},{maxy}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "f": "geojson",
    }
    features = fetch_all_features(config.VDOT_ADT_URL, params)
    if not features:
        return gpd.GeoDataFrame({"ADT": []}, geometry=[], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    return gdf[gdf.geometry.notna()].reset_index(drop=True)


def _direction(lines: np.ndarray, along: np.ndarray, sample_m: float) -> np.ndarray:
    """Compass-free direction (radians, 0 to pi) of each line near the given distance along it."""
    length = shapely.length(lines)
    a = shapely.line_interpolate_point(lines, np.clip(along - sample_m, 0, length))
    b = shapely.line_interpolate_point(lines, np.clip(along + sample_m, 0, length))
    angle = np.arctan2(shapely.get_y(b) - shapely.get_y(a), shapely.get_x(b) - shapely.get_x(a))
    return np.mod(angle, np.pi)


def _angle_gap(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Smallest angle between two undirected directions (radians, 0 to pi/2)."""
    diff = np.abs(a - b)
    return np.minimum(diff, np.pi - diff)


def match_adt(
    segs: gpd.GeoDataFrame, counts: gpd.GeoDataFrame,
    snap_m: float = config.AADT_SNAP_M, max_angle_deg: float = config.AADT_MAX_ANGLE_DEG,
) -> pd.Series:
    """ADT for each segment (NaN if no matching count line). Both inputs must be in a meters CRS.

    Candidates are count lines within `snap_m` of the segment's midpoint and within `max_angle_deg`
    of its direction. The closest candidate wins; ties go to the larger count.
    """
    result = pd.Series(np.nan, index=segs.index, name="adt")
    if len(counts) == 0 or len(segs) == 0:
        return result
    seg_geoms = segs.geometry.values
    count_geoms = counts.geometry.values
    mids = shapely.line_interpolate_point(seg_geoms, 0.5, normalized=True)
    seg_idx, count_idx = shapely.STRtree(count_geoms).query(mids, predicate="dwithin", distance=snap_m)
    if len(seg_idx) == 0:
        return result

    pair_counts = count_geoms[count_idx]
    distance = shapely.distance(mids[seg_idx], pair_counts)
    seg_dir = _direction(seg_geoms[seg_idx], shapely.length(seg_geoms[seg_idx]) / 2, config.AADT_DIRECTION_SAMPLE_M)
    count_dir = _direction(pair_counts, shapely.line_locate_point(pair_counts, mids[seg_idx]), config.AADT_DIRECTION_SAMPLE_M)
    parallel = _angle_gap(seg_dir, count_dir) <= np.deg2rad(max_angle_deg)

    pairs = pd.DataFrame({
        "seg": seg_idx, "distance": distance, "adt": counts["ADT"].to_numpy(dtype=float)[count_idx],
    })[parallel]
    best = pairs.sort_values(["seg", "distance", "adt"], ascending=[True, True, False]).drop_duplicates("seg")
    result.iloc[best["seg"].to_numpy()] = best["adt"].to_numpy()
    return result


def build_aadt_table(segs: gpd.GeoDataFrame, matched_adt: pd.Series) -> pd.DataFrame:
    """seg_id, adt, log_aadt, aadt_imputed. Unmatched segments get their road class's median ADT."""
    global_median = int(matched_adt.median()) if matched_adt.notna().any() else 1
    filled, imputed = impute_by_class(matched_adt, segs["highway"], {}, global_median)
    return pd.DataFrame({
        "seg_id": segs["seg_id"].to_numpy(),
        "adt": filled.to_numpy(),
        "log_aadt": np.log1p(filled.to_numpy()),
        "aadt_imputed": imputed.to_numpy(),
    })


def main() -> None:
    from crosscheck_pipeline.s07_train import evaluate_models

    segs = gpd.read_parquet(SEGMENTS_PARQUET)
    area = gpd.read_file(STUDY_AREA_GPKG).geometry.iloc[0]
    print("Downloading traffic counts...")
    counts = download_adt(area)
    print(f"{len(counts)} traffic-count lines in the study-area box; median ADT {counts['ADT'].median():,.0f}")

    matched = match_adt(segs, counts.to_crs(config.CRS_METERS))
    table = build_aadt_table(segs, matched)
    table.to_parquet(AADT_PARQUET)
    print(f"Matched {matched.notna().sum()} of {len(segs)} segments ({matched.notna().mean():.1%}); the rest are estimated.")
    by_class = pd.DataFrame({"highway": segs["highway"], "matched": matched.notna()}).groupby("highway")["matched"].mean()
    print("Share matched by class:", by_class.round(2).to_dict())

    labeled = gpd.read_parquet(LABELED_PARQUET).merge(table, on="seg_id")
    without = evaluate_models(labeled, use_aadt=False)["full"]
    with_aadt = evaluate_models(labeled, use_aadt=True)["full"]
    print("\nFull model, spatial cross-validation:")
    print(pd.DataFrame({"without AADT": without, "with AADT": with_aadt}).round(3).to_string())
    gain = with_aadt["top10_capture"] - without["top10_capture"]
    verdict = "KEEP: set USE_AADT = True in config.py" if gain > 0 else "DROP: leave USE_AADT = False"
    print(f"\nTop-10% capture changes by {gain:+.3f}. {verdict}")


if __name__ == "__main__":
    main()
