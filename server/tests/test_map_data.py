from tests.mini_data import SCHOOL_ID


def test_schools_lists_the_pilot_schools(client) -> None:
    schools = client.get("/schools").json()
    assert [s["id"] for s in schools] == [SCHOOL_ID]
    assert set(schools[0]) == {"id", "name", "level", "lat", "lon", "radius_m", "bbox"}
    assert schools[0]["level"] == "MS" and len(schools[0]["bbox"]) == 4


def test_risk_layer_is_geojson_with_the_documented_properties(make_client) -> None:
    edges = {(4, 5): {"risk_pct": 95.0, "risk_class": "high"}, (5, 6): {"risk_pct": 75.0, "risk_class": "medium"}}
    with make_client(edge_overrides=edges) as client:
        response = client.get(f"/schools/{SCHOOL_ID}/risk-layer")
    layer = response.json()
    assert layer["type"] == "FeatureCollection" and len(layer["features"]) == 2
    props = layer["features"][0]["properties"]
    assert set(props) == {"seg_id", "seg_ids", "name", "risk_class", "risk_pct", "crashes_recent"}
    assert layer["features"][0]["geometry"]["type"] == "LineString"
    assert response.headers["cache-control"] == "public, max-age=3600"


def test_crash_layer_has_only_the_public_properties(client) -> None:
    layer = client.get(f"/schools/{SCHOOL_ID}/crashes").json()
    assert layer["type"] == "FeatureCollection"
    assert set(layer["features"][0]["properties"]) == {"year", "month", "severity", "mode", "prelim"}


def test_segment_detail_has_the_documented_fields(make_client) -> None:
    segments = {"s4-5": {"reasons": ["2 crashes involving someone walking or biking here since 2022"],
                         "crashes_recent": 2, "crashes_recent_ka": 1, "speed_imputed": 1, "risk_pct": 96.0,
                         "risk_class": "high"}}
    edges = {(4, 5): {"risk_pct": 96.0, "risk_class": "high"}}
    with make_client(edge_overrides=edges, segment_overrides=segments) as client:
        body = client.get(f"/segments/{SCHOOL_ID}/s4-5").json()
    assert set(body) == {"seg_id", "name", "risk_pct", "risk_class", "reasons", "speed_mph", "speed_imputed", "lanes",
                         "sidewalk_cov", "sidewalk_known", "crashes_recent", "crashes_recent_ka",
                         "crashes_prelim", "reports_recent"}
    assert body["seg_id"] == "s4-5" and body["name"] == "Road 4-5"
    assert body["risk_class"] == "high" and body["risk_pct"] == 96.0
    assert body["crashes_recent"] == 2 and body["crashes_recent_ka"] == 1
    assert body["speed_imputed"] is True and body["sidewalk_known"] is True
    assert body["reports_recent"] == 0


def test_unnamed_streets_get_a_friendly_name(make_client) -> None:
    segments = {"s1-2": {"name": "", "highway": "service"}, "s2-3": {"name": "", "highway": "residential"}}
    with make_client(segment_overrides=segments) as client:
        assert client.get(f"/segments/{SCHOOL_ID}/s1-2").json()["name"] == "a driveway or parking lot aisle"
        assert client.get(f"/segments/{SCHOOL_ID}/s2-3").json()["name"] == "an unnamed street"


def test_unknown_school_and_segment_use_the_app_error_shape(client) -> None:
    for path in ("/schools/nope/risk-layer", "/schools/nope/crashes", "/segments/nope/s1-2"):
        response = client.get(path)
        assert response.status_code == 404
        assert response.json() == {"detail": {"code": "UNKNOWN_SCHOOL", "message": "This school's map isn't ready yet."}}
    response = client.get(f"/segments/{SCHOOL_ID}/does-not-exist")
    assert response.status_code == 404 and response.json()["detail"]["code"] == "UNKNOWN_SEGMENT"


def test_openapi_docs_list_the_new_endpoints(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/schools", "/schools/{school_id}/risk-layer", "/schools/{school_id}/crashes",
                 "/segments/{school_id}/{seg_id}"):
        assert path in paths
