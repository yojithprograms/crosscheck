import logging

import pytest

from app import config, routing
from app.graph_io import build_graph
from tests.mini_data import SCHOOL_ID, build_files, node_lonlat

# Lengths that make the fastest route 1-2-3-6-9 (200 m): bottom row and right column are 50 m each,
# every other edge is 100 m.
SHORT_EDGES = [(1, 2), (2, 3), (3, 6), (6, 9)]


def lengths():
    from tests.mini_data import grid_edges
    return {edge: {"length": 50.0 if edge in SHORT_EDGES else 100.0} for edge in grid_edges()}


def edges_with(changes: dict[tuple[int, int], dict]) -> dict[tuple[int, int], dict]:
    """Standard lengths plus per-edge changes."""
    base = lengths()
    for edge, values in changes.items():
        base[edge] = {**base[edge], **values}
    return base


def origin_at(node: int, dlat_m: float = 0.0, dlon_m: float = 0.0) -> dict:
    lon, lat = node_lonlat(node)
    return {"lat": lat + dlat_m / 110540, "lon": lon + dlon_m / 86800}


def request(client, node_or_origin=1, mode="walk", school=SCHOOL_ID):
    origin = origin_at(node_or_origin) if isinstance(node_or_origin, int) else node_or_origin
    return client.post("/routes", json={"school_id": school, "origin": origin, "mode": mode})


# ---- the risk curve and edge costs

@pytest.mark.parametrize("risk, expected", [(0, 0.0), (50, 0.0), (70, 0.16), (90, 0.64), (100, 1.0)])
def test_risk_curve_matches_the_design_table(risk, expected) -> None:
    assert routing.risk_curve(risk) == pytest.approx(expected)


def costed_graph(edge_overrides=None, node_overrides=None):
    graph = build_graph(build_files(edge_overrides=edge_overrides, node_overrides=node_overrides)["graph"]).graph
    routing.compute_costs(graph)
    return graph


def test_a_low_risk_edge_costs_only_its_length() -> None:
    graph = costed_graph({(1, 2): {"length": 80.0, "risk_pct": 10.0}})
    assert graph[1][2]["cost_low"] == pytest.approx(80.0) == graph[2][1]["cost_low"]


def test_risky_streets_count_as_longer() -> None:
    graph = costed_graph({(1, 2): {"length": 100.0, "risk_pct": 90.0, "risk_class": "high"}})
    assert graph[1][2]["cost_low"] == pytest.approx(100 * (1 + config.ALPHA * 0.64))      # about 2.9 times as long


def test_crossing_a_risky_road_adds_a_fixed_penalty() -> None:
    graph = costed_graph({(1, 2): {"length": 20.0, "risk_pct": 100.0, "is_crossing": True}})
    assert graph[1][2]["cost_low"] == pytest.approx(20 * (1 + config.ALPHA) + config.BETA_CROSSING_M)


def test_entering_a_risky_intersection_from_another_road_costs_extra_only_in_that_direction() -> None:
    nodes = {2: {"node_risk": 95.0, "major_seg": "s2-3"}}
    graph = costed_graph({(1, 2): {"length": 60.0}}, nodes)
    extra = config.GAMMA_INTERSECTION_M * routing.risk_curve(95.0)
    assert graph[1][2]["cost_low"] == pytest.approx(60.0 + extra)        # arriving at node 2 from road s1-2
    assert graph[2][1]["cost_low"] == pytest.approx(60.0)                # node 1 isn't risky
    # Walking along the risky road itself is not "entering" its intersection.
    along = costed_graph({(2, 3): {"length": 60.0}}, {3: {"node_risk": 95.0, "major_seg": "s2-3"}})
    assert along[2][3]["cost_low"] == pytest.approx(60.0)


def test_a_moderately_risky_intersection_does_not_add_cost() -> None:
    graph = costed_graph({(1, 2): {"length": 60.0}}, {2: {"node_risk": config.MEDIUM_PCT - 1, "major_seg": "other"}})
    assert graph[1][2]["cost_low"] == pytest.approx(60.0)


def test_each_recent_report_adds_a_penalty_up_to_the_cap() -> None:
    graph = costed_graph({(1, 2): {"length": 50.0}})
    routing.add_report(graph, 1, 2)
    assert graph[1][2]["cost_low"] == pytest.approx(50 + config.REPORT_PENALTY_M) == graph[2][1]["cost_low"]
    routing.add_report(graph, 1, 2, delta=10)
    assert graph[1][2]["report_count"] == 11
    assert graph[1][2]["cost_low"] == pytest.approx(50 + config.REPORT_PENALTY_M * config.REPORT_MAX_COUNT)
    routing.add_report(graph, 1, 2, delta=-100)                           # removing reports never goes below zero
    assert graph[1][2]["report_count"] == 0 and graph[1][2]["cost_low"] == pytest.approx(50.0)


