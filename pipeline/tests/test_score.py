import json

import numpy as np
import pandas as pd
import pytest

from crosscheck_pipeline import config
from crosscheck_pipeline.s07_train import ALL_FEATURES, add_log_hist, make_model
from crosscheck_pipeline.s08_score import contributions, risk_classes, score_segments
from crosscheck_pipeline.utils.reasons import (
    ASK_ABOUT,
    GENERIC_CONTEXT_TEXT,
    crash_history_text,
    segment_reason_items,
)


# ---- classes

def test_risk_class_thresholds() -> None:
    pct = pd.Series([0.0, 69.9, 70.0, 89.9, 90.0, 100.0])
    assert risk_classes(pct).tolist() == ["low", "low", "medium", "medium", "high", "high"]


# ---- reasons

def row(**overrides) -> dict:
    base = {"crashes_recent": 0, "crashes_recent_ka": 0, "speed_mph": 25, "speed_imputed": 0, "lanes": 2,
            "sidewalk_cov": 0.9, "sidewalk_known": 1, "highway": "residential",
            "length_m": 80.0, "marked_crossings": 0, "bus_stops_200m": 0}
    base.update(overrides)
    return base


def pushes(**overrides) -> dict:
    base = {f: 0.0 for f in ["speed_mph", "lanes", "sidewalk_cov", "no_sidewalk_fast", "class_trunk", "class_primary",
                             "class_secondary", "class_tertiary", "bus_stops_200m", "marked_crossings", "log_length"]}
    base.update(overrides)
    return base


def texts(items) -> list[str]:
    return [i.text for i in items]


def test_crash_history_wording() -> None:
    assert crash_history_text(1, 0) == "1 crash involving someone walking or biking here since 2022"
    assert crash_history_text(2, 1) == (
        "2 crashes involving someone walking or biking here since 2022, 1 with serious or fatal injuries")


def test_quiet_street_has_no_reasons() -> None:
    assert segment_reason_items(row(), pushes()) == []


def test_crash_history_is_always_first_and_needs_no_contribution() -> None:
    items = segment_reason_items(row(crashes_recent=2, lanes=4), pushes(lanes=0.9))
    assert items[0].kind == "crashes" and items[1].kind == "lanes"
    # Even with nothing else going on, a crash since 2022 is shown.
    assert [i.kind for i in segment_reason_items(row(crashes_recent=1), pushes())] == ["crashes"]


def test_a_reason_needs_both_its_condition_and_a_positive_push() -> None:
    fast = row(speed_mph=40)
    assert texts(segment_reason_items(fast, pushes(speed_mph=0.3))) == ["Speed limit is 40 mph"]
    assert segment_reason_items(fast, pushes(speed_mph=-0.3)) == []           # condition true, push negative
    assert segment_reason_items(row(speed_mph=25), pushes(speed_mph=0.3)) == []  # push positive, condition false
    assert segment_reason_items(row(speed_mph=config.FAST_MPH - 1), pushes(speed_mph=1.0)) == []


def test_estimated_speed_is_marked() -> None:
    items = segment_reason_items(row(speed_mph=40, speed_imputed=1), pushes(speed_mph=0.3))
    assert texts(items) == ["Speed limit ≈ 40 mph (estimated)"]


def test_no_sidewalk_needs_known_coverage() -> None:
    missing = row(sidewalk_cov=0.0)
    assert texts(segment_reason_items(missing, pushes(sidewalk_cov=0.2))) == ["No sidewalk along most of this stretch"]
    assert segment_reason_items(row(sidewalk_cov=0.0, sidewalk_known=0), pushes(sidewalk_cov=0.2)) == []
    # The two sidewalk features' pushes are added together.
    assert segment_reason_items(missing, pushes(sidewalk_cov=-0.4, no_sidewalk_fast=0.3)) == []
    assert segment_reason_items(missing, pushes(sidewalk_cov=-0.1, no_sidewalk_fast=0.3)) != []


def test_major_road_reason_for_trunk_and_primary_only() -> None:
    p = pushes(class_primary=0.4)
    assert texts(segment_reason_items(row(highway="primary"), p)) == ["Major road with heavy traffic"]
    assert texts(segment_reason_items(row(highway="trunk"), pushes(class_trunk=0.2))) == ["Major road with heavy traffic"]
    assert segment_reason_items(row(highway="secondary"), pushes(class_primary=0.4)) == []


def test_reasons_are_ordered_by_push_and_capped_at_three() -> None:
    busy = row(crashes_recent=1, speed_mph=45, lanes=4, sidewalk_cov=0.0, highway="primary")
    items = segment_reason_items(busy, pushes(speed_mph=0.1, lanes=0.5, sidewalk_cov=0.3, class_primary=0.2))
    assert len(items) == config.MAX_REASONS == 3
    assert [i.kind for i in items] == ["crashes", "lanes", "no_sidewalk"]  # crash first, then by push: 0.5, 0.3


def test_every_ask_about_key_is_a_known_reason_kind() -> None:
    assert set(ASK_ABOUT) <= {"speed", "lanes", "no_sidewalk", "no_signal"}


