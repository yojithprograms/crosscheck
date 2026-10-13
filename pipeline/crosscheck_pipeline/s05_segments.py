"""Step 1.5 — Road segments and features.

Run: python -m crosscheck_pipeline.s05_segments
Output: data/interim/segments.parquet (GeoParquet in CRS_METERS), one row per road segment.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
import shapely

from crosscheck_pipeline import config

INTERIM_DIR = Path(__file__).resolve().parents[1] / "data" / "interim"
DRIVE_GRAPHML = INTERIM_DIR / "drive.graphml"
SIDEWALKS_GPKG = INTERIM_DIR / "sidewalks.gpkg"
CROSSWALKS_GPKG = INTERIM_DIR / "county_crosswalks.gpkg"
POINTS_GPKG = INTERIM_DIR / "osm_points.gpkg"
GAPS_GPKG = INTERIM_DIR / "sidewalk_gaps.gpkg"
OUT_PARQUET = INTERIM_DIR / "segments.parquet"

CLASS_COLUMNS = [f"class_{c}" for c in config.ROAD_CLASSES]
# Model inputs from this step (Step 1.7 adds log_hist, and optionally log_aadt / aadt_imputed).
FEATURE_COLUMNS = [
    "log_length", "speed_mph", "speed_imputed", "lanes", "lanes_imputed", "oneway", *CLASS_COLUMNS,
    "sidewalk_cov", "sidewalk_known", "no_sidewalk_fast", "signal_end", "marked_crossings", "bus_stops_200m",
]


# ---------------------------------------------------------------- tag cleaning

def as_list(value: Any) -> list[Any]:
    """OSM tag values can be a single value, a list, or missing; always return a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set, np.ndarray)):
        return list(value)
    if isinstance(value, float) and np.isnan(value):
        return []
    return [value]


def clean_highway(value: Any) -> str:
    """First value; `*_link` becomes its base class (motorway_link -> motorway)."""
    items = as_list(value)
    if not items:
        return ""
    return str(items[0]).removesuffix("_link")


def clean_name(value: Any) -> str:
    """Join list values with ' / '; missing -> empty string."""
    names = [str(n).strip() for n in as_list(value) if str(n).strip()]
    return " / ".join(dict.fromkeys(names))


def largest_int(value: Any) -> float:
    """Largest whole number found in a tag value ("35 mph", "2;3", ["25 mph", "30 mph"]); NaN if none."""
    numbers = [int(n) for item in as_list(value) for n in re.findall(r"\d+", str(item))]
    numbers = [n for n in numbers if n > 0]
    return float(max(numbers)) if numbers else float("nan")


def parse_oneway(value: Any) -> int:
    for item in as_list(value):
        if item is True or str(item).strip().lower() in {"yes", "true", "1", "-1", "reverse"}:
            return 1
    return 0


def impute_by_class(
    known: pd.Series, highway: pd.Series, fallback: dict[str, int], default: int
) -> tuple[pd.Series, pd.Series]:
    """Fill missing values with the median of known values in the same highway class.

    Classes with no known values use `fallback`; classes missing from `fallback` use `default`.
    Returns (filled integer values, 0/1 flag marking which values were estimated).
    """
    medians = known.groupby(highway).median()
    guess = highway.map(medians).fillna(highway.map(fallback)).fillna(default).round()
    flag = known.isna().astype(int)
    return known.fillna(guess).astype(int), flag