# ---- the spec's five routing tests (DESIGN §7.6)

def test_1_lower_risk_route_avoids_a_high_risk_edge_when_a_detour_exists(make_client) -> None:
    risky = {(3, 6): {"risk_pct": 99.0, "risk_class": "high"}}
    with make_client(edge_overrides=edges_with(risky)) as client:
        body = request(client).json()
    assert body["same_route"] is False
    assert body["fastest"]["distance_m"] == 200          # 1-2-3-6-9 straight through the risky edge
    assert body["lower_risk"]["distance_m"] == 300       # 1-2-5-6-9 goes around it
    assert body["lower_risk"]["mean_risk_pct"] < body["fastest"]["mean_risk_pct"]


def test_2_same_route_when_nothing_is_risky(make_client) -> None:
    with make_client(edge_overrides=lengths()) as client:
        body = request(client).json()
    assert body["same_route"] is True
    assert body["lower_risk"] == body["fastest"]
    assert body["notes"] == ["Your fastest route is also the lower-risk route."]


def test_3_bike_mode_skips_steps(make_client) -> None:
    steps = {(3, 6): {"is_steps": True}}
    with make_client(edge_overrides=edges_with(steps)) as client:
        walk = request(client, mode="walk").json()
        bike = request(client, mode="bike").json()
    assert walk["fastest"]["distance_m"] == 200          # walkers take the steps
    assert bike["fastest"]["distance_m"] == 300          # bikes and scooters go around
    assert bike["lower_risk"]["distance_m"] == 300


def test_4_outside_area_and_no_nearby_path(client) -> None:
    far_north = request(client, origin_at(9, dlat_m=700))                 # more than 500 m x 1.1 from the school
    assert far_north.status_code == 422 and far_north.json()["detail"]["code"] == "OUTSIDE_AREA"
    assert "Mini School" in far_north.json()["detail"]["message"]
    nowhere = request(client, origin_at(9, dlon_m=400))                   # inside the area, but 400 m from any path
    assert nowhere.status_code == 422 and nowhere.json()["detail"]["code"] == "NO_NEARBY_PATH"


def test_5_a_report_penalty_changes_the_lower_risk_route_only(make_client) -> None:
    with make_client(edge_overrides=lengths()) as client:
        before = request(client).json()
        assert before["same_route"] is True and before["lower_risk"]["distance_m"] == 200
        graph = client.app.state.store.schools[SCHOOL_ID].graph.graph
        routing.add_report(graph, 3, 6, delta=3)                           # three confirmed reports on a street of the route
        after = request(client).json()
    # The fastest route ignores reports: same path, but it now shows the reported spot as a hazard.
    assert after["fastest"]["polyline"] == before["fastest"]["polyline"]
    assert after["fastest"]["distance_m"] == before["fastest"]["distance_m"] == 200
    assert after["fastest"]["report_spot_count"] == 1 and before["fastest"]["report_spot_count"] == 0
    assert after["same_route"] is False
    assert after["lower_risk"]["distance_m"] == 300
    assert after["lower_risk"]["report_spot_count"] == 0


# ---- more route details

def test_no_route_when_the_start_is_cut_off(make_client) -> None:
    with make_client(drop_edges=[(1, 2), (1, 4)]) as client:
        response = request(client)
    assert response.status_code == 422 and response.json()["detail"]["code"] == "NO_ROUTE"


def test_unknown_school(client) -> None:
    response = request(client, school="nope")
    assert response.status_code == 404 and response.json()["detail"]["code"] == "UNKNOWN_SCHOOL"


def test_polyline_runs_from_start_to_entrance_without_repeated_points(make_client) -> None:
    with make_client(edge_overrides=lengths()) as client:
        line = request(client).json()["fastest"]["polyline"]
    assert line[0] == list(node_lonlat(1)) and line[-1] == list(node_lonlat(9))
    assert len(line) == 5 and len({tuple(p) for p in line}) == 5         # 4 edges -> 5 distinct points
    assert line == [list(node_lonlat(n)) for n in (1, 2, 3, 6, 9)]


