import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import LineString

from crosscheck_pipeline import config
from crosscheck_pipeline.s09_aadt import build_aadt_table, match_adt

CRS = config.CRS_METERS


def segs(*lines, highway="residential") -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {"seg_id": [f"s{i}" for i in range(len(lines))], "highway": [highway] * len(lines)},
        geometry=[LineString(c) for c in lines], crs=CRS,
    )


def counts(*rows: tuple[list, float]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"ADT": [r[1] for r in rows]}, geometry=[LineString(r[0]) for r in rows], crs=CRS)


ARTERIAL = [(0, 0), (500, 0)]          # a 500 m east-west count line, ADT 30,000


def test_parallel_segment_on_the_count_line_matches() -> None:
    result = match_adt(segs([(100, 3), (200, 3)]), counts((ARTERIAL, 30000)))
    assert result.iloc[0] == 30000


def test_a_side_street_touching_the_arterial_does_not_inherit_its_count() -> None:
    side_street = [(250, 0), (250, 100)]    # starts on the arterial but runs perpendicular to it
    short_spur = [(250, 2), (250, 12)]      # short enough that its midpoint is within 15 m of the arterial
    result = match_adt(segs(side_street, short_spur), counts((ARTERIAL, 30000)))
    assert result.isna().all()


def test_segment_far_from_any_count_line_is_unmatched() -> None:
    assert np.isnan(match_adt(segs([(100, 80), (200, 80)]), counts((ARTERIAL, 30000))).iloc[0])


def test_closest_parallel_line_wins_and_ties_take_the_larger_count() -> None:
    near, far = [(0, 2), (500, 2)], [(0, 9), (500, 9)]
    result = match_adt(segs([(100, 0), (200, 0)]), counts((far, 5000), (near, 12000)))
    assert result.iloc[0] == 12000
    same_place = match_adt(segs([(100, 0), (200, 0)]), counts((near, 12000), (near, 18000)))
    assert same_place.iloc[0] == 18000


def test_angle_limit_is_configurable() -> None:
    diagonal = [(100, 0), (150, 20)]       # about 22 degrees off the arterial; midpoint 10 m from it
    assert match_adt(segs(diagonal), counts((ARTERIAL, 9000)), max_angle_deg=30).iloc[0] == 9000
    assert np.isnan(match_adt(segs(diagonal), counts((ARTERIAL, 9000)), max_angle_deg=10).iloc[0])


def test_no_counts_returns_all_missing() -> None:
    empty = gpd.GeoDataFrame({"ADT": []}, geometry=[], crs=CRS)
    assert match_adt(segs([(0, 0), (10, 0)]), empty).isna().all()


def test_unmatched_segments_get_their_class_median_and_a_flag() -> None:
    frame = segs([(0, 0), (10, 0)], [(0, 5), (10, 5)], [(0, 9), (10, 9)], [(0, 20), (10, 20)])
    frame["highway"] = ["primary", "primary", "residential", "residential"]
    matched = pd.Series([20000.0, 30000.0, np.nan, np.nan], index=frame.index)
    table = build_aadt_table(frame, matched)
    assert table["aadt_imputed"].tolist() == [0, 0, 1, 1]
    # No residential segment was matched, so the overall median of matched segments (25,000) is used.
    assert table["adt"].tolist() == [20000, 30000, 25000, 25000]
    assert table["log_aadt"].iloc[0] == pytest.approx(np.log1p(20000))
    assert list(table.columns) == ["seg_id", "adt", "log_aadt", "aadt_imputed"]


# ---- how traffic volume plugs into training and reasons

def test_evaluate_models_runs_with_and_without_traffic_volume(synthetic_segments) -> None:
    from crosscheck_pipeline.s07_train import evaluate_models, feature_lists

    road_without, all_without = feature_lists(False)
    road_with, all_with = feature_lists(True)
    assert set(all_with) - set(all_without) == {"log_aadt", "aadt_imputed"}
    assert set(road_with) - set(road_without) == {"log_aadt", "aadt_imputed"}
    without = evaluate_models(synthetic_segments, use_aadt=False)
    with_aadt = evaluate_models(synthetic_segments, use_aadt=True)
    assert set(without) == set(with_aadt)
    assert with_aadt["full"]["roc_auc"] != without["full"]["roc_auc"]   # the extra columns really are used


def test_traffic_reason_needs_a_measured_high_count_and_a_positive_push() -> None:
    from crosscheck_pipeline.utils.reasons import segment_reason_items

    row = {"crashes_recent": 0, "crashes_recent_ka": 0, "speed_mph": 25, "speed_imputed": 0, "lanes": 2,
           "sidewalk_cov": 0.9, "sidewalk_known": 1, "highway": "residential", "adt": 18420.0, "aadt_imputed": 0}
    push = {f: 0.0 for f in ["speed_mph", "lanes", "sidewalk_cov", "no_sidewalk_fast", "class_trunk", "class_primary"]}
    push["log_aadt"] = 0.3
    assert [r.text for r in segment_reason_items(row, push)] == ["About 18,400 cars a day"]
    assert segment_reason_items({**row, "aadt_imputed": 1}, push) == []          # estimated: never shown
    assert segment_reason_items({**row, "adt": 4000.0}, push) == []              # below AADT_REASON_MIN
    assert segment_reason_items(row, {**push, "log_aadt": -0.3}) == []           # doesn't push risk up
