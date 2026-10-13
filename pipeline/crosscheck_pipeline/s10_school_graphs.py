"""Step 1.10 — Per-school walk graphs for routing.

Run: python -m crosscheck_pipeline.s10_school_graphs
Reads:  data/schools_pilot.csv, data/interim/segments_scored.parquet
Writes: server/data/graphs/{school_id}.json.gz, data/interim/schools_used.json

Each school gets a small walking graph (sidewalks, crosswalks, paths, streets within `radius_m` of
the entrance by walking distance, on the main connected walking network). Every walking edge borrows the risk of the road it runs along or
crosses, and every intersection remembers the riskiest road touching it. Routing costs are NOT
stored here: the server computes them at startup so weights can be tuned without rerunning this.
"""
from __future__ import annotations

import gzip
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import geopandas as gpd
import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import shapely
from shapely.geometry import Point

from crosscheck_pipeline import config
from crosscheck_pipeline.s01_schools import load_pilot
from crosscheck_pipeline.s05_segments import as_list
from crosscheck_pipeline.utils.osm_parse import configure_osmnx

PIPELINE_DIR = Path(__file__).resolve().parents[1]
SCORED_PARQUET = PIPELINE_DIR / "data" / "interim" / "segments_scored.parquet"
USED_JSON = PIPELINE_DIR / "data" / "interim" / "schools_used.json"
GRAPHS_DIR = PIPELINE_DIR.parent / "server" / "data" / "graphs"
ROAD_COLUMNS = ["seg_id", "u", "v", "name", "risk_pct", "risk_class", "geometry"]


# ---------------------------------------------------------------- edge table

def any_tag(value: Any, test: Callable[[str], bool]) -> bool:
    """OSM tags can be lists after simplification; a list matches if any item matches."""
    return any(test(str(item)) for item in as_list(value))


def walk_edges(graph) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Undirected walk graph -> (nodes, edges), both in lon/lat.

    Self-loops are dropped, and only the shortest edge between each pair of nodes is kept, so every
    pair of nodes has one unambiguous edge. `a` and `b` are the lower and higher node ids.
    """
    undirected = ox.convert.to_undirected(graph)
    nodes, edges = ox.convert.graph_to_gdfs(undirected)
    edges = edges.reset_index()
    edges = edges[edges["u"] != edges["v"]].copy()
    edges["a"] = edges[["u", "v"]].min(axis=1)
    edges["b"] = edges[["u", "v"]].max(axis=1)
    edges = edges.sort_values("length").drop_duplicates(["a", "b"]).reset_index(drop=True)
    return nodes, edges


def flag_edges(edges: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add is_crossing (a marked crossing) and is_steps."""
    out = edges.copy()

    def col(name: str) -> pd.Series:
        return out[name] if name in out.columns else pd.Series([None] * len(out), index=out.index)

    crossing_by_tag = (
        col("footway").map(lambda v: any_tag(v, lambda t: t == "crossing"))
        | col("cycleway").map(lambda v: any_tag(v, lambda t: t == "crossing"))
    )
    path_like = col("highway").map(lambda v: any_tag(v, lambda t: t in ("footway", "path", "cycleway", "pedestrian")))
    has_crossing_tag = col("crossing").map(lambda v: len(as_list(v)) > 0)
    out["is_crossing"] = (crossing_by_tag | (path_like & has_crossing_tag)).astype(bool)
    out["is_steps"] = col("highway").map(lambda v: any_tag(v, lambda t: t == "steps")).astype(bool)
    return out


def orient_coords(edge_geometry, u_point: Point, v_point: Point) -> list[list[float]]:
    """The edge's [lon, lat] coordinates, running from node u to node v (reversed if they run the other way)."""
    coords = [list(c) for c in edge_geometry.coords]
    first = Point(coords[0])
    if first.distance(u_point) > first.distance(v_point):
        coords.reverse()
    return [[round(x, config.COORD_DECIMALS), round(y, config.COORD_DECIMALS)] for x, y in coords]


# ---------------------------------------------------------------- risk from the road network

