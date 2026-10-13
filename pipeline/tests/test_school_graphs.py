import gzip
import json

import geopandas as gpd
import networkx as nx
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from crosscheck_pipeline import config
from crosscheck_pipeline.s10_school_graphs import (
    clip_to_walking_distance,
    entrance_node,
    flag_edges,
    graph_payload,
    link_edges_to_roads,
    node_risk_table,
    orient_coords,
    reachable_share,
    walk_edges,
    write_payload,
)

# Four nodes near Fairfax on an east-west street (node 1 -> 4), 0.001 degrees (about 87 m) apart.
LAT = 38.8400
LONS = {1: -77.2700, 2: -77.2690, 3: -77.2680, 4: -77.2670}


def walk_graph() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph(crs="EPSG:4326")
    for node, lon in LONS.items():
        g.add_node(node, x=lon, y=LAT)

    def both(a, b, **tags):
        osmid = 1000 * a + b                      # real OSMnx edges always carry an osmid
        g.add_edge(a, b, osmid=osmid, length=tags.pop("length", 87.0), **tags)
        g.add_edge(b, a, osmid=osmid, length=g[a][b][0]["length"], **tags)

    both(1, 2, highway="footway", footway="sidewalk")
    both(2, 3, highway="footway", footway="crossing")
    both(3, 4, highway="steps")
    return g


# ---- edge table

def test_walk_edges_keeps_the_shortest_of_parallel_edges_and_drops_loops() -> None:
    g = walk_graph()
    g.add_edge(1, 2, osmid=77, length=200.0, highway="path")   # longer parallel edge between the same nodes
    g.add_edge(2, 1, osmid=77, length=200.0, highway="path")
    g.add_edge(3, 3, osmid=88, length=40.0, highway="path")    # self-loop
    nodes, edges = walk_edges(g)
    assert len(nodes) == 4
    assert sorted(zip(edges["a"], edges["b"])) == [(1, 2), (2, 3), (3, 4)]
    assert edges.loc[(edges["a"] == 1), "length"].iloc[0] == 87.0
    assert (edges["a"] < edges["b"]).all()


def edges_with(**columns) -> gpd.GeoDataFrame:
    n = len(next(iter(columns.values())))
    return gpd.GeoDataFrame(columns, geometry=[LineString([(0, 0), (1, 1)])] * n, crs="EPSG:4326")


def test_crossing_and_steps_flags_handle_lists() -> None:
    edges = edges_with(
        highway=["footway", "footway", ["footway", "steps"], "residential", "path", "footway"],
        footway=["crossing", "sidewalk", None, None, None, None],
        crossing=[None, None, None, "marked", "marked", None],
        cycleway=[None, None, None, None, None, ["lane", "crossing"]],
    )
    flagged = flag_edges(edges)
    assert flagged["is_crossing"].tolist() == [True, False, False, False, True, True]
    assert flagged["is_steps"].tolist() == [False, False, True, False, False, False]


def test_flags_work_when_the_tag_columns_are_missing() -> None:
    flagged = flag_edges(edges_with(highway=["footway", "steps"]))
    assert flagged["is_crossing"].tolist() == [False, False]
    assert flagged["is_steps"].tolist() == [False, True]


def test_orient_coords_runs_from_u_to_v() -> None:
    line = LineString([(0.002, 0.0), (0.001, 0.0), (0.0, 0.0)])
    u_point, v_point = Point(0.0, 0.0), Point(0.002, 0.0)
    coords = orient_coords(line, u_point, v_point)
    assert coords[0] == [0.0, 0.0] and coords[-1] == [0.002, 0.0]
    assert orient_coords(LineString([(0, 0), (0.002, 0)]), u_point, v_point)[0] == [0.0, 0.0]


# ---- risk from the road network

def roads_gdf() -> gpd.GeoDataFrame:
    """One high-risk road running along the walk graph's street, in meters."""
    street = gpd.GeoSeries([LineString([(LONS[1], LAT), (LONS[4], LAT)])], crs="EPSG:4326").to_crs(config.CRS_METERS)
    return gpd.GeoDataFrame(
        {"seg_id": ["1-4-0"], "risk_pct": [96.0], "risk_class": ["high"], "name": ["Main St"],
         "u": [1], "v": [4]},
        geometry=street.geometry, crs=config.CRS_METERS,
    )


def test_edges_next_to_a_road_borrow_its_risk_and_far_edges_do_not() -> None:
    _, edges = walk_edges(walk_graph())
    far = edges.iloc[[0]].copy()
    far["geometry"] = [LineString([(-77.27, 38.86), (-77.269, 38.86)])]  # ~2 km north of the road
    far["a"], far["b"] = 90, 91
    linked = link_edges_to_roads(pd.concat([edges, far], ignore_index=True), roads_gdf())
    near_rows = linked[linked["a"] < 90]
    assert (near_rows["seg_id"] == "1-4-0").all()
    assert (near_rows["risk_class"] == "high").all() and (near_rows["risk_pct"] == 96.0).all()
    assert (near_rows["road_name"] == "Main St").all()
    far_row = linked[linked["a"] == 90].iloc[0]
    assert far_row["seg_id"] is None and far_row["risk_pct"] == 0.0 and far_row["risk_class"] == "low"
    assert far_row["road_name"] == ""


def test_node_risk_is_the_riskiest_road_touching_the_node() -> None:
    roads = pd.DataFrame({
        "seg_id": ["a", "b", "c"], "u": [1, 1, 2], "v": [2, 3, 3], "risk_pct": [40.0, 95.0, 70.0],
    })
    table = node_risk_table(roads)
    assert table.loc[1, "node_risk"] == 95.0 and table.loc[1, "major_seg"] == "b"
    assert table.loc[2, "node_risk"] == 70.0 and table.loc[2, "major_seg"] == "c"
    assert table.loc[3, "node_risk"] == 95.0 and table.loc[3, "major_seg"] == "b"


