import pytest

from app import config, hazards
from app.hazards import NO_SIGNAL_REASON
from app.store import DataStore
from tests.mini_data import SCHOOL_ID, grid_edges, node_lonlat, write_mini_data

PATH = [1, 2, 3, 6, 9]       # the straight-through route used in most tests (1-2, 2-3, 3-6, 6-9)
HIGH = {"risk_pct": 95.0, "risk_class": "high"}


def edge_changes(changes: dict[tuple[int, int], dict]) -> dict[tuple[int, int], dict]:
    """Every edge 50 m long, plus per-edge changes."""
    base = {edge: {"length": 50.0} for edge in grid_edges()}
    for edge, values in changes.items():
        base[edge] = {**base[edge], **values}
    return base


def load_school(tmp_path, changes=None, **overrides):
    overrides["edge_overrides"] = edge_changes(changes or {})
    store = DataStore.load(write_mini_data(tmp_path / "data", **overrides))
    return store.schools[SCHOOL_ID]


def put_reports(school, u, v, count, types):
    for a, b in ((u, v), (v, u)):
        school.graph.graph[a][b]["report_count"] = count
        school.graph.graph[a][b]["report_types"] = dict(types)


def analyze(school, path=PATH, mode="walk"):
    return hazards.analyze_route(school, path, mode)


# ---- the spec's three hazard tests (DESIGN §7.7)

def test_two_adjacent_high_edges_become_one_hazard(tmp_path) -> None:
    school = load_school(tmp_path, {(2, 3): {"risk_pct": 92.0, "risk_class": "high"},
                                    (3, 6): {"risk_pct": 97.0, "risk_class": "high"}})
    result = analyze(school)
    assert len(result.hazards) == 1 and result.high_count == 1
    hazard = result.hazards[0]
    assert hazard.n == 1 and hazard.kind == "along"
    assert hazard.seg_id == "s3-6" and hazard.risk_pct == 97.0           # the riskiest member names the group
    assert hazard.title == "Walking along Road 3-6"
    assert (hazard.lon, hazard.lat) == pytest.approx(node_lonlat(3), abs=1e-6)   # middle of the 100 m group = node 3


def test_titles_for_each_kind_of_hazard(tmp_path) -> None:
    crossing = load_school(tmp_path / "a", {(3, 6): {**HIGH, "is_crossing": True}})
    assert analyze(crossing).hazards[0].title == "Crossing Road 3-6" and analyze(crossing).hazards[0].kind == "crossing"

    along = load_school(tmp_path / "b", {(3, 6): HIGH})
    assert analyze(along, mode="walk").hazards[0].title == "Walking along Road 3-6"
    assert analyze(along, mode="bike").hazards[0].title == "Riding along Road 3-6"

    intersection = load_school(tmp_path / "c", node_overrides={6: {"node_risk": 95.0, "major_seg": "s5-6"}})
    hazard = analyze(intersection).hazards[0]
    assert hazard.kind == "intersection" and hazard.title == "Intersection with Road 5-6"
    assert hazard.seg_id == "s5-6" and hazard.risk_pct == 95.0 and hazard.risk_class == "high"
    assert (hazard.lon, hazard.lat) == pytest.approx(node_lonlat(6), abs=1e-6)   # at the node itself

    reported = load_school(tmp_path / "d")
    put_reports(reported, 3, 6, 1, {"turning_vehicle": 1})
    hazard = analyze(reported).hazards[0]
    assert hazard.kind == "reported" and hazard.title == "Students reported a problem on Road 3-6"


def test_a_report_only_hazard_appears(tmp_path) -> None:
    school = load_school(tmp_path)
    put_reports(school, 2, 3, 2, {"turning_vehicle": 2})
    result = analyze(school)
    assert len(result.hazards) == 1
    hazard = result.hazards[0]
    assert hazard.kind == "reported" and hazard.risk_class == "low"
    assert hazard.report_count == 2 and hazard.report_types == ["turning_vehicle"]
    assert result.high_count == 0 and result.report_spot_count == 1
    assert hazard.reasons[-1] == "2 student reports here in the last 6 months, mostly: turning cars"


