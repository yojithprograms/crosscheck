import logging

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.geo import flat_distance_m, haversine_m, nearest_index
from app.graph_io import build_graph, edge_polyline, load_graph
from app.main import create_app
from app.store import DataStore
from tests.mini_data import ENTRANCE_NODE, SCHOOL_ID, build_files, grid_edges, node_lonlat, write_mini_data


# ---- graph loading

def test_every_edge_is_stored_in_both_directions() -> None:
    sg = build_graph(build_files()["graph"])
    assert sg.graph.number_of_nodes() == 9
    assert sg.graph.number_of_edges() == 2 * len(grid_edges()) == 24
    assert sg.undirected_edge_count == 12
    assert sg.entrance_node == ENTRANCE_NODE
    for u, v in grid_edges():
        assert sg.graph[u][v]["reversed"] is False and sg.graph[v][u]["reversed"] is True
        assert sg.graph[u][v]["coords"] is sg.graph[v][u]["coords"]      # one shared list, not a copy
        assert sg.graph[u][v]["length"] == sg.graph[v][u]["length"]
        assert sg.graph[u][v]["report_count"] == 0


def test_edge_polyline_follows_the_direction_of_travel() -> None:
    sg = build_graph(build_files()["graph"])
    forward = edge_polyline(sg.graph, 1, 2)
    backward = edge_polyline(sg.graph, 2, 1)
    assert forward[0] == list(node_lonlat(1)) and forward[-1] == list(node_lonlat(2))
    assert backward == forward[::-1]
    assert sg.graph[1][2]["coords"][0] == list(node_lonlat(1))           # the stored list was not reversed in place


def test_node_arrays_line_up_with_the_graph() -> None:
    sg = build_graph(build_files()["graph"])
    assert list(sg.node_ids) == list(range(1, 10))
    position, distance = nearest_index(sg.node_lons, sg.node_lats, *node_lonlat(5))
    assert sg.node_ids[position] == 5 and distance == pytest.approx(0, abs=0.01)


def test_load_graph_reads_the_gzip_file(mini_data_dir) -> None:
    sg = load_graph(mini_data_dir / "graphs" / f"{SCHOOL_ID}.json.gz")
    assert sg.school_id == SCHOOL_ID and sg.graph.number_of_edges() == 24


# ---- geometry helpers

def test_flat_and_haversine_distances_agree_over_short_distances() -> None:
    a, b = node_lonlat(1), node_lonlat(9)
    flat = flat_distance_m(*a, *b)
    assert flat == pytest.approx(haversine_m(*a, *b), rel=0.005)
    assert flat == pytest.approx(((2 * 0.001 * 86500) ** 2 + (2 * 0.001 * 110540) ** 2) ** 0.5, rel=0.01)


# ---- the store

def test_store_loads_everything_and_logs_each_school(mini_data_dir, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="crosscheck.store"):
        store = DataStore.load(mini_data_dir)
    assert list(store.schools) == [SCHOOL_ID]
    school = store.schools[SCHOOL_ID]
    assert school.info["name"] == "Mini School"
    assert len(school.segments) == 12 and school.report["school_id"] == SCHOOL_ID
    assert school.risk_layer["type"] == "FeatureCollection" and school.crash_layer["features"]
    assert store.meta["data_through"] == "July 2026"
    assert "loaded mini: 9 nodes, 12 edges, 12 segments" in caplog.text


def test_store_without_data_raises_a_helpful_error(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Run the pipeline"):
        DataStore.load(tmp_path)


# ---- the app

def test_health_and_meta(client) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    meta = client.get("/meta").json()
    assert meta["data_through"] == "July 2026" and meta["metrics"]["full_top10_capture"] == 0.64


def test_app_starts_without_data_and_says_so(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "nothing-here")
    with TestClient(create_app(settings)) as test_client:
        assert test_client.get("/health").json() == {"status": "ok"}     # still alive (and waking the host)
        response = test_client.get("/meta")
        assert response.status_code == 503
        assert response.json()["detail"]["code"] == "DATA_NOT_READY"


def test_startup_logs_the_loaded_schools(tmp_path, caplog) -> None:
    settings = Settings(data_dir=write_mini_data(tmp_path / "data"))
    with caplog.at_level(logging.INFO):
        with TestClient(create_app(settings)):
            pass
    assert "data store ready: 1 schools" in caplog.text
