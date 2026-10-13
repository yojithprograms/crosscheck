"""A tiny fixture school for tests: a 3×3 grid of walkways, written in the same file formats the
pipeline exports. Tests change individual edges (risk, crossings, steps) to set up each situation.

Node ids and positions (about 87 m east-west and 111 m north-south between neighbors):

    7 - 8 - 9      north   (node 9, the school entrance, is the top-right corner)
    |   |   |
    4 - 5 - 6
    |   |   |
    1 - 2 - 3      south
"""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Any

BASE_LON, BASE_LAT = -77.2700, 38.8400
STEP_DEG = 0.001
ENTRANCE_NODE = 9
RADIUS_M = 500
SCHOOL_ID = "mini"


def node_lonlat(node: int) -> tuple[float, float]:
    row, col = divmod(node - 1, 3)
    return round(BASE_LON + col * STEP_DEG, 6), round(BASE_LAT + row * STEP_DEG, 6)


def grid_edges() -> list[tuple[int, int]]:
    """The 12 undirected edges, each as (u, v) with u < v."""
    edges = []
    for node in range(1, 10):
        if node % 3 != 0:
            edges.append((node, node + 1))   # east
        if node <= 6:
            edges.append((node, node + 3))   # north
    return edges


def _length_m(u: int, v: int) -> float:
    (lon1, lat1), (lon2, lat2) = node_lonlat(u), node_lonlat(v)
    dx = (lon2 - lon1) * math.cos(math.radians(lat1)) * 111320
    dy = (lat2 - lat1) * 110540
    return round(math.hypot(dx, dy), 1)


def _bbox() -> list[float]:
    lon, lat = node_lonlat(ENTRANCE_NODE)
    dlat = RADIUS_M / 110540
    dlon = RADIUS_M / (111320 * math.cos(math.radians(lat)))
    return [round(lon - dlon, 6), round(lat - dlat, 6), round(lon + dlon, 6), round(lat + dlat, 6)]


def build_files(
    edge_overrides: dict[tuple[int, int], dict[str, Any]] | None = None,
    node_overrides: dict[int, dict[str, Any]] | None = None,
    segment_overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The contents of every exported file, as Python objects, for the mini school."""
    edge_overrides = edge_overrides or {}
    node_overrides = node_overrides or {}
    segment_overrides = segment_overrides or {}

    nodes = []
    for node in range(1, 10):
        lon, lat = node_lonlat(node)
        nodes.append({"id": node, "lon": lon, "lat": lat, "node_risk": 0.0, "major_seg": None,
                      **node_overrides.get(node, {})})

    edges, segments, risky_features = [], {}, []
    for u, v in grid_edges():
        seg_id = f"s{u}-{v}"
        edge = {
            "u": u, "v": v, "length": _length_m(u, v),
            "coords": [list(node_lonlat(u)), list(node_lonlat(v))],
            "seg_id": seg_id, "road_name": f"Road {u}-{v}", "risk_pct": 10.0, "risk_class": "low",
            "is_crossing": False, "is_steps": False,
            **edge_overrides.get((u, v), {}),
        }
        edges.append(edge)
        if edge["seg_id"] is None:
            continue
        mid = [round((node_lonlat(u)[0] + node_lonlat(v)[0]) / 2, 6), round((node_lonlat(u)[1] + node_lonlat(v)[1]) / 2, 6)]
        segments[edge["seg_id"]] = {
            "name": edge["road_name"], "highway": "residential", "speed_mph": 25, "speed_imputed": 0, "lanes": 2,
            "sidewalk_cov": 0.9, "sidewalk_known": 1, "signal_end": 0,
            "risk_pct": edge["risk_pct"], "risk_class": edge["risk_class"], "crashes_recent": 0,
            "crashes_recent_ka": 0, "crashes_prelim": 0, "reasons": [], "mid": mid,
            **segment_overrides.get(edge["seg_id"], {}),
        }
        if edge["risk_class"] in ("medium", "high"):
            risky_features.append({
                "type": "Feature", "geometry": {"type": "LineString", "coordinates": edge["coords"]},
                "properties": {"seg_id": edge["seg_id"], "seg_ids": [edge["seg_id"]], "name": edge["road_name"],
                               "risk_class": edge["risk_class"], "risk_pct": edge["risk_pct"], "crashes_recent": 0},
            })

    lon, lat = node_lonlat(ENTRANCE_NODE)
    return {
        "schools": [{"id": SCHOOL_ID, "name": "Mini School", "level": "MS", "lat": lat, "lon": lon,
                     "radius_m": RADIUS_M, "bbox": _bbox()}],
        "meta": {"data_through": "July 2026", "data_through_date": "2026-07-31",
                 "windows": {"serve_hist": [2022, 2025]}, "model_version": "test",
                 "metrics": {"full_top10_capture": 0.64, "full_lift": 6.4}, "generated_at": "2026-10-12T00:00:00Z"},
        "graph": {"school_id": SCHOOL_ID, "entrance_node": ENTRANCE_NODE, "nodes": nodes, "edges": edges},
        "segments": segments,
        "risk_layer": {"type": "FeatureCollection", "features": risky_features},
        "crash_layer": {"type": "FeatureCollection", "features": [{
            "type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {"year": 2024, "month": 5, "severity": "B", "mode": "ped", "prelim": False}}]},
        "report": {"school_id": SCHOOL_ID,
                   "stats": {"window": "2022–2025", "crashes": 1, "serious_or_fatal": 0, "ped": 1, "bike": 0},
                   "top_spots": []},
    }


def write_mini_data(root: Path, **overrides: Any) -> Path:
    """Write the mini school's files into `root` (layout: schools.json, graphs/, segments/, layers/, reports/)."""
    files = build_files(**overrides)
    for folder in ("graphs", "segments", "layers", "reports"):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / "schools.json").write_text(json.dumps(files["schools"]))
    (root / "meta.json").write_text(json.dumps(files["meta"]))
    with gzip.open(root / "graphs" / f"{SCHOOL_ID}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(files["graph"], f)
    (root / "segments" / f"{SCHOOL_ID}.json").write_text(json.dumps(files["segments"]))
    (root / "layers" / f"{SCHOOL_ID}_risk.geojson").write_text(json.dumps(files["risk_layer"]))
    (root / "layers" / f"{SCHOOL_ID}_crashes.geojson").write_text(json.dumps(files["crash_layer"]))
    (root / "reports" / f"{SCHOOL_ID}.json").write_text(json.dumps(files["report"]))
    (root / "reports" / f"{SCHOOL_ID}_map.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return root
