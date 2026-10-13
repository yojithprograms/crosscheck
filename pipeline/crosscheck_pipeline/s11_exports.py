"""Step 1.11 — Exports for the API server.

Run: python -m crosscheck_pipeline.s11_exports
Reads:  data/schools_pilot.csv, data/interim/{segments_scored,crashes}.parquet,
        data/interim/schools_used.json, models/metrics.json, server/data/graphs/*.json.gz
Writes (server/data/): schools.json, meta.json, segments/{id}.json, layers/{id}_risk.geojson,
        layers/{id}_crashes.geojson, reports/{id}.json, reports/{id}_map.png
"""
from __future__ import annotations

import gzip
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point, mapping

from crosscheck_pipeline import config
from crosscheck_pipeline.s01_schools import load_pilot
from crosscheck_pipeline.utils.reasons import ASK_ABOUT, display_road_name

PIPELINE_DIR = Path(__file__).resolve().parents[1]
INTERIM_DIR = PIPELINE_DIR / "data" / "interim"
SCORED_PARQUET = INTERIM_DIR / "segments_scored.parquet"
CRASHES_PARQUET = INTERIM_DIR / "crashes.parquet"
USED_JSON = INTERIM_DIR / "schools_used.json"
METRICS_JSON = PIPELINE_DIR / "models" / "metrics.json"
SERVER_DATA = PIPELINE_DIR.parent / "server" / "data"

# How important a road class is when picking the "cross street" in a spot's title.
CLASS_RANK = {"trunk": 6, "primary": 5, "secondary": 4, "tertiary": 3, "unclassified": 2,
              "residential": 1, "living_street": 0, "service": 0}


# ---------------------------------------------------------------- small helpers

def bbox_for(lon: float, lat: float, radius_m: float) -> list[float]:
    """[min_lon, min_lat, max_lon, max_lat] of a circle's bounding box (same flat-earth meters as the server)."""
    dlat = radius_m / 110540
    dlon = radius_m / (111320 * math.cos(math.radians(lat)))
    return [round(lon - dlon, 6), round(lat - dlat, 6), round(lon + dlon, 6), round(lat + dlat, 6)]


def entrance_point_m(school: pd.Series) -> Point:
    return gpd.GeoSeries(gpd.points_from_xy([school["entrance_lon"]], [school["entrance_lat"]]),
                         crs="EPSG:4326").to_crs(config.CRS_METERS).iloc[0]


def midpoints_m(segments_m: gpd.GeoDataFrame) -> gpd.GeoSeries:
    return gpd.GeoSeries(shapely.line_interpolate_point(segments_m.geometry.values, 0.5, normalized=True),
                         index=segments_m.index, crs=config.CRS_METERS)


def to_lonlat(points_m: gpd.GeoSeries) -> pd.DataFrame:
    wgs = points_m.to_crs("EPSG:4326")
    return pd.DataFrame({"lon": wgs.x.round(6), "lat": wgs.y.round(6)}, index=points_m.index)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------- schools.json and segments/{id}.json

