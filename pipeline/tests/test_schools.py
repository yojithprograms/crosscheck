import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

from crosscheck_pipeline import config
from crosscheck_pipeline.s01_schools import (
    PILOT_COLUMNS,
    compare_to_reference,
    load_pilot,
    validate_pilot,
)


def make_pilot(**overrides) -> pd.DataFrame:
    row = {
        "school_id": "frost-ms",
        "name": "Robert Frost Middle School",
        "level": "MS",
        "entrance_lat": 38.836,
        "entrance_lon": -77.273,
        "radius_m": float("nan"),
    }
    row.update(overrides)
    return pd.DataFrame([row], columns=PILOT_COLUMNS)


def test_valid_pilot_has_no_problems() -> None:
    assert validate_pilot(make_pilot()) == []


def test_swapped_lat_lon_is_caught() -> None:
    problems = validate_pilot(make_pilot(entrance_lat=-77.273, entrance_lon=38.836))
    assert any("outside the study box" in p for p in problems)


@pytest.mark.parametrize("bad_id", ["Frost MS", "frost_ms", "-frost", "frost-", "FROST"])
def test_bad_school_id_is_caught(bad_id: str) -> None:
    assert any("school_id" in p for p in validate_pilot(make_pilot(school_id=bad_id)))


def test_bad_level_is_caught() -> None:
    assert any("level" in p for p in validate_pilot(make_pilot(level="JR")))


def test_duplicate_ids_and_missing_columns_are_caught() -> None:
    both = pd.concat([make_pilot(), make_pilot()], ignore_index=True)
    assert any("duplicate" in p for p in validate_pilot(both))
    assert validate_pilot(make_pilot().drop(columns=["level"])) == ["missing columns: ['level']"]


def test_blank_radius_uses_level_default(tmp_path) -> None:
    path = tmp_path / "pilot.csv"
    make_pilot().to_csv(path, index=False)
    loaded = load_pilot(path)
    assert loaded.loc[0, "radius_m"] == config.DEFAULT_RADIUS_M["MS"]


def test_given_radius_is_kept(tmp_path) -> None:
    path = tmp_path / "pilot.csv"
    make_pilot(radius_m=1800).to_csv(path, index=False)
    assert load_pilot(path).loc[0, "radius_m"] == 1800


def test_invalid_csv_raises(tmp_path) -> None:
    path = tmp_path / "pilot.csv"
    make_pilot(level="JR").to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_pilot(path)


def test_compare_uses_same_level_only() -> None:
    # An "Alternative Court" sits exactly on the entrance; the real middle school is ~100 m away.
    reference = gpd.GeoDataFrame(
        {
            "SCHOOL_NAME": ["ISAEP CENTRAL", "FROST"],
            "TYPE_DESC": ["Alternative Court", "Middle School"],
        },
        geometry=[Point(-77.273, 38.836), Point(-77.273, 38.8369)],
        crs="EPSG:4326",
    )
    report = compare_to_reference(make_pilot(), reference)
    assert report.loc[0, "SCHOOL_NAME"] == "FROST"
    assert not report.loc[0, "check"]


def test_far_entrance_is_flagged() -> None:
    reference = gpd.GeoDataFrame(
        {"SCHOOL_NAME": ["FROST"], "TYPE_DESC": ["Middle School"]},
        geometry=[Point(-77.30, 38.86)],  # several km away
        crs="EPSG:4326",
    )
    assert compare_to_reference(make_pilot(), reference).loc[0, "check"]