def test_a_reported_spot_with_no_linked_road_has_a_generic_title(tmp_path) -> None:
    school = load_school(tmp_path, {(2, 3): {"seg_id": None, "road_name": ""}})
    put_reports(school, 2, 3, 1, {})
    hazard = analyze(school).hazards[0]
    assert hazard.title == "Students reported a problem here" and hazard.seg_id is None
    assert hazard.reasons == ["1 student report here in the last 6 months"]      # no types known: no "mostly"


# ---- grouping

def test_hazards_closer_than_the_group_distance_merge_and_farther_ones_do_not(tmp_path) -> None:
    gap = config.HAZARD_GROUP_M
    merged = load_school(tmp_path / "near", {(1, 2): HIGH, (2, 3): {"length": float(gap)}, (3, 6): HIGH})
    assert len(analyze(merged).hazards) == 1                                    # a 40 m gap is still the same spot
    apart = load_school(tmp_path / "far", {(1, 2): HIGH, (2, 3): {"length": gap + 1.0}, (3, 6): HIGH})
    result = analyze(apart)
    assert [h.n for h in result.hazards] == [1, 2] and result.high_count == 2   # numbered in path order
    assert result.hazards[0].seg_id == "s1-2" and result.hazards[1].seg_id == "s3-6"


def test_a_crossing_and_the_intersection_it_leads_to_are_one_spot(tmp_path) -> None:
    school = load_school(tmp_path, {(3, 6): {"risk_pct": 97.0, "risk_class": "high", "is_crossing": True}},
                         node_overrides={6: {"node_risk": 95.0, "major_seg": "s5-6"}})
    result = analyze(school)
    assert len(result.hazards) == 1
    assert result.hazards[0].kind == "crossing" and result.hazards[0].seg_id == "s3-6"   # riskiest member names it


def test_equally_risky_members_prefer_the_crossing_for_the_title(tmp_path) -> None:
    school = load_school(tmp_path, {(2, 3): {**HIGH}, (3, 6): {**HIGH, "is_crossing": True}})
    assert analyze(school).hazards[0].kind == "crossing"


def test_walking_along_the_risky_road_itself_is_not_an_intersection_hazard(tmp_path) -> None:
    # Node 3 belongs to the risky road s2-3, and the edge into it is that road: no intersection hazard.
    school = load_school(tmp_path, {(2, 3): HIGH}, node_overrides={3: {"node_risk": 95.0, "major_seg": "s2-3"}})
    kinds = [h.kind for h in analyze(school).hazards]
    assert kinds == ["along"]


def test_reports_in_a_group_add_up(tmp_path) -> None:
    school = load_school(tmp_path, {(2, 3): HIGH, (3, 6): HIGH})
    put_reports(school, 2, 3, 1, {"speeding": 1})
    put_reports(school, 3, 6, 2, {"turning_vehicle": 2})
    hazard = analyze(school).hazards[0]
    assert hazard.report_count == 3 and hazard.report_types == ["turning_vehicle", "speeding"]
    assert hazard.reasons[-1] == "3 student reports here in the last 6 months, mostly: turning cars"


# ---- reasons

def test_reasons_put_no_signal_first_for_crossings_on_wide_unsignaled_roads(tmp_path) -> None:
    segments = {"s3-6": {"lanes": 4, "signal_end": 0, "reasons": ["2 crashes involving someone walking or biking here since 2022",
                                                                   "Speed limit is 40 mph"]}}
    school = load_school(tmp_path, {(3, 6): {**HIGH, "is_crossing": True}}, segment_overrides=segments)
    assert analyze(school).hazards[0].reasons == [
        NO_SIGNAL_REASON, "2 crashes involving someone walking or biking here since 2022", "Speed limit is 40 mph"]


def test_no_signal_reason_needs_a_crossing_a_wide_road_and_no_signal(tmp_path) -> None:
    def reasons(sub, kind_changes, segment):
        school = load_school(tmp_path / sub, {(3, 6): {**HIGH, **kind_changes}}, segment_overrides={"s3-6": segment})
        return analyze(school).hazards[0].reasons

    assert reasons("signal", {"is_crossing": True}, {"lanes": 4, "signal_end": 1}) == []      # has a signal
    assert reasons("narrow", {"is_crossing": True}, {"lanes": 2, "signal_end": 0}) == []      # not a wide road
    assert reasons("along", {}, {"lanes": 4, "signal_end": 0}) == []                          # just walking along it