def edges_table(graph) -> gpd.GeoDataFrame:
    """Undirected road graph -> one cleaned row per segment, in CRS_METERS."""
    undirected = ox.convert.to_undirected(graph)
    raw = ox.convert.graph_to_gdfs(undirected, nodes=False).reset_index()

    def col(name: str) -> pd.Series:
        return raw[name] if name in raw.columns else pd.Series([None] * len(raw), index=raw.index)

    highway = col("highway").map(clean_highway)
    segs = gpd.GeoDataFrame(
        {
            "seg_id": [f"{min(u, v)}-{max(u, v)}-{k}" for u, v, k in zip(raw["u"], raw["v"], raw["key"])],
            "u": raw["u"],
            "v": raw["v"],
            "key": raw["key"],
            "name": col("name").map(clean_name),
            "highway": highway,
            "length_m": raw["length"].astype(float),
            "speed_raw": col("maxspeed").map(largest_int),
            "lanes_raw": col("lanes").map(largest_int),
            "oneway": col("oneway").map(parse_oneway),
        },
        geometry=raw.geometry,
        crs=raw.crs,
    )
    segs = segs[~segs["highway"].isin(config.DROP_HIGHWAYS)].reset_index(drop=True)
    segs["speed_mph"], segs["speed_imputed"] = impute_by_class(
        segs.pop("speed_raw"), segs["highway"], config.FALLBACK_SPEED_MPH, config.DEFAULT_SPEED_MPH)
    segs["lanes"], segs["lanes_imputed"] = impute_by_class(
        segs.pop("lanes_raw"), segs["highway"], config.FALLBACK_LANES, config.DEFAULT_LANES)
    return segs.to_crs(config.CRS_METERS)


# ---------------------------------------------------------------- spatial features

def count_near(segs: np.ndarray, targets: np.ndarray, distance_m: float) -> np.ndarray:
    """For each segment, how many target geometries (points or lines) are within `distance_m` of it."""
    if len(targets) == 0:
        return np.zeros(len(segs), dtype=int)
    query_idx, _ = shapely.STRtree(targets).query(segs, predicate="dwithin", distance=distance_m)
    return np.bincount(query_idx, minlength=len(segs))


def sidewalk_coverage(
    segs: np.ndarray, seg_lengths: np.ndarray, sidewalks: np.ndarray,
    buffer_m: float = config.SIDEWALK_BUFFER_M, chunk: int = config.SEGMENT_CHUNK,
) -> np.ndarray:
    """Sidewalk length inside a flat-cap buffer around each segment ÷ (2 × segment length), capped at 1.

    About 1.0 = sidewalks on both sides, 0.5 = one side.
    """
    covered = np.zeros(len(segs))
    if len(sidewalks):
        tree = shapely.STRtree(sidewalks)
        for start in range(0, len(segs), chunk):
            buffers = shapely.buffer(segs[start:start + chunk], buffer_m, cap_style="flat")
            query_idx, tree_idx = tree.query(buffers, predicate="intersects")
            if len(query_idx):
                inside = shapely.length(shapely.intersection(buffers[query_idx], sidewalks[tree_idx]))
                covered[start:start + len(buffers)] = np.bincount(query_idx, weights=inside, minlength=len(buffers))
    return np.minimum(covered / (2 * np.maximum(seg_lengths, config.MIN_SEGMENT_LENGTH_M)), 1.0)


def inside_any(segs: np.ndarray, polygons: np.ndarray) -> np.ndarray:
    """True where a segment's midpoint falls inside any of the polygons."""
    flags = np.zeros(len(segs), dtype=bool)
    if len(polygons):
        mids = shapely.line_interpolate_point(segs, 0.5, normalized=True)
        query_idx, _ = shapely.STRtree(polygons).query(mids, predicate="within")
        flags[query_idx] = True
    return flags


def nodes_near_signals(nodes: gpd.GeoDataFrame, signals: np.ndarray) -> set[int]:
    """Ids of road-graph nodes within SIGNAL_SNAP_M of a traffic signal."""
    if len(signals) == 0:
        return set()
    node_idx, _ = shapely.STRtree(signals).query(nodes.geometry.values, predicate="dwithin", distance=config.SIGNAL_SNAP_M)
    return set(nodes.index[np.unique(node_idx)])


