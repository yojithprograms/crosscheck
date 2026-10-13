"""Tests for Step 1.7 ★ (written by the student in crosscheck_pipeline/s07_train.py).

These tests skip until s07_train.py exists. They describe the behavior DESIGN.md §6 Step 1.7 asks
for. The function names are suggestions: rename them if you like, and change the tests to match.

    spatial_groups(segments, cell_m=config.GRID_CELL_M) -> array, one group id per segment
    top_fraction_capture(scores, label_count, fraction=0.10) -> float
    evaluate_models(segments) -> {model_name: {"roc_auc", "pr_auc", "top10_capture", "lift"}}
        model names: "length_only", "history_only", "roads_only", "full"
"""
import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString

from crosscheck_pipeline import config

s07 = pytest.importorskip("crosscheck_pipeline.s07_train")

MODEL_NAMES = {"length_only", "history_only", "roads_only", "full"}
METRIC_NAMES = {"roc_auc", "pr_auc", "top10_capture", "lift"}


# ---- spatial groups

def test_segments_in_the_same_grid_cell_share_a_group() -> None:
    cell = 2000
    # Segment midpoints: (500, 500), (1500, 1900) -> same cell; (2500, 500) and (500, 2500) -> different cells.
    segments = gpd.GeoDataFrame(
        geometry=[
            LineString([(400, 500), (600, 500)]),
            LineString([(1400, 1900), (1600, 1900)]),
            LineString([(2400, 500), (2600, 500)]),
            LineString([(500, 2400), (500, 2600)]),
        ],
        crs=config.CRS_METERS,
    )
    groups = np.asarray(s07.spatial_groups(segments, cell))
    assert len(groups) == 4
    assert groups[0] == groups[1]
    assert len({groups[0], groups[2], groups[3]}) == 3


def test_a_segment_straddling_a_cell_edge_uses_its_midpoint() -> None:
    # Runs from x=1900 to x=2100: the midpoint x=2000 is the start of cell 1, so it joins cell 1, not cell 0.
    segments = gpd.GeoDataFrame(
        geometry=[
            LineString([(1900, 500), (2100, 500)]),   # midpoint (2000, 500)
            LineString([(2400, 500), (2600, 500)]),   # midpoint (2500, 500), cell 1
            LineString([(400, 500), (600, 500)]),     # midpoint (500, 500), cell 0
        ],
        crs=config.CRS_METERS,
    )
    groups = np.asarray(s07.spatial_groups(segments, 2000))
    assert groups[0] == groups[1] != groups[2]


# ---- top-10% capture

def test_capture_counts_crashes_not_segments() -> None:
    # 10 segments; the highest score (10) has 3 of the 4 crashes. Top 10% of 10 segments = 1 segment.
    scores = np.arange(1, 11)
    label_count = np.array([0, 0, 0, 0, 0, 1, 0, 0, 0, 3])
    assert s07.top_fraction_capture(scores, label_count, 0.10) == pytest.approx(0.75)


def test_capture_ranks_by_score_not_by_position() -> None:
    scores = np.array([5.0, 1.0, 9.0, 3.0, 7.0, 2.0, 8.0, 4.0, 6.0, 10.0])
    label_count = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 2])  # all crashes on the top-scored segment (last row)
    assert s07.top_fraction_capture(scores, label_count, 0.10) == pytest.approx(1.0)
    assert s07.top_fraction_capture(-scores, label_count, 0.10) == pytest.approx(0.0)  # reversed ranking misses it


def test_capture_takes_the_top_tenth_of_segments() -> None:
    scores = np.arange(1, 21)                      # 20 segments -> top 10% = 2 segments (scores 20 and 19)
    label_count = np.zeros(20, dtype=int)
    label_count[[19, 18, 0, 1]] = 1                # 2 crashes in the top two, 2 elsewhere
    assert s07.top_fraction_capture(scores, label_count, 0.10) == pytest.approx(0.5)


def test_perfect_and_random_rankings_bracket_the_capture() -> None:
    rng = np.random.default_rng(0)
    n = 2000
    label_count = (rng.random(n) < 0.03).astype(int)
    perfect = s07.top_fraction_capture(label_count + rng.random(n) * 0.01, label_count, 0.10)
    random = s07.top_fraction_capture(rng.random(n), label_count, 0.10)
    assert perfect > 0.95
    assert 0.0 <= random < 0.30  # a random 10% of segments should hold about 10% of the crashes


# ---- the four-model comparison

@pytest.fixture
def results(synthetic_segments):
    return s07.evaluate_models(synthetic_segments)


def test_all_four_models_report_all_metrics(results) -> None:
    assert set(results) == MODEL_NAMES
    for metrics in results.values():
        assert METRIC_NAMES <= set(metrics)
        assert 0.0 <= metrics["roc_auc"] <= 1.0
        assert 0.0 <= metrics["pr_auc"] <= 1.0
        assert 0.0 <= metrics["top10_capture"] <= 1.0


def test_lift_is_capture_divided_by_ten_percent(results) -> None:
    for metrics in results.values():
        assert metrics["lift"] == pytest.approx(metrics["top10_capture"] / 0.10)


def test_models_that_use_road_features_beat_length_only(results) -> None:
    # In the synthetic data, risk is driven by speed, lanes, and sidewalks, so these should clearly win.
    assert results["roads_only"]["roc_auc"] > results["length_only"]["roc_auc"]
    assert results["full"]["roc_auc"] > results["length_only"]["roc_auc"]
    assert results["full"]["top10_capture"] > results["length_only"]["top10_capture"]


def test_full_model_is_at_least_as_good_as_history_only(results) -> None:
    assert results["full"]["roc_auc"] >= results["history_only"]["roc_auc"]


def test_training_never_looks_at_the_serving_window(synthetic_segments, results) -> None:
    """hist_serve (2022–2025) overlaps the label years (2021–2024). Using it to train would be cheating."""
    changed = s07.evaluate_models(synthetic_segments.assign(hist_serve=1000))
    for name in MODEL_NAMES:
        for metric in METRIC_NAMES:
            assert changed[name][metric] == pytest.approx(results[name][metric])