# ---- context (fallback) reasons

def test_no_fallback_for_low_risk_or_when_no_class_is_given() -> None:
    busy = row(highway="tertiary", bus_stops_200m=4)
    p = pushes(class_tertiary=0.3, bus_stops_200m=0.2)
    assert segment_reason_items(busy, p) == []
    assert segment_reason_items(busy, p, "low") == []


def test_fallback_uses_true_drivers_in_order_of_push() -> None:
    busy = row(highway="tertiary", bus_stops_200m=4, marked_crossings=5, length_m=300.0)
    p = pushes(class_tertiary=0.30, bus_stops_200m=0.25, marked_crossings=0.05, log_length=0.5)
    items = segment_reason_items(busy, p, "high")
    # Largest pushes first, at most MAX_CONTEXT_REASONS (2): long stretch (0.5), road type (0.30).
    assert [i.kind for i in items] == ["long_stretch", "road_type"]
    assert items[1].text == "A busier through street, not a quiet neighborhood road"


def test_fallback_conditions_and_negative_pushes_are_respected() -> None:
    p = pushes(bus_stops_200m=0.3, marked_crossings=0.3)
    items = segment_reason_items(row(bus_stops_200m=0, marked_crossings=2), p, "medium")
    assert [i.kind for i in items] == ["generic"]                      # conditions false -> generic
    items = segment_reason_items(row(bus_stops_200m=3), pushes(bus_stops_200m=-0.3), "medium")
    assert [i.kind for i in items] == ["generic"]                      # push negative -> generic


def test_generic_fallback_text_matches_the_class() -> None:
    assert texts(segment_reason_items(row(), pushes(), "high")) == [GENERIC_CONTEXT_TEXT["high"]]
    assert texts(segment_reason_items(row(), pushes(), "medium")) == [GENERIC_CONTEXT_TEXT["medium"]]


def test_fallback_is_not_used_when_an_appendix_a_reason_exists() -> None:
    items = segment_reason_items(row(crashes_recent=1, highway="tertiary", bus_stops_200m=4),
                                 pushes(class_tertiary=0.3, bus_stops_200m=0.3), "high")
    assert [i.kind for i in items] == ["crashes"]


# ---- scoring on the synthetic fixture

@pytest.fixture
def bundle_and_segments(synthetic_segments):
    frame = add_log_hist(synthetic_segments, "hist_train")
    model = make_model().fit(frame[ALL_FEATURES], frame["y"])
    segments = synthetic_segments.assign(
        name="Test Rd", crashes_recent=synthetic_segments["hist_serve"],
        crashes_recent_ka=(synthetic_segments["hist_serve"] > 1).astype(int),
    )
    return {"pipeline": model, "features": ALL_FEATURES, "model_version": "test"}, segments


def test_contributions_add_up_to_the_models_log_odds(bundle_and_segments) -> None:
    bundle, segments = bundle_and_segments
    features = add_log_hist(segments, "hist_serve")
    pushes_table = contributions(bundle, features)
    pipeline = bundle["pipeline"]
    rebuilt = pushes_table.sum(axis=1) + pipeline.named_steps["lr"].intercept_[0]
    np.testing.assert_allclose(rebuilt, pipeline.decision_function(features[ALL_FEATURES]), atol=1e-9)


def test_score_segments_adds_percentiles_classes_and_reasons(bundle_and_segments) -> None:
    bundle, segments = bundle_and_segments
    scored = score_segments(segments, bundle)
    assert scored["risk_pct"].between(0, 100).all() and scored["risk_pct"].max() == 100
    shares = scored["risk_class"].value_counts(normalize=True)
    assert shares["high"] == pytest.approx(0.10, abs=0.01)
    assert shares["medium"] == pytest.approx(0.20, abs=0.01)
    assert scored["reasons"].map(len).max() <= config.MAX_REASONS
    with_crashes = scored[scored["crashes_recent"] >= 1]
    assert len(with_crashes) > 0
    assert with_crashes["reasons"].map(lambda r: "crash" in r[0]).all()
    assert set(json.loads(scored["contribs"].iloc[0])) == set(ALL_FEATURES)
    # A colored street (medium or high) always gets at least one reason.
    colored = scored[scored["risk_class"].isin(["medium", "high"])]
    assert (colored["reasons"].map(len) >= 1).all()


def test_scoring_uses_the_serving_history_window(bundle_and_segments) -> None:
    """Scores use hist_serve (2022–2025), so piling crashes onto one segment must raise its percentile."""
    bundle, segments = bundle_and_segments
    weight = bundle["pipeline"].named_steps["lr"].coef_[0][ALL_FEATURES.index("log_hist")]
    assert weight > 0
    target = segments.index[0]
    base = score_segments(segments, bundle)
    boosted_input = segments.copy()
    boosted_input.loc[target, "hist_serve"] = 50
    boosted = score_segments(boosted_input, bundle)
    assert boosted.loc[target, "risk_pct"] > base.loc[target, "risk_pct"]
