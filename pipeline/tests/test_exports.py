import gzip
import json
from typing import Any

import geopandas as gpd
import pandas as pd
import pytest
from pyproj import Transformer
from shapely.geometry import LineString

from crosscheck_pipeline import config
from crosscheck_pipeline.run_all import STEPS, steps_to_run
from crosscheck_pipeline.s11_exports import (
    ask_about_lines,
    bbox_for,
    cross_street,
    crash_collection,
    merge_risk_layer,
    meta_record,
    pick_top_spots,
    school_records,
    school_stats,
    segment_records,
    spot_title,
)
from crosscheck_pipeline.validate_exports import validate

TO_M = Transformer.from_crs("EPSG:4326", config.CRS_METERS, always_xy=True)
LON, LAT = -77.2735, 38.8362


def line(east_m: float, north_m: float, length_m: float = 100.0) -> LineString:
    """A segment starting `east_m`/`north_m` meters from the school and running east."""
    x0, y0 = TO_M.transform(LON, LAT)
    x, y = x0 + east_m, y0 + north_m
    return LineString([(x, y), (x + length_m, y)])


def segs(rows: list[dict[str, Any]]) -> gpd.GeoDataFrame:
    base = {"name": "Pickett Road", "highway": "primary", "u": 1, "v": 2, "speed_mph": 40, "speed_imputed": 0,
            "lanes": 4, "sidewalk_cov": 0.1, "sidewalk_known": 1, "signal_end": 0, "risk_pct": 95.0,
            "risk_class": "high", "crashes_recent": 1, "crashes_recent_ka": 0, "crashes_prelim": 0,
            "reasons": ["Major road with heavy traffic"]}
    frame = pd.DataFrame([{**base, **{k: v for k, v in r.items() if k != "geometry"}} for r in rows])
    return gpd.GeoDataFrame(frame, geometry=[r["geometry"] for r in rows], crs=config.CRS_METERS)


# ---- schools and segments

def test_bbox_is_centered_on_the_entrance() -> None:
    min_lon, min_lat, max_lon, max_lat = bbox_for(LON, LAT, 2400)
    assert (min_lat + max_lat) / 2 == pytest.approx(LAT, abs=1e-5)
    assert (max_lat - min_lat) * 110540 / 2 == pytest.approx(2400, rel=0.001)
    assert (min_lon + max_lon) / 2 == pytest.approx(LON, abs=1e-5)


def test_school_records_use_the_radius_actually_used() -> None:
    pilot = pd.DataFrame({"school_id": ["frost-ms"], "name": ["Robert Frost Middle School"], "level": ["MS"],
                          "entrance_lat": [LAT], "entrance_lon": [LON], "radius_m": [2400]})
    record = school_records(pilot, {"frost-ms": {"radius_m": 2000}})[0]
    assert record["id"] == "frost-ms" and record["radius_m"] == 2000
    assert set(record) == {"id", "name", "level", "lat", "lon", "radius_m", "bbox"}
    assert school_records(pilot, {})[0]["radius_m"] == 2400


def test_segment_records_have_the_documented_fields() -> None:
    data = segment_records(segs([{"seg_id": "1-2-0", "geometry": line(0, 0)}]))["1-2-0"]
    assert set(data) == {"name", "highway", "speed_mph", "speed_imputed", "lanes", "sidewalk_cov", "sidewalk_known",
                         "signal_end", "risk_pct", "risk_class", "crashes_recent", "crashes_recent_ka",
                         "crashes_prelim", "reasons", "mid"}
    assert data["mid"][0] == pytest.approx(LON, abs=0.001) and data["mid"][1] == pytest.approx(LAT, abs=0.001)
    json.dumps(data)  # plain Python types only


# ---- risk layer

def test_adjacent_same_name_same_class_segments_merge_into_one_feature() -> None:
    layer = merge_risk_layer(segs([
        {"seg_id": "a", "geometry": line(0, 0), "risk_pct": 91.0, "crashes_recent": 1},
        {"seg_id": "b", "geometry": line(100, 0), "risk_pct": 97.0, "crashes_recent": 2},
    ]))
    assert len(layer) == 1
    row = layer.iloc[0]
    assert row["seg_id"] == "b" and sorted(row["seg_ids"]) == ["a", "b"]
    assert row["risk_pct"] == 97.0 and row["crashes_recent"] == 3
    assert row.geometry.geom_type == "LineString" and layer.crs.to_epsg() == 4326


def test_different_class_or_unnamed_segments_do_not_merge() -> None:
    layer = merge_risk_layer(segs([
        {"seg_id": "a", "geometry": line(0, 0), "risk_class": "high"},
        {"seg_id": "b", "geometry": line(100, 0), "risk_class": "medium", "risk_pct": 75.0},
        {"seg_id": "c", "geometry": line(0, 300), "name": ""},
        {"seg_id": "d", "geometry": line(100, 300), "name": ""},
    ]))
    assert len(layer) == 4


