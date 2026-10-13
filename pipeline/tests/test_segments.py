import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pytest
import shapely
from shapely.geometry import LineString, Point, box

from crosscheck_pipeline import config
from crosscheck_pipeline.s05_segments import (
    add_features,
    as_list,
    clean_highway,
    clean_name,
    count_near,
    edges_table,
    impute_by_class,
    inside_any,
    largest_int,
    nodes_near_signals,
    parse_oneway,
    sidewalk_coverage,
)
from crosscheck_pipeline.utils.reasons import display_road_name


# ---- tag cleaning

def test_as_list_handles_all_shapes() -> None:
    assert as_list(None) == [] and as_list(float("nan")) == []
    assert as_list("a") == ["a"] and as_list(["a", "b"]) == ["a", "b"]


@pytest.mark.parametrize("raw, expected", [
    ("residential", "residential"), (["primary", "secondary"], "primary"),
    ("motorway_link", "motorway"), ("trunk_link", "trunk"), (None, ""),
])
def test_clean_highway(raw, expected) -> None:
    assert clean_highway(raw) == expected


def test_clean_name_joins_lists_and_handles_missing() -> None:
    assert clean_name(["Pickett Rd", "Route 123"]) == "Pickett Rd / Route 123"
    assert clean_name(["Main St", "Main St"]) == "Main St"
    assert clean_name(None) == "" and clean_name(float("nan")) == ""


@pytest.mark.parametrize("raw, expected", [
    ("35 mph", 35), ("2;3", 3), (["25 mph", "30 mph"], 30), ("25 mph;30 mph", 30), ("4", 4),
])
def test_largest_int(raw, expected) -> None:
    assert largest_int(raw) == expected


@pytest.mark.parametrize("raw", [None, "none", "signals", "", float("nan"), "0"])
def test_largest_int_returns_nan_when_there_is_no_number(raw) -> None:
    assert np.isnan(largest_int(raw))


@pytest.mark.parametrize("raw, expected", [
    (True, 1), (False, 0), ("yes", 1), ("no", 0), ("-1", 1), (None, 0), ([False, True], 1),
])
def test_parse_oneway(raw, expected) -> None:
    assert parse_oneway(raw) == expected


def test_impute_uses_class_median_then_fallback_then_default() -> None:
    known = pd.Series([25.0, 35.0, np.nan, np.nan, np.nan, np.nan])
    highway = pd.Series(["residential", "residential", "residential", "primary", "service", "busway"])
    filled, flag = impute_by_class(known, highway, {"primary": 40, "service": 15}, default=22)
    assert filled.tolist() == [25, 35, 30, 40, 15, 22]  # median of 25 and 35 = 30
    assert flag.tolist() == [0, 0, 1, 1, 1, 1]


def test_display_road_name() -> None:
    assert display_road_name("Pickett Rd", "residential") == "Pickett Rd"
    assert display_road_name("", "service") == "a driveway or parking lot aisle"
    assert display_road_name(None, "residential") == "an unnamed street"
    assert display_road_name("  ", "tertiary") == "an unnamed street"


# ---- spatial features (meters)

ROAD = shapely.linestrings([[(0, 0), (100, 0)]])  # a 100 m east-west road


def line(x0, y0, x1, y1):
    return LineString([(x0, y0), (x1, y1)])


def test_sidewalk_coverage_both_sides_one_side_none() -> None:
    both = np.array([line(0, 7, 100, 7), line(0, -7, 100, -7)])
    one = np.array([line(0, 7, 100, 7)])
    far = np.array([line(0, 40, 100, 40)])  # outside the 15 m buffer
    lengths = np.array([100.0])
    assert sidewalk_coverage(ROAD, lengths, both)[0] == pytest.approx(1.0)
    assert sidewalk_coverage(ROAD, lengths, one)[0] == pytest.approx(0.5)
    assert sidewalk_coverage(ROAD, lengths, far)[0] == 0.0
    assert sidewalk_coverage(ROAD, lengths, np.array([]))[0] == 0.0


def test_sidewalk_coverage_is_capped_at_one_and_flat_capped() -> None:
    triple = np.array([line(0, 7, 100, 7), line(0, -7, 100, -7), line(0, 5, 100, 5)])
    assert sidewalk_coverage(ROAD, np.array([100.0]), triple)[0] == 1.0
    # A sidewalk running past the end of the road only counts where it overlaps the flat-cap buffer.
    long_side = np.array([line(-500, 7, 600, 7)])
    assert sidewalk_coverage(ROAD, np.array([100.0]), long_side)[0] == pytest.approx(0.5)


def test_sidewalk_coverage_chunks_give_the_same_answer() -> None:
    segs = shapely.linestrings([[(0, 0), (100, 0)], [(0, 200), (100, 200)], [(0, 400), (100, 400)]])
    sidewalks = np.array([line(0, 7, 100, 7), line(0, 207, 100, 207)])
    lengths = np.array([100.0, 100.0, 100.0])
    whole = sidewalk_coverage(segs, lengths, sidewalks, chunk=10)
    pieces = sidewalk_coverage(segs, lengths, sidewalks, chunk=1)
    assert whole.tolist() == pytest.approx(pieces.tolist()) == [0.5, 0.5, 0.0]


