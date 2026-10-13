"""Shared test fixtures."""
import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString

from crosscheck_pipeline import config
from crosscheck_pipeline.s05_segments import CLASS_COLUMNS


@pytest.fixture
def synthetic_segments() -> gpd.GeoDataFrame:
    """Fake labeled road segments (the shape of segments_labeled.parquet) with a known risk pattern.

    Risk goes up with speed, lanes, and having no sidewalk on a fast road, so a model that uses
    those features should beat "longer segments have more crashes". Crash history from the earlier
    window (hist_train) comes from the same hidden risk, so it carries real signal too.
    Segments sit on a 12 km × 12 km grid so spatial cross-validation has many cells to split on.
    """
    rng = np.random.default_rng(config.RANDOM_SEED)
    n = 4000
    x0 = rng.uniform(0, 12_000, n)
    y0 = rng.uniform(0, 12_000, n)
    length = rng.uniform(20, 300, n)
    geometry = [LineString([(x, y), (x + dx, y)]) for x, y, dx in zip(x0, y0, length)]

    highway = rng.choice(["residential", "tertiary", "secondary", "primary", "service"], n, p=[0.5, 0.15, 0.1, 0.1, 0.15])
    speed = np.select([highway == "primary", highway == "secondary", highway == "tertiary", highway == "service"],
                      [45, 35, 30, 15], default=25)
    lanes = np.select([highway == "primary", highway == "secondary"], [4, 2], default=2) + (rng.random(n) < 0.1)
    sidewalk_cov = np.clip(rng.normal(0.6, 0.4, n), 0, 1)
    no_sidewalk_fast = ((sidewalk_cov < config.NO_SIDEWALK_COV) & (speed >= config.FAST_MPH)).astype(int)

    logit = -6.0 + 0.06 * speed + 0.35 * lanes + 1.2 * no_sidewalk_fast + 0.8 * np.log(length / 100) + rng.normal(0, 0.4, n)
    rate = np.exp(logit)
    hist_train = rng.poisson(rate)
    label_count = rng.poisson(rate)
    hist_serve = rng.poisson(rate)

    data = {
        "seg_id": [f"{i}-{i + 1}-0" for i in range(n)],
        "highway": highway,
        "length_m": length,
        "log_length": np.log(length + 1),
        "speed_mph": speed,
        "speed_imputed": rng.integers(0, 2, n),
        "lanes": lanes,
        "lanes_imputed": rng.integers(0, 2, n),
        "oneway": rng.integers(0, 2, n),
        "sidewalk_cov": sidewalk_cov,
        "sidewalk_known": np.ones(n, dtype=int),
        "no_sidewalk_fast": no_sidewalk_fast,
        "signal_end": rng.integers(0, 2, n),
        "marked_crossings": rng.poisson(3, n),
        "bus_stops_200m": rng.integers(0, 6, n),
        "hist_train": hist_train,
        "label_count": label_count,
        "hist_serve": hist_serve,
    }
    for column in CLASS_COLUMNS:
        data[column] = (highway == column.removeprefix("class_")).astype(int)
    frame = gpd.GeoDataFrame(data, geometry=geometry, crs=config.CRS_METERS)
    frame["y"] = (frame["label_count"] > 0).astype(int)
    return frame