# ---- crash layer

def test_crash_collection_hides_report_numbers_and_exact_dates() -> None:
    crashes = gpd.GeoDataFrame(
        {"doc_nbr": [111, 222, 333], "year": [2021, 2024, 2026], "severity": ["C", "A", "B"],
         "mode": ["ped", "bike", "ped"], "street": ["MAIN ST"] * 3,
         "date": pd.to_datetime(["2021-03-05", "2024-07-19", "2026-02-11"], utc=True)},
        geometry=gpd.points_from_xy([LON] * 3, [LAT] * 3), crs="EPSG:4326",
    ).to_crs(config.CRS_METERS)
    collection = crash_collection(crashes)
    assert [f["properties"]["year"] for f in collection["features"]] == [2024, 2026]   # 2021 is before MAP_CRASHES_FROM
    first = collection["features"][0]["properties"]
    assert first == {"year": 2024, "month": 7, "severity": "A", "mode": "bike", "prelim": False}
    assert collection["features"][1]["properties"]["prelim"] is True
    assert collection["features"][0]["geometry"]["type"] == "Point"


# ---- top spots

def test_cross_street_prefers_the_more_important_other_road() -> None:
    roads = segs([
        {"seg_id": "me", "geometry": line(0, 0), "name": "Pickett Road", "u": 1, "v": 2},
        {"seg_id": "r1", "geometry": line(0, 100), "name": "Quiet Lane", "highway": "residential", "u": 2, "v": 3},
        {"seg_id": "r2", "geometry": line(0, 200), "name": "Main Street", "highway": "secondary", "u": 1, "v": 4},
        {"seg_id": "r3", "geometry": line(0, 300), "name": "", "highway": "trunk", "u": 2, "v": 5},            # unnamed: ignored
        {"seg_id": "r4", "geometry": line(0, 400), "name": "Pickett Road", "highway": "trunk", "u": 2, "v": 6},  # the same road
        {"seg_id": "r5", "geometry": line(0, 500), "name": "Far Street", "highway": "trunk", "u": 8, "v": 9},    # not touching
    ])
    me = roads.iloc[0]
    assert cross_street(me, roads) == "Main Street"
    assert spot_title(me, roads) == "Pickett Road near Main Street"
    assert cross_street(roads.iloc[4], roads.iloc[[4]]) is None
    unnamed = me.copy()
    unnamed["name"], unnamed["highway"] = "", "service"
    assert spot_title(unnamed, roads.iloc[[0]]) == "A driveway or parking lot aisle near Pickett Road"
    assert spot_title(unnamed, roads.iloc[0:0]) == "A driveway or parking lot aisle"   # no cross street found


def test_ask_about_lines_follow_appendix_a() -> None:
    base = pd.Series({"speed_mph": 40, "speed_imputed": 0, "lanes": 4, "sidewalk_cov": 0.1, "sidewalk_known": 1})
    assert len(ask_about_lines(base)) == 3
    estimated = base.copy()
    estimated["speed_imputed"] = 1
    assert len(ask_about_lines(estimated)) == 2        # an estimated speed doesn't trigger the speed question
    quiet = pd.Series({"speed_mph": 25, "speed_imputed": 0, "lanes": 2, "sidewalk_cov": 0.9, "sidewalk_known": 1})
    assert ask_about_lines(quiet) == []
    unknown_walks = base.copy()
    unknown_walks["sidewalk_known"] = 0
    assert len(ask_about_lines(unknown_walks)) == 2


def test_top_spots_are_riskiest_first_and_spread_apart() -> None:
    candidates = segs([
        {"seg_id": "top", "geometry": line(0, 0), "risk_pct": 99.0, "u": 1, "v": 2},
        {"seg_id": "too-close", "geometry": line(0, 40), "risk_pct": 98.0, "u": 3, "v": 4},     # 40 m from the top one
        {"seg_id": "second", "geometry": line(0, 400), "risk_pct": 97.0, "crashes_recent": 5, "u": 5, "v": 6},
        {"seg_id": "tie-fewer", "geometry": line(500, 400), "risk_pct": 90.0, "crashes_recent": 1, "u": 7, "v": 8},
        {"seg_id": "tie-more", "geometry": line(-500, 400), "risk_pct": 90.0, "crashes_recent": 4, "u": 9, "v": 10},
    ])
    spots = pick_top_spots(candidates, candidates, n=3, min_spacing_m=150)
    assert [s["seg_id"] for s in spots] == ["top", "second", "tie-more"]   # too-close skipped; tie broken by crashes
    assert [s["rank"] for s in spots] == [1, 2, 3]
    assert set(spots[0]) == {"rank", "title", "lat", "lon", "seg_id", "risk_pct", "crashes_recent",
                             "crashes_recent_ka", "reasons", "ask_about"}
    json.dumps(spots)


