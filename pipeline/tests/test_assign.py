import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point

from crosscheck_pipeline import config
from crosscheck_pipeline.s06_assign import add_crash_counts, assign_crashes

CRS = config.CRS_METERS


def segments() -> gpd.GeoDataFrame:
    # Two parallel 100 m roads: "A" along y=0 and "B" along y=100.
    return gpd.GeoDataFrame(
        {"seg_id": ["A", "B"]},
        geometry=[LineString([(0, 0), (100, 0)]), LineString([(0, 100), (100, 100)])],
        crs=CRS,
    )


def crashes(*rows: tuple[float, float, int, bool]) -> gpd.GeoDataFrame:
    """rows: (x, y, year, ka)"""
    return gpd.GeoDataFrame(
        {"year": [r[2] for r in rows], "ka": [r[3] for r in rows], "doc_nbr": range(len(rows))},
        geometry=[Point(r[0], r[1]) for r in rows],
        crs=CRS,
    )


def test_matches_nearest_segment_within_the_limit() -> None:
    matched, unmatched = assign_crashes(
        crashes((50, 10, 2022, False), (50, 90, 2022, False), (50, 50, 2022, False)), segments(), max_dist_m=30
    )
    assert dict(zip(matched["doc_nbr"], matched["seg_id"])) == {0: "A", 1: "B"}
    assert unmatched["doc_nbr"].tolist() == [2]  # 50 m from both roads
    assert matched["dist_m"].tolist() == pytest.approx([10, 10])


def test_a_crash_equidistant_from_two_segments_is_matched_once() -> None:
    matched, unmatched = assign_crashes(crashes((50, 50, 2022, False)), segments(), max_dist_m=60)
    assert len(matched) == 1 and len(unmatched) == 0


def test_no_crashes_at_all() -> None:
    matched, unmatched = assign_crashes(crashes(), segments())
    assert len(matched) == 0 and len(unmatched) == 0


def labeled(*rows: tuple[float, float, int, bool]) -> gpd.GeoDataFrame:
    matched, _ = assign_crashes(crashes(*rows), segments(), max_dist_m=30)
    return add_crash_counts(segments(), matched).set_index("seg_id")


def test_year_windows_count_the_right_crashes() -> None:
    # All on road A (y=0), one per year of interest.
    result = labeled(
        (10, 1, 2016, False),                      # before everything
        (20, 1, 2018, False),                      # TRAIN_HIST (2017–2020)
        (30, 1, 2020, False),                      # TRAIN_HIST edge
        (40, 1, 2021, True),                       # TRAIN_LABEL (2021–2024), K/A
        (50, 1, 2024, False),                      # TRAIN_LABEL and SERVE_HIST (2022–2025) edge
        (60, 1, 2025, True),                       # SERVE_HIST and recent, K/A
        (70, 1, 2026, True),                       # preliminary year, recent, K/A
    ).loc["A"]
    assert result["hist_train"] == 2
    assert result["label_count"] == 2
    assert result["hist_serve"] == 2
    assert result["crashes_recent"] == 3          # 2024, 2025, 2026 (MAP_CRASHES_FROM = 2022)
    assert result["crashes_recent_ka"] == 2       # 2025 and 2026
    assert result["crashes_prelim"] == 1
    assert result["y"] == 1


def test_segments_without_crashes_get_zero_and_y_false() -> None:
    result = labeled((10, 1, 2022, False)).loc["B"]
    assert result[["hist_train", "label_count", "hist_serve", "crashes_recent", "crashes_prelim", "y"]].tolist() == [0] * 6


def test_label_uses_label_window_only() -> None:
    # A crash in 2019 is history, not a label, so y stays 0.
    result = labeled((10, 1, 2019, False)).loc["A"]
    assert result["hist_train"] == 1 and result["label_count"] == 0 and result["y"] == 0


def test_original_columns_are_kept() -> None:
    out = labeled((10, 1, 2022, False))
    assert isinstance(out, pd.DataFrame) and "geometry" in out.columns