def test_duration_rounds_up_and_depends_on_the_mode(make_client) -> None:
    with make_client(edge_overrides=lengths()) as client:
        walk = request(client, mode="walk").json()["fastest"]
        bike = request(client, mode="bike").json()["fastest"]
    assert walk["distance_m"] == 200 and walk["duration_min"] == 3        # 200 / 1.2 / 60 = 2.8 -> 3
    assert bike["duration_min"] == 1                                      # 200 / 4.0 / 60 = 0.83 -> 1


def test_mean_risk_is_weighted_by_length(make_client) -> None:
    changes = {(3, 6): {"risk_pct": 98.0, "risk_class": "high"}}
    with make_client(edge_overrides=edges_with(changes)) as client:
        fastest = request(client).json()["fastest"]
    assert fastest["mean_risk_pct"] == pytest.approx((50 * 10 + 50 * 10 + 50 * 98 + 50 * 10) / 200)   # 32.0


def test_a_start_on_the_entrance_node_is_a_zero_length_route(client) -> None:
    body = request(client, 9).json()
    assert body["fastest"]["distance_m"] == 0 and body["fastest"]["duration_min"] == 0
    assert body["fastest"]["polyline"] == [list(node_lonlat(9))] and body["same_route"] is True


def test_notes_when_the_lower_risk_route_is_a_lot_longer(make_client) -> None:
    # The shortcut is a risky crossing (cost 750 effective meters), so the 400 m detour wins: 2x longer.
    changes = {edge: {"length": 400.0} for edge in [(1, 4), (4, 5), (4, 7), (7, 8), (8, 9), (5, 8)]}
    changes[(2, 5)] = {"length": 150.0}
    changes[(5, 6)] = {"length": 150.0}
    changes[(3, 6)] = {"risk_pct": 100.0, "risk_class": "high", "is_crossing": True, "length": 50.0}
    with make_client(edge_overrides=edges_with(changes)) as client:
        body = request(client).json()
    assert body["same_route"] is False
    assert body["fastest"]["distance_m"] == 200 and body["lower_risk"]["distance_m"] == 400
    assert body["lower_risk"]["distance_m"] > config.LONG_DETOUR_RATIO * body["fastest"]["distance_m"]
    assert routing.LONG_DETOUR_NOTE in body["notes"]


def test_route_notes_wording() -> None:
    from app.schemas import Route

    def route(distance, minutes, high, mean=50.0, reports=0):
        return Route(distance_m=distance, duration_min=minutes, polyline=[], high_count=high, medium_count=0,
                     report_spot_count=reports, mean_risk_pct=mean, hazards=[])

    fast = route(1000, 14, 2, mean=60.0)
    assert routing.route_notes(False, fast, route(1100, 17, 0, mean=40.0)) == [
        "The lower-risk route adds 3 min and avoids 2 high-risk spots."]
    assert routing.route_notes(False, route(1000, 14, 1), route(1100, 17, 0)) == [
        "The lower-risk route adds 3 min and avoids 1 high-risk spot."]
    # No fewer high-risk spots, but a lower average risk: only then say "less of the trip on risky streets".
    assert routing.route_notes(False, route(1000, 14, 1, mean=58.8), route(1003, 14, 2, mean=54.9)) == [
        "The lower-risk route adds less than a minute and spends less of the trip on risky streets."]
    # Detouring to dodge reported spots must not claim a lower average risk.
    assert routing.route_notes(False, route(1000, 14, 0, mean=30.0, reports=2), route(1100, 16, 0, mean=33.0)) == [
        "The lower-risk route adds 2 min and avoids 2 spots students reported."]
    assert routing.route_notes(False, route(1000, 14, 0, mean=30.0, reports=1), route(1100, 16, 0, mean=33.0)) == [
        "The lower-risk route adds 2 min and avoids 1 spot students reported."]
    assert routing.route_notes(False, route(1000, 14, 0, mean=30.0), route(1100, 16, 0, mean=33.0)) == [
        "The lower-risk route adds 2 min and has about the same level of risk."]
    assert routing.route_notes(True, fast, fast) == ["Your fastest route is also the lower-risk route."]


def test_invalid_coordinates_are_rejected(client) -> None:
    response = client.post("/routes", json={"school_id": SCHOOL_ID, "origin": {"lat": 95, "lon": -77.27}})
    assert response.status_code == 422


def test_the_start_point_is_never_logged(make_client, caplog) -> None:
    origin = {"lat": 38.840123, "lon": -77.270456}
    with make_client(edge_overrides=lengths()) as client:
        with caplog.at_level(logging.DEBUG):
            request(client, origin)
    assert "38.840123" not in caplog.text and "77.270456" not in caplog.text