def test_intersection_hazards_use_the_major_roads_reasons(tmp_path) -> None:
    segments = {"s5-6": {"lanes": 5, "signal_end": 0, "reasons": ["Major road with heavy traffic"], "name": "Big Road"}}
    school = load_school(tmp_path, node_overrides={6: {"node_risk": 96.0, "major_seg": "s5-6"}}, segment_overrides=segments)
    hazard = analyze(school).hazards[0]
    assert hazard.title == "Intersection with Big Road" or "Road 5-6" in hazard.title
    assert hazard.reasons == [NO_SIGNAL_REASON, "Major road with heavy traffic"]


def test_unnamed_roads_get_friendly_names_in_titles(tmp_path) -> None:
    school = load_school(tmp_path, {(3, 6): {**HIGH, "road_name": ""}}, segment_overrides={"s3-6": {"highway": "service"}})
    assert analyze(school).hazards[0].title == "Walking along a driveway or parking lot aisle"
    other = load_school(tmp_path / "x", {(3, 6): {**HIGH, "road_name": "", "is_crossing": True}})
    assert analyze(other).hazards[0].title == "Crossing an unnamed street"


# ---- counts and position

def test_counts_for_the_route_cards(tmp_path) -> None:
    school = load_school(tmp_path, {
        (1, 2): {"risk_pct": 75.0, "risk_class": "medium", "seg_id": "shared"},
        (2, 3): {"risk_pct": 80.0, "risk_class": "medium", "seg_id": "shared"},       # same street: counted once
        (3, 6): HIGH,
        (6, 9): {"risk_pct": 72.0, "risk_class": "medium"},
    })
    put_reports(school, 6, 9, 1, {"speeding": 1})
    result = analyze(school)
    assert result.medium_count == 2                                                   # "shared" and s6-9
    assert result.high_count == 1                                                     # s3-6
    assert result.report_spot_count == 1
    # (3,6) is high-risk and the adjacent (6,9) has a report, so they merge into ONE spot that carries both.
    assert len(result.hazards) == 1
    assert result.hazards[0].report_count == 1 and result.hazards[0].risk_class == "high"


def test_a_quiet_route_has_no_hazards(tmp_path) -> None:
    result = analyze(load_school(tmp_path))
    assert result.hazards == [] and (result.high_count, result.medium_count, result.report_spot_count) == (0, 0, 0)


def test_hazard_positions_follow_the_edge_shape(tmp_path) -> None:
    school = load_school(tmp_path, {(1, 2): HIGH})                                    # a single 50 m edge from node 1 to 2
    hazard = analyze(school).hazards[0]
    middle = ((node_lonlat(1)[0] + node_lonlat(2)[0]) / 2, (node_lonlat(1)[1] + node_lonlat(2)[1]) / 2)
    assert (hazard.lon, hazard.lat) == pytest.approx(middle, abs=1e-6)


def test_hazards_can_be_read_in_the_other_direction(tmp_path) -> None:
    school = load_school(tmp_path, {(3, 6): HIGH})
    forward = analyze(school, [1, 2, 3, 6, 9]).hazards[0]
    backward = analyze(school, [9, 6, 3, 2, 1]).hazards[0]
    assert (forward.lon, forward.lat) == pytest.approx((backward.lon, backward.lat), abs=1e-6)


# ---- through the API

def test_routes_include_hazards_and_a_note_that_counts_them(make_client) -> None:
    changes = edge_changes({(1, 2): {"length": 50.0}, (3, 6): {"risk_pct": 99.0, "risk_class": "high"}})
    with make_client(edge_overrides=changes) as client:
        origin = {"lat": node_lonlat(1)[1], "lon": node_lonlat(1)[0]}
        body = client.post("/routes", json={"school_id": SCHOOL_ID, "origin": origin, "mode": "walk"}).json()
    fastest, lower = body["fastest"], body["lower_risk"]
    assert fastest["high_count"] == 1 and len(fastest["hazards"]) == 1 and fastest["hazards"][0]["n"] == 1
    assert fastest["hazards"][0]["title"] == "Walking along Road 3-6"
    assert lower["high_count"] == 0 and lower["hazards"] == []
    assert body["notes"][0].endswith("and avoids 1 high-risk spot.")
    assert set(fastest["hazards"][0]) == {"n", "kind", "title", "lon", "lat", "risk_pct", "risk_class", "reasons",
                                           "report_count", "report_types", "seg_id"}