def add_features(
    segs: gpd.GeoDataFrame,
    *,
    sidewalks_m: np.ndarray,
    crosswalks_m: np.ndarray,
    crossing_points_m: np.ndarray,
    bus_stops_m: np.ndarray,
    signal_nodes: set[int],
    gap_polygons_m: np.ndarray,
) -> gpd.GeoDataFrame:
    """Add every Step 1.5 feature column (see DESIGN §6 Step 1.5)."""
    geoms = segs.geometry.values
    out = segs.copy()
    out["log_length"] = np.log(out["length_m"] + 1)
    for road_class in config.ROAD_CLASSES:
        out[f"class_{road_class}"] = (out["highway"] == road_class).astype(int)
    out["sidewalk_cov"] = sidewalk_coverage(geoms, out["length_m"].to_numpy(), sidewalks_m)
    out["sidewalk_known"] = (~inside_any(geoms, gap_polygons_m)).astype(int)
    out["no_sidewalk_fast"] = (
        (out["sidewalk_cov"] < config.NO_SIDEWALK_COV) & (out["speed_mph"] >= config.FAST_MPH)
    ).astype(int)
    out["signal_end"] = (out["u"].isin(signal_nodes) | out["v"].isin(signal_nodes)).astype(int)
    out["marked_crossings"] = (
        count_near(geoms, crossing_points_m, config.CROSSING_SNAP_M)
        + count_near(geoms, crosswalks_m, config.CROSSING_SNAP_M)
    )
    out["bus_stops_200m"] = np.minimum(
        count_near(geoms, bus_stops_m, config.BUS_STOP_RADIUS_M), config.BUS_STOP_CAP)
    return out


def estimated_share_table(segs: pd.DataFrame) -> pd.DataFrame:
    """Share of segments for each yes/no feature, so you can see how much was estimated."""
    rows = {
        "speed_mph estimated": segs["speed_imputed"].mean(),
        "lanes estimated": segs["lanes_imputed"].mean(),
        "sidewalk unknown (county gap)": 1 - segs["sidewalk_known"].mean(),
        "no sidewalk (cov < NO_SIDEWALK_COV)": (segs["sidewalk_cov"] < config.NO_SIDEWALK_COV).mean(),
        "no sidewalk on a fast road": segs["no_sidewalk_fast"].mean(),
        "signal at an end": segs["signal_end"].mean(),
        "has a marked crossing nearby": (segs["marked_crossings"] > 0).mean(),
        "has a bus stop within 200 m": (segs["bus_stops_200m"] > 0).mean(),
        "one-way": segs["oneway"].mean(),
    }
    return pd.DataFrame({"share": pd.Series(rows)}).assign(share=lambda t: (t["share"] * 100).round(1))


def build_segments(
    graph, sidewalks: gpd.GeoDataFrame, crosswalks: gpd.GeoDataFrame, points: gpd.GeoDataFrame,
    gaps: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    segs = edges_table(graph)
    nodes = ox.convert.graph_to_gdfs(ox.convert.to_undirected(graph), edges=False).to_crs(config.CRS_METERS)
    pts = points.to_crs(config.CRS_METERS)
    return add_features(
        segs,
        sidewalks_m=sidewalks.to_crs(config.CRS_METERS).geometry.values,
        crosswalks_m=crosswalks.to_crs(config.CRS_METERS).geometry.values,
        crossing_points_m=pts[pts["highway"] == "crossing"].geometry.values,
        bus_stops_m=pts[pts["highway"] == "bus_stop"].geometry.values,
        signal_nodes=nodes_near_signals(nodes, pts[pts["highway"] == "traffic_signals"].geometry.values),
        gap_polygons_m=gaps.to_crs(config.CRS_METERS).geometry.values,
    )


def main() -> None:
    print("Loading the road graph and layers...")
    graph = ox.io.load_graphml(DRIVE_GRAPHML)
    segs = build_segments(
        graph,
        gpd.read_file(SIDEWALKS_GPKG),
        gpd.read_file(CROSSWALKS_GPKG),
        gpd.read_file(POINTS_GPKG),
        gpd.read_file(GAPS_GPKG),
    )
    missing = segs[FEATURE_COLUMNS].isna().sum()
    assert missing.sum() == 0, f"missing values in feature columns:\n{missing[missing > 0]}"
    assert segs["seg_id"].is_unique, "duplicate seg_id"
    segs.to_parquet(OUT_PARQUET)
    print(f"Saved {len(segs)} segments -> {OUT_PARQUET}\n")
    print("Segments by highway class:")
    print(segs["highway"].value_counts().to_string(), "\n")
    print("Share of segments (%):")
    print(estimated_share_table(segs).to_string(), "\n")
    print("Feature summary:")
    print(segs[["length_m", "speed_mph", "lanes", "sidewalk_cov", "marked_crossings", "bus_stops_200m"]]
          .describe().round(2).to_string())
    print("\nNo missing values in any feature column.")


if __name__ == "__main__":
    main()