def school_records(pilot: pd.DataFrame, used: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """`[{id, name, level, lat, lon, radius_m, bbox}]`; lat/lon is the entrance, radius_m the radius actually used."""
    records = []
    for _, school in pilot.iterrows():
        radius = int(used.get(school["school_id"], {}).get("radius_m", school["radius_m"]))
        records.append({
            "id": school["school_id"], "name": school["name"], "level": school["level"],
            "lat": float(school["entrance_lat"]), "lon": float(school["entrance_lon"]), "radius_m": radius,
            "bbox": bbox_for(school["entrance_lon"], school["entrance_lat"], radius),
        })
    return records


def segment_records(segments_m: gpd.GeoDataFrame) -> dict[str, dict[str, Any]]:
    """`{seg_id: {...}}` street details for the app's street card and the server's hazard logic."""
    mids = to_lonlat(midpoints_m(segments_m))
    records: dict[str, dict[str, Any]] = {}
    for row, (_, mid) in zip(segments_m.itertuples(), mids.iterrows()):
        records[row.seg_id] = {
            "name": row.name, "highway": row.highway,
            "speed_mph": int(row.speed_mph), "speed_imputed": int(row.speed_imputed),
            "lanes": int(row.lanes), "sidewalk_cov": round(float(row.sidewalk_cov), 2),
            "sidewalk_known": int(row.sidewalk_known), "signal_end": int(row.signal_end),
            "risk_pct": round(float(row.risk_pct), 1), "risk_class": row.risk_class,
            "crashes_recent": int(row.crashes_recent), "crashes_recent_ka": int(row.crashes_recent_ka),
            "crashes_prelim": int(row.crashes_prelim), "reasons": list(row.reasons),
            "mid": [float(mid["lon"]), float(mid["lat"])],
        }
    return records


# ---------------------------------------------------------------- layers

def merge_risk_layer(segments_m: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Medium and high segments merged by (name, risk_class), simplified, in lon/lat.

    Unnamed segments are not merged. The merged feature keeps the riskiest segment's id as `seg_id`,
    every merged id in `seg_ids`, the highest `risk_pct`, and the summed `crashes_recent`.
    """
    rows: list[dict[str, Any]] = []

    def feature(group: pd.DataFrame, geometry) -> dict[str, Any]:
        riskiest = group.loc[group["risk_pct"].idxmax()]
        return {
            "seg_id": riskiest["seg_id"], "seg_ids": list(group["seg_id"]), "name": riskiest["name"],
            "risk_class": riskiest["risk_class"], "risk_pct": round(float(group["risk_pct"].max()), 1),
            "crashes_recent": int(group["crashes_recent"].sum()),
            "geometry": geometry.simplify(config.LAYER_SIMPLIFY_M, preserve_topology=True),
        }

    named = segments_m[segments_m["name"] != ""]
    for _, group in named.groupby(["name", "risk_class"], sort=False):
        merged = shapely.line_merge(shapely.union_all(group.geometry.values))
        rows.append(feature(group, merged))
    for _, segment in segments_m[segments_m["name"] == ""].iterrows():
        rows.append(feature(segment.to_frame().T, segment.geometry))

    layer = gpd.GeoDataFrame(rows, geometry="geometry", crs=config.CRS_METERS)
    layer = layer.sort_values("risk_pct", ascending=False).reset_index(drop=True)
    return layer.to_crs("EPSG:4326")


def feature_collection(layer: gpd.GeoDataFrame, property_columns: list[str]) -> dict[str, Any]:
    """GeoJSON FeatureCollection with coordinates snapped to about 1 m."""
    features = []
    for _, row in layer.iterrows():
        geometry = shapely.set_precision(row.geometry, config.COORD_GRID_DEG)
        props = {c: (row[c].item() if hasattr(row[c], "item") else row[c]) for c in property_columns}
        features.append({"type": "Feature", "properties": props, "geometry": mapping(geometry)})
    return {"type": "FeatureCollection", "features": features}


def crash_collection(crashes_m: gpd.GeoDataFrame) -> dict[str, Any]:
    """Crash dots for the map. Only year, month, severity, mode, and prelim: no report numbers or exact dates."""
    recent = crashes_m[crashes_m["year"] >= config.MAP_CRASHES_FROM].to_crs("EPSG:4326")
    layer = gpd.GeoDataFrame(
        {"year": recent["year"].astype(int), "month": recent["date"].dt.month.astype(int),
         "severity": recent["severity"].astype(str), "mode": recent["mode"].astype(str),
         "prelim": recent["year"].eq(config.PRELIM_YEAR)},
        geometry=recent.geometry, crs="EPSG:4326",
    )
    return feature_collection(layer, ["year", "month", "severity", "mode", "prelim"])


# ---------------------------------------------------------------- school report data

def cross_street(segment: pd.Series, roads: pd.DataFrame) -> str | None:
    """The most important other named road touching either end of the segment (ties: the riskier one)."""
    touching = roads[roads["u"].isin([segment["u"], segment["v"]]) | roads["v"].isin([segment["u"], segment["v"]])]
    others = touching[(touching["name"] != "") & (touching["name"] != segment["name"])].copy()
    if others.empty:
        return None
    others["rank"] = others["highway"].map(CLASS_RANK).fillna(0)
    return others.sort_values(["rank", "risk_pct"], ascending=False).iloc[0]["name"]


def spot_title(segment: pd.Series, roads: pd.DataFrame) -> str:
    """"{road} near {cross street}", first letter capitalized."""
    road = display_road_name(segment["name"], segment["highway"])
    other = cross_street(segment, roads)
    title = f"{road} near {other}" if other else road
    return title[0].upper() + title[1:]


def ask_about_lines(segment: pd.Series) -> list[str]:
    """Questions to ask about a spot (DESIGN Appendix A). Estimated speeds don't trigger the speed question."""
    lines = []
    if segment["speed_mph"] >= config.FAST_MPH and not segment["speed_imputed"]:
        lines.append(ASK_ABOUT["speed"])
    if segment["lanes"] >= config.WIDE_ROAD_LANES:
        lines.append(ASK_ABOUT["lanes"])
    if segment["sidewalk_cov"] < config.NO_SIDEWALK_COV and segment["sidewalk_known"] == 1:
        lines.append(ASK_ABOUT["no_sidewalk"])
    return lines


def pick_top_spots(
    candidates: gpd.GeoDataFrame, roads: pd.DataFrame, n: int = config.TOP_SPOTS,
    min_spacing_m: float = config.TOP_SPOT_MIN_SPACING_M,
) -> list[dict[str, Any]]:
    """Top spots: riskiest first (ties: more recent crashes), greedily keeping spots at least
    `min_spacing_m` apart. `candidates` are scored segments in meters that a walking edge uses."""
    ordered = candidates.sort_values(["risk_pct", "crashes_recent"], ascending=False)
    mids = midpoints_m(ordered)
    chosen: list[int] = []
    for position, index in enumerate(ordered.index):
        point = mids.loc[index]
        if all(point.distance(mids.loc[ordered.index[c]]) >= min_spacing_m for c in chosen):
            chosen.append(position)
        if len(chosen) == n:
            break
    picked = ordered.iloc[chosen]
    lonlat = to_lonlat(mids.loc[picked.index])
    spots = []
    for rank, (index, segment) in enumerate(picked.iterrows(), start=1):
        spots.append({
            "rank": rank, "title": spot_title(segment, roads),
            "lat": float(lonlat.loc[index, "lat"]), "lon": float(lonlat.loc[index, "lon"]),
            "seg_id": segment["seg_id"], "risk_pct": round(float(segment["risk_pct"]), 1),
            "crashes_recent": int(segment["crashes_recent"]), "crashes_recent_ka": int(segment["crashes_recent_ka"]),
            "reasons": list(segment["reasons"]), "ask_about": ask_about_lines(segment),
        })
    return spots


def school_stats(crashes_in_radius: pd.DataFrame) -> dict[str, Any]:
    """Crash counts in the full years of SERVE_HIST, so the numbers don't shift as new months arrive."""
    first, last = config.SERVE_HIST
    window = crashes_in_radius[crashes_in_radius["year"].between(first, last)]
    return {
        "window": f"{first}–{last}", "crashes": int(len(window)), "serious_or_fatal": int(window["ka"].sum()),
        "ped": int((window["mode"] == "ped").sum()), "bike": int((window["mode"] == "bike").sum()),
    }


def render_report_map(
    path: Path, school: dict[str, Any], walk_lines: list[list[list[float]]], risky_m: gpd.GeoDataFrame,
    spots: list[dict[str, Any]],
) -> Path:
    """Schematic map for the printed report: no basemap, just walking paths, risky streets, and the top spots."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lat0 = school["lat"]
    lon_scale = math.cos(math.radians(lat0))
    fig, ax = plt.subplots(figsize=(12, 12), dpi=100)
    for line in walk_lines:
        xs, ys = zip(*line)
        ax.plot(xs, ys, color="#c8ccd0", linewidth=0.6, zorder=1)
    risky = risky_m.to_crs("EPSG:4326")
    for _, row in risky.iterrows():
        geoms = getattr(row.geometry, "geoms", [row.geometry])
        for geom in geoms:
            xs, ys = geom.xy
            if row["risk_class"] == "high":
                ax.plot(xs, ys, color="#d62828", linewidth=2.4, zorder=3)
            else:
                ax.plot(xs, ys, color="#f4a100", linewidth=1.6, linestyle=(0, (5, 3)), zorder=2)
    ax.scatter([school["lon"]], [school["lat"]], marker="*", s=700, color="#0f766e", edgecolor="white", zorder=5)
    for spot in spots:
        ax.scatter([spot["lon"]], [spot["lat"]], s=520, color="white", edgecolor="black", linewidth=1.5, zorder=6)
        ax.text(spot["lon"], spot["lat"], str(spot["rank"]), ha="center", va="center", fontsize=13,
                fontweight="bold", zorder=7)
    min_lon, min_lat, max_lon, max_lat = school["bbox"]
    ax.set_xlim(min_lon, max_lon)
    ax.set_ylim(min_lat, max_lat)
    ax.set_aspect(1 / lon_scale)
    ax.set_axis_off()
    bar_m = config.MAP_SCALE_BAR_M
    bar_deg = bar_m / (111320 * lon_scale)
    x0, y0 = min_lon + (max_lon - min_lon) * 0.04, min_lat + (max_lat - min_lat) * 0.05
    ax.plot([x0, x0 + bar_deg], [y0, y0], color="black", linewidth=4, zorder=8)
    ax.text(x0, y0 + (max_lat - min_lat) * 0.012, f"{bar_m} m", fontsize=12, zorder=8)
    ax.text(max_lon - (max_lon - min_lon) * 0.01, min_lat + (max_lat - min_lat) * 0.01, "© OpenStreetMap contributors",
            ha="right", va="bottom", fontsize=10, color="#444444", zorder=8)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- everything for one school

def read_graph(school_id: str, directory: Path = SERVER_DATA / "graphs") -> dict[str, Any]:
    with gzip.open(directory / f"{school_id}.json.gz", "rt", encoding="utf-8") as f:
        return json.load(f)


def export_school(
    school: dict[str, Any], scored_m: gpd.GeoDataFrame, crashes_m: gpd.GeoDataFrame, out: Path = SERVER_DATA
) -> dict[str, int]:
    """Write one school's segments, layers, report data, and map. Returns a few counts for printing."""
    entrance = entrance_point_m(pd.Series({"entrance_lon": school["lon"], "entrance_lat": school["lat"]}))
    mids = midpoints_m(scored_m)
    distance = mids.distance(entrance)
    radius = school["radius_m"]

    nearby = scored_m[distance <= radius + config.SEGMENTS_EXTRA_M]
    write_json(out / "segments" / f"{school['id']}.json", segment_records(nearby))

    inside = scored_m[distance <= radius]
    risky = inside[inside["risk_class"].isin(["medium", "high"])]
    layer = merge_risk_layer(risky[["seg_id", "name", "risk_class", "risk_pct", "crashes_recent", "geometry"]])
    write_json(out / "layers" / f"{school['id']}_risk.geojson",
               feature_collection(layer, ["seg_id", "seg_ids", "name", "risk_class", "risk_pct", "crashes_recent"]))

    crash_distance = crashes_m.geometry.distance(entrance)
    crashes_here = crashes_m[crash_distance <= radius]
    write_json(out / "layers" / f"{school['id']}_crashes.geojson", crash_collection(crashes_here))

    graph = read_graph(school["id"], out / "graphs")
    used_ids = {e["seg_id"] for e in graph["edges"] if e["seg_id"] is not None}
    candidates = inside[inside["seg_id"].isin(used_ids)]
    spots = pick_top_spots(candidates, scored_m)
    write_json(out / "reports" / f"{school['id']}.json", {
        "school_id": school["id"], "stats": school_stats(crashes_here), "top_spots": spots,
    })
    render_report_map(out / "reports" / f"{school['id']}_map.png", school,
                      [e["coords"] for e in graph["edges"]], risky, spots)
    return {"segments": len(nearby), "risk_features": len(layer), "crashes": len(crashes_here), "spots": len(spots)}


def meta_record(crashes: pd.DataFrame, metrics: dict[str, Any]) -> dict[str, Any]:
    last = crashes["date"].max()
    return {
        "data_through": last.strftime("%B %Y"),
        "data_through_date": last.strftime("%Y-%m-%d"),
        "windows": {"train_hist": list(config.TRAIN_HIST), "train_label": list(config.TRAIN_LABEL),
                    "serve_hist": list(config.SERVE_HIST), "map_crashes_from": config.MAP_CRASHES_FROM,
                    "prelim_year": config.PRELIM_YEAR},
        "metrics": {**metrics["cv"], "full_top10_capture": metrics["full_top10_capture"],
                    "full_lift": metrics["full_lift"]},
        "model_version": metrics["model_version"],
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> None:
    pilot = load_pilot()
    used = json.loads(USED_JSON.read_text())
    scored_m = gpd.read_parquet(SCORED_PARQUET)
    crashes = gpd.read_parquet(CRASHES_PARQUET)
    crashes_m = crashes.to_crs(config.CRS_METERS)

    schools = school_records(pilot, used)
    write_json(SERVER_DATA / "schools.json", schools)
    for school in schools:
        counts = export_school(school, scored_m, crashes_m)
        print(f"{school['id']:14s} {counts['segments']:5d} segments | {counts['risk_features']:4d} risk features | "
              f"{counts['crashes']:4d} crashes | {counts['spots']} top spots")
    write_json(SERVER_DATA / "meta.json", meta_record(crashes, json.loads(METRICS_JSON.read_text())))
    print(f"\nWrote schools.json, meta.json and per-school files to {SERVER_DATA}")


if __name__ == "__main__":
    main()