def test_count_near_points_and_lines() -> None:
    points = np.array([Point(50, 10), Point(50, 14), Point(50, 20), Point(300, 0)])
    assert count_near(ROAD, points, 15)[0] == 2
    connectors = np.array([line(50, 5, 50, 25), line(200, 0, 200, 10)])
    assert count_near(ROAD, connectors, 15)[0] == 1
    assert count_near(ROAD, np.array([]), 15).tolist() == [0]


def test_inside_any_uses_the_midpoint() -> None:
    segs = shapely.linestrings([[(0, 0), (100, 0)], [(0, 500), (100, 500)]])
    polygons = np.array([box(-10, -10, 60, 10)])  # contains the first midpoint (50, 0)
    assert inside_any(segs, polygons).tolist() == [True, False]
    assert inside_any(segs, np.array([])).tolist() == [False, False]


def test_nodes_near_signals() -> None:
    nodes = gpd.GeoDataFrame(geometry=[Point(0, 0), Point(100, 0)], index=[10, 20], crs=config.CRS_METERS)
    signals = np.array([Point(5, 5), Point(300, 300)])
    assert nodes_near_signals(nodes, signals) == {10}
    assert nodes_near_signals(nodes, np.array([])) == set()


# ---- whole table

def tiny_graph() -> nx.MultiDiGraph:
    """Three nodes along a street near Fairfax; both directions stored, as OSMnx does."""
    g = nx.MultiDiGraph(crs="EPSG:4326")
    g.add_node(1, x=-77.2700, y=38.8400)
    g.add_node(2, x=-77.2690, y=38.8400)
    g.add_node(3, x=-77.2680, y=38.8400)
    attrs = dict(length=86.5)
    for a, b, tags in [
        (1, 2, dict(highway="residential", name="Quiet St", maxspeed="25 mph", lanes="2", oneway=False)),
        (2, 3, dict(highway=["primary", "secondary"], name=["Big Rd", "Route 1"], oneway=True)),
    ]:
        g.add_edge(a, b, **attrs, **tags)
        g.add_edge(b, a, **attrs, **tags)
    g.add_edge(3, 3, **attrs, highway="motorway_link", oneway=True)  # dropped: freeway ramp
    return g


def test_edges_table_cleans_tags_and_drops_freeways() -> None:
    segs = edges_table(tiny_graph())
    assert sorted(segs["seg_id"]) == ["1-2-0", "2-3-0"]
    assert segs.crs.to_string() == config.CRS_METERS
    quiet = segs.set_index("seg_id").loc["1-2-0"]
    assert (quiet["name"], quiet["highway"], quiet["speed_mph"], quiet["speed_imputed"]) == ("Quiet St", "residential", 25, 0)
    big = segs.set_index("seg_id").loc["2-3-0"]
    assert big["name"] == "Big Rd / Route 1" and big["highway"] == "primary"
    assert big["speed_mph"] == 40 and big["speed_imputed"] == 1      # primary fallback
    assert big["lanes"] == 4 and big["lanes_imputed"] == 1           # primary fallback
    assert big["oneway"] == 1 and quiet["oneway"] == 0


def test_add_features_end_to_end() -> None:
    segs = edges_table(tiny_graph())
    quiet_geom = segs.set_index("seg_id").loc["1-2-0", "geometry"]
    midpoint = quiet_geom.interpolate(0.5, normalized=True)
    out = add_features(
        segs,
        sidewalks_m=np.array([]),
        crosswalks_m=np.array([]),
        crossing_points_m=np.array([midpoint]),
        bus_stops_m=np.array([Point(midpoint.x, midpoint.y + 50)] * 15),
        signal_nodes={1},
        gap_polygons_m=np.array([]),
    ).set_index("seg_id")
    assert out.loc["1-2-0", "signal_end"] == 1 and out.loc["2-3-0", "signal_end"] == 0
    assert out.loc["1-2-0", "marked_crossings"] == 1
    assert out.loc["1-2-0", "bus_stops_200m"] == config.BUS_STOP_CAP   # 15 stops, capped
    assert out.loc["1-2-0", "class_residential"] == 1 and out.loc["1-2-0", "class_primary"] == 0
    assert out.loc["2-3-0", "class_primary"] == 1
    assert (out["sidewalk_cov"] == 0).all() and (out["sidewalk_known"] == 1).all()
    # No sidewalk + fast road -> flagged; no sidewalk + 25 mph street -> not flagged.
    assert out.loc["2-3-0", "no_sidewalk_fast"] == 1 and out.loc["1-2-0", "no_sidewalk_fast"] == 0
    assert out["log_length"].iloc[0] == pytest.approx(np.log(86.5 + 1))