# ---- payload

def test_graph_payload_matches_the_documented_structure() -> None:
    nodes, edges = walk_edges(walk_graph())
    edges = link_edges_to_roads(flag_edges(edges), roads_gdf())
    risk = node_risk_table(roads_gdf().assign())
    payload = graph_payload("frost-ms", nodes, edges, risk, entrance=1)
    assert payload["school_id"] == "frost-ms" and payload["entrance_node"] == 1
    assert {n["id"] for n in payload["nodes"]} == {1, 2, 3, 4}
    node = {n["id"]: n for n in payload["nodes"]}
    assert node[1]["node_risk"] == 96.0 and node[1]["major_seg"] == "1-4-0"
    assert node[2]["node_risk"] == 0.0 and node[2]["major_seg"] is None   # not a road intersection
    assert len(payload["edges"]) == 3
    for edge in payload["edges"]:
        assert edge["u"] < edge["v"]
        first, last = edge["coords"][0], edge["coords"][-1]
        assert first == [LONS[edge["u"]], LAT] and last == [LONS[edge["v"]], LAT]   # oriented u -> v
        assert set(edge) == {"u", "v", "length", "coords", "seg_id", "road_name", "risk_pct",
                             "risk_class", "is_crossing", "is_steps"}
    by_pair = {(e["u"], e["v"]): e for e in payload["edges"]}
    assert by_pair[(2, 3)]["is_crossing"] is True and by_pair[(3, 4)]["is_steps"] is True


def test_payload_survives_a_gzip_json_round_trip(tmp_path) -> None:
    nodes, edges = walk_edges(walk_graph())
    edges = link_edges_to_roads(flag_edges(edges), roads_gdf())
    payload = graph_payload("frost-ms", nodes, edges, node_risk_table(roads_gdf()), entrance=1)
    path = write_payload(payload, tmp_path)
    assert path.name == "frost-ms.json.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        assert json.load(f) == payload


def test_reachable_share() -> None:
    payload = {"entrance_node": 1, "nodes": [{"id": i} for i in (1, 2, 3, 4)],
               "edges": [{"u": 1, "v": 2}, {"u": 2, "v": 3}]}
    assert reachable_share(payload) == pytest.approx(0.75)   # node 4 is cut off
    payload["edges"].append({"u": 3, "v": 4})
    assert reachable_share(payload) == 1.0


def test_clip_keeps_only_what_is_reachable_within_the_radius() -> None:
    nodes, edges = walk_edges(walk_graph())        # a chain 1-2-3-4, each edge 87 m
    near_nodes, near_edges = clip_to_walking_distance(nodes, edges, entrance=1, radius_m=100)
    assert sorted(near_nodes.index) == [1, 2]       # node 3 is 174 m away
    assert sorted(zip(near_edges["a"], near_edges["b"])) == [(1, 2)]
    all_nodes, all_edges = clip_to_walking_distance(nodes, edges, entrance=1, radius_m=500)
    assert len(all_nodes) == 4 and len(all_edges) == 3


def test_clip_drops_pieces_not_connected_to_the_entrance() -> None:
    g = walk_graph()
    g.add_node(9, x=-77.30, y=38.86)
    g.add_node(10, x=-77.299, y=38.86)
    g.add_edge(9, 10, osmid=9010, length=87.0, highway="footway")
    g.add_edge(10, 9, osmid=9010, length=87.0, highway="footway")
    nodes, edges = walk_edges(g)
    kept_nodes, _ = clip_to_walking_distance(nodes, edges, entrance=1, radius_m=10_000)
    assert sorted(kept_nodes.index) == [1, 2, 3, 4]  # the separate 9-10 island is gone


def entrance_graph():
    """Node 1 is a dead-end spur right at the entrance point; node 2 (60 m away) joins a bigger network."""
    g = nx.MultiDiGraph(crs="EPSG:4326")
    positions = {1: (-77.2700, 38.8400), 2: (-77.2706, 38.8400), 3: (-77.2712, 38.8400),
                 4: (-77.2712, 38.8410), 5: (-77.2718, 38.8410), 6: (-77.2718, 38.8420)}
    for node, (lon, lat) in positions.items():
        g.add_node(node, x=lon, y=lat)
    for a, b in [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]:
        g.add_edge(a, b, osmid=1000 * a + b, length=60.0, highway="footway")
        g.add_edge(b, a, osmid=1000 * a + b, length=60.0, highway="footway")
    return g


def test_entrance_prefers_the_better_connected_node_over_a_dead_end() -> None:
    nodes, edges = walk_edges(entrance_graph())
    # radius 130 m: from node 1 you reach nodes 1-3; from node 2 you reach nodes 1-4.
    chosen = entrance_node(nodes, edges, -77.27001, 38.84, radius_m=130)
    assert chosen == 2


def test_entrance_keeps_the_nearest_node_when_it_is_well_connected() -> None:
    nodes, edges = walk_edges(entrance_graph())
    # A point right beside node 3, which reaches as much as any other candidate: no reason to move away from it.
    assert entrance_node(nodes, edges, -77.27121, 38.84, radius_m=130) == 3


def test_entrance_uses_the_nearest_node_when_no_other_is_close() -> None:
    nodes, edges = walk_edges(entrance_graph())
    assert entrance_node(nodes, edges, -77.30, 38.86, radius_m=130) in set(nodes.index)   # far away: nearest overall