def link_edges_to_roads(edges: gpd.GeoDataFrame, roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Give each walking edge the risk of the nearest road segment within WALK_TO_ROAD_MAX_M.

    Uses the edge's midpoint. No road close enough (a trail, a park path) -> seg_id None, risk 0, "low".
    `edges` is in lon/lat; `roads` (the scored segments) is in meters.
    """
    edges_m = edges.to_crs(config.CRS_METERS)
    mids = gpd.GeoDataFrame(
        {"edge_idx": np.arange(len(edges))},
        geometry=shapely.line_interpolate_point(edges_m.geometry.values, 0.5, normalized=True),
        crs=config.CRS_METERS,
    )
    road_cols = roads[["seg_id", "risk_pct", "risk_class", "name", "geometry"]].rename(columns={"name": "road_name"})
    joined = gpd.sjoin_nearest(mids, road_cols, how="left", max_distance=config.WALK_TO_ROAD_MAX_M)
    joined = joined[~joined["edge_idx"].duplicated(keep="first")].set_index("edge_idx").reindex(np.arange(len(edges)))

    out = edges.copy()
    matched = joined["seg_id"].notna().to_numpy()
    out["seg_id"] = pd.Series(np.where(matched, joined["seg_id"], None), index=out.index, dtype=object)
    out["road_name"] = np.where(matched, joined["road_name"].fillna(""), "")
    out["risk_pct"] = np.where(matched, joined["risk_pct"], 0.0)
    out["risk_class"] = np.where(matched, joined["risk_class"], "low")
    return out


def node_risk_table(roads: pd.DataFrame) -> pd.DataFrame:
    """For every road intersection (OSM node id): the highest risk_pct among the road segments that
    touch it (`node_risk`), and which segment that is (`major_seg`)."""
    ends = pd.concat([
        roads[["u", "seg_id", "risk_pct"]].rename(columns={"u": "node"}),
        roads[["v", "seg_id", "risk_pct"]].rename(columns={"v": "node"}),
    ])
    riskiest = ends.sort_values("risk_pct", ascending=False).drop_duplicates("node").set_index("node")
    return riskiest.rename(columns={"risk_pct": "node_risk", "seg_id": "major_seg"})


# ---------------------------------------------------------------- one school

def reach_count(walk: nx.Graph, node: int, radius_m: float) -> int:
    """How many nodes can be walked to from `node` within `radius_m` meters."""
    return len(nx.single_source_dijkstra_path_length(walk, node, cutoff=radius_m, weight="weight"))


def entrance_node(
    nodes: gpd.GeoDataFrame, edges: gpd.GeoDataFrame, lon: float, lat: float, radius_m: float
) -> int:
    """The walking node students route to.

    Starts from the nodes closest to the entrance point (within ENTRANCE_CANDIDATE_RADIUS_M, at most
    ENTRANCE_MAX_CANDIDATES) and takes the nearest one that is well connected: it must reach at least
    ENTRANCE_MIN_REACH_SHARE of what the best-connected candidate reaches within `radius_m`. That keeps a
    point that falls on a dead-end campus path from stranding the whole graph, without drifting away
    from the entrance toward the middle of the network. If no node is that close, the nearest is used.
    """
    nodes_m = nodes.to_crs(config.CRS_METERS)
    entrance_m = gpd.GeoSeries(gpd.points_from_xy([lon], [lat]), crs="EPSG:4326").to_crs(config.CRS_METERS).iloc[0]
    distance = nodes_m.geometry.distance(entrance_m).sort_values()
    candidates = list(distance[distance <= config.ENTRANCE_CANDIDATE_RADIUS_M].index[: config.ENTRANCE_MAX_CANDIDATES])
    if len(candidates) <= 1:
        return int(distance.index[0])
    walk = nx.Graph()
    walk.add_weighted_edges_from(zip(edges["a"], edges["b"], edges["length"]))
    reach = {node: reach_count(walk, node, radius_m) for node in candidates}
    needed = config.ENTRANCE_MIN_REACH_SHARE * max(reach.values())
    return int(next(node for node in candidates if reach[node] >= needed))   # candidates are nearest-first


def graph_payload(
    school_id: str, nodes: gpd.GeoDataFrame, edges: gpd.GeoDataFrame, node_risk: pd.DataFrame, entrance: int
) -> dict[str, Any]:
    """The JSON structure described in DESIGN §6 Step 1.10: each undirected edge once, with u < v."""
    node_points = {int(i): geom for i, geom in nodes.geometry.items()}
    risk = node_risk.reindex(nodes.index)
    node_rows = []
    for node_id, point, value, major in zip(nodes.index, nodes.geometry, risk["node_risk"], risk["major_seg"]):
        node_rows.append({
            "id": int(node_id),
            "lon": round(point.x, config.COORD_DECIMALS),
            "lat": round(point.y, config.COORD_DECIMALS),
            "node_risk": 0.0 if pd.isna(value) else round(float(value), 1),
            "major_seg": None if pd.isna(major) else str(major),
        })
    edge_rows = []
    for e in edges.itertuples():
        lo, hi = int(e.a), int(e.b)
        edge_rows.append({
            "u": lo, "v": hi,
            "length": round(float(e.length), 1),
            "coords": orient_coords(e.geometry, node_points[lo], node_points[hi]),
            "seg_id": None if e.seg_id is None else str(e.seg_id),
            "road_name": str(e.road_name),
            "risk_pct": round(float(e.risk_pct), 1),
            "risk_class": str(e.risk_class),
            "is_crossing": bool(e.is_crossing),
            "is_steps": bool(e.is_steps),
        })
    return {"school_id": school_id, "entrance_node": int(entrance), "nodes": node_rows, "edges": edge_rows}


def clip_to_walking_distance(
    nodes: gpd.GeoDataFrame, edges: gpd.GeoDataFrame, entrance: int, radius_m: float
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Keep only what can be reached from the entrance within `radius_m` meters of walking.

    This also guarantees that every kept node can walk to the entrance.
    """
    walk = nx.Graph()
    walk.add_weighted_edges_from(zip(edges["a"], edges["b"], edges["length"]))
    reach = set(nx.single_source_dijkstra_path_length(walk, entrance, cutoff=radius_m, weight="weight"))
    keep_edges = edges[edges["a"].isin(reach) & edges["b"].isin(reach)].reset_index(drop=True)
    return nodes[nodes.index.isin(reach)], keep_edges


def download_walk_graph(lat: float, lon: float, radius_m: float):
    """Walk network in a square around the point (with a margin), keeping the largest connected piece.

    A square is used instead of a network-distance circle so that an entrance point that sits in a
    small disconnected pocket (inside school grounds, say) can't leave us with a tiny graph. Retries
    a few times, switching Overpass servers each time, because they sometimes time out.
    """
    last_error: Exception | None = None
    for attempt in range(config.HTTP_RETRIES):
        ox.settings.overpass_url = config.OVERPASS_URLS[attempt % len(config.OVERPASS_URLS)]
        try:
            return ox.graph.graph_from_point(
                (lat, lon), dist=radius_m + config.WALK_GRAPH_BBOX_MARGIN_M, dist_type="bbox",
                network_type="walk", simplify=True,
            )
        except Exception as error:  # network trouble: wait and try again
            last_error = error
            print(f"  download failed ({type(error).__name__}) via {ox.settings.overpass_url}; "
                  f"retry {attempt + 1}/{config.HTTP_RETRIES}")
            time.sleep(config.WALK_DOWNLOAD_RETRY_WAIT_S)
    raise RuntimeError(f"Could not download the walk network: {last_error}")


def build_school_graph(school: pd.Series, roads: gpd.GeoDataFrame, node_risk: pd.DataFrame) -> tuple[dict[str, Any], int]:
    """Build one school's walk graph, shrinking the radius until it has at most MAX_GRAPH_EDGES edges.

    The entrance is the node on the main walking network closest to the school's entrance point.
    Returns (payload, radius_used).
    """
    lat, lon = school["entrance_lat"], school["entrance_lon"]
    radius = int(school["radius_m"])
    while True:
        graph = download_walk_graph(lat, lon, radius)
        all_nodes, all_edges = walk_edges(graph)
        entrance = entrance_node(all_nodes, all_edges, lon, lat, radius)
        nodes, edges = clip_to_walking_distance(all_nodes, all_edges, entrance, radius)
        if len(edges) <= config.MAX_GRAPH_EDGES:
            break
        radius = int(radius * config.WALK_GRAPH_SHRINK)
        print(f"  {len(edges)} edges is too many; retrying with radius {radius} m")
    edges = link_edges_to_roads(flag_edges(edges), roads)
    return graph_payload(school["school_id"], nodes, edges, node_risk, entrance), radius


def reachable_share(payload: dict[str, Any]) -> float:
    """Share of nodes that can walk to the entrance (1.0 = the whole graph is connected to it)."""
    g = nx.Graph()
    g.add_nodes_from(n["id"] for n in payload["nodes"])
    g.add_edges_from((e["u"], e["v"]) for e in payload["edges"])
    return len(nx.node_connected_component(g, payload["entrance_node"])) / g.number_of_nodes()


def write_payload(payload: dict[str, Any], directory: Path = GRAPHS_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{payload['school_id']}.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))
    return path