def test_school_stats_counts_only_the_serving_window() -> None:
    crashes = pd.DataFrame({
        "year": [2021, 2022, 2025, 2025, 2026], "ka": [True, True, False, True, True],
        "mode": ["ped", "ped", "bike", "ped", "ped"],
    })
    assert school_stats(crashes) == {"window": "2022–2025", "crashes": 3, "serious_or_fatal": 2, "ped": 2, "bike": 1}


def test_meta_record_names_the_last_month_of_crash_data() -> None:
    crashes = pd.DataFrame({"date": pd.to_datetime(["2026-06-30", "2026-07-31"], utc=True)})
    metrics = {"model_version": "logreg-test", "full_top10_capture": 0.64, "full_lift": 6.4,
               "cv": {"folds": 5, "models": {}}}
    meta = meta_record(crashes, metrics)
    assert meta["data_through"] == "July 2026" and meta["data_through_date"] == "2026-07-31"
    assert meta["metrics"]["full_top10_capture"] == 0.64 and meta["model_version"] == "logreg-test"
    assert {"data_through", "windows", "metrics", "model_version", "generated_at"} <= set(meta)


# ---- validation

def write_valid_export(root) -> None:
    school = {"id": "frost-ms", "name": "Frost", "level": "MS", "lat": LAT, "lon": LON, "radius_m": 2400,
              "bbox": [0, 0, 1, 1]}
    for folder in ("graphs", "segments", "layers", "reports"):
        (root / folder).mkdir(parents=True)
    (root / "schools.json").write_text(json.dumps([school]))
    (root / "meta.json").write_text(json.dumps({"data_through": "July 2026", "windows": {}, "metrics": {},
                                                "model_version": "x", "generated_at": "now"}))
    graph = {"school_id": "frost-ms", "entrance_node": 1, "nodes": [{"id": 1}, {"id": 2}],
             "edges": [{"u": 1, "v": 2, "seg_id": "a"}]}
    with gzip.open(root / "graphs" / "frost-ms.json.gz", "wt") as f:
        json.dump(graph, f)
    (root / "segments" / "frost-ms.json").write_text(json.dumps({"a": {}}))
    (root / "layers" / "frost-ms_risk.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [{"properties": {"seg_ids": ["a"]}}]}))
    (root / "layers" / "frost-ms_crashes.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [{"properties": {"year": 2024}}]}))
    (root / "reports" / "frost-ms.json").write_text(json.dumps(
        {"school_id": "frost-ms", "stats": {}, "top_spots": [{"seg_id": "a"}]}))
    (root / "reports" / "frost-ms_map.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 10)


def test_a_complete_export_validates(tmp_path) -> None:
    write_valid_export(tmp_path)
    assert validate(tmp_path) == []


def test_validation_catches_missing_files_bad_ids_and_leaks(tmp_path) -> None:
    write_valid_export(tmp_path)
    (tmp_path / "reports" / "frost-ms_map.png").unlink()
    (tmp_path / "segments" / "frost-ms.json").write_text(json.dumps({"other": {}}))
    (tmp_path / "layers" / "frost-ms_crashes.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [{"properties": {"doc_nbr": 1}}]}))
    problems = " | ".join(validate(tmp_path))
    assert "missing file: reports/frost-ms_map.png" in problems or "missing reports/frost-ms_map.png" in problems
    assert "missing from segments/frost-ms.json" in problems
    assert "crash layer exposes" in problems
    assert "top spots reference unknown segments" in problems


def test_validation_flags_unparseable_and_oversized_files(tmp_path) -> None:
    write_valid_export(tmp_path)
    (tmp_path / "meta.json").write_text("{not json")
    (tmp_path / "layers" / "frost-ms_risk.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": [{"properties": {"seg_ids": ["a"], "pad": "x" * 600_000}}]}))
    problems = " | ".join(validate(tmp_path))
    assert "meta.json does not parse" in problems
    assert "risk layer is bigger than" in problems


# ---- run_all

def test_steps_run_in_pipeline_order_with_traffic_volume_before_training() -> None:
    ids = [i for i, _ in steps_to_run(use_aadt=True)]
    assert ids.index("s09") < ids.index("s07") < ids.index("s08") < ids.index("s10") < ids.index("s11")
    assert ids[0] == "s01" and ids[-1] == "validate"


def test_resume_and_skipping_the_optional_step() -> None:
    assert [i for i, _ in steps_to_run("s05", use_aadt=True)][0] == "s05"
    assert "s09" not in [i for i, _ in steps_to_run(use_aadt=False)]
    assert [i for i, _ in steps_to_run("s09", use_aadt=False)][0] == "s07"   # nothing to run for s09 itself
    with pytest.raises(ValueError):
        steps_to_run("s99")
    assert len(STEPS) == len({i for i, _ in STEPS})