def main() -> None:
    configure_osmnx()
    pilot = load_pilot()
    # Only the columns this step uses: the full table also carries reasons and contributions (lots of memory).
    roads = gpd.read_parquet(SCORED_PARQUET, columns=ROAD_COLUMNS)
    node_risk = node_risk_table(roads)
    used: dict[str, dict[str, Any]] = {}
    for _, school in pilot.iterrows():
        print(f"{school['school_id']}: downloading the walk network ({school['radius_m']} m)...")
        payload, radius = build_school_graph(school, roads, node_risk)
        path = write_payload(payload)
        size_mb = path.stat().st_size / 1e6
        crossings = sum(e["is_crossing"] for e in payload["edges"])
        linked = sum(e["seg_id"] is not None for e in payload["edges"])
        share = reachable_share(payload)
        used[school["school_id"]] = {
            "radius_m": radius, "entrance_node": payload["entrance_node"],
            "nodes": len(payload["nodes"]), "edges": len(payload["edges"]),
        }
        print(f"  {len(payload['nodes'])} nodes, {len(payload['edges'])} edges ({linked} linked to a road, "
              f"{crossings} crossings); {size_mb:.2f} MB; {share:.0%} of nodes reach the entrance")
        assert size_mb < config.MAX_GRAPH_FILE_MB, f"{path.name} is too big"
        assert share == 1.0, "some nodes can't reach the entrance"
    USED_JSON.write_text(json.dumps(used, indent=2))
    print(f"\nWrote {len(used)} graphs to {GRAPHS_DIR} and {USED_JSON.name}")


if __name__ == "__main__":
    main()
