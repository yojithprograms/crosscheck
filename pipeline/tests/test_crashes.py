from typing import Any

import pandas as pd

from crosscheck_pipeline.s02_crashes import OUTPUT_COLUMNS, clean_crashes, crashes_by_year_and_mode

# 2021-03-05 12:00:00 UTC in epoch milliseconds
MARCH_5_2021_MS = 1614945600000


def feature(doc: int, *, ped: str = "1", bike: str = "0", severity: str = "C", year: str = "2021",
            geometry: dict[str, Any] | None = None, **props: Any) -> dict[str, Any]:
    if geometry is None:
        geometry = {"type": "Point", "coordinates": [-77.27, 38.84]}
    properties = {
        "DOCUMENT_NBR": doc, "CRASH_YEAR": year, "CRASH_DT": MARCH_5_2021_MS,
        "CRASH_SEVERITY": severity, "PED_NONPED": ped, "BIKE_NONBIKE": bike,
        "PEDESTRIANS_KILLED": 0, "PEDESTRIANS_INJURED": 1, "LIGHT_CONDITION": "1. Daylight",
        "INTERSECTION_TYPE": "1. Not at Intersection", "SCHOOL_ZONE": "3. No",
        "ROUTE_OR_STREET_NM": "PICKETT RD", **props,
    }
    return {"type": "Feature", "geometry": geometry, "properties": properties}


def test_clean_basic_fields() -> None:
    crashes, dropped = clean_crashes([feature(1)])
    assert list(crashes.columns) == OUTPUT_COLUMNS
    row = crashes.iloc[0]
    assert row["year"] == 2021
    assert row["mode"] == "ped"
    assert row["street"] == "PICKETT RD"
    assert row["date"] == pd.Timestamp("2021-03-05 12:00:00", tz="UTC")
    assert dropped == {"raw": 1, "no_geometry": 0, "no_year": 0, "duplicate": 0}


def test_mode_is_ped_or_bike() -> None:
    crashes, _ = clean_crashes([
        feature(1, ped="1", bike="0"),
        feature(2, ped="0", bike="1"),
        feature(3, ped="1", bike="1"),  # both flags: counted as ped
    ])
    assert crashes["mode"].tolist() == ["ped", "bike", "ped"]


def test_ka_flag_is_true_only_for_k_and_a() -> None:
    crashes, _ = clean_crashes([feature(i, severity=s) for i, s in enumerate("KABCO")])
    assert crashes["ka"].tolist() == [True, True, False, False, False]


def test_rows_without_geometry_are_dropped_even_if_lat_lon_exist() -> None:
    crashes, dropped = clean_crashes([
        feature(1),
        {**feature(2, LAT=38.8, LON=-77.2), "geometry": None},
    ])
    assert crashes["doc_nbr"].tolist() == [1]
    assert dropped["no_geometry"] == 1


def test_duplicate_report_numbers_are_dropped() -> None:
    crashes, dropped = clean_crashes([feature(7), feature(7), feature(8)])
    assert crashes["doc_nbr"].tolist() == [7, 8]
    assert dropped["duplicate"] == 1


def test_missing_year_is_dropped_and_counted() -> None:
    crashes, dropped = clean_crashes([feature(1), feature(2, year="")])
    assert len(crashes) == 1
    assert dropped["no_year"] == 1


def test_missing_counts_become_zero() -> None:
    crashes, _ = clean_crashes([feature(1, PEDESTRIANS_KILLED=None, PEDESTRIANS_INJURED=None)])
    assert crashes.loc[0, "ped_killed"] == 0 and crashes.loc[0, "ped_injured"] == 0


def test_empty_input_gives_empty_table() -> None:
    crashes, dropped = clean_crashes([])
    assert len(crashes) == 0 and dropped["raw"] == 0


def test_year_mode_table() -> None:
    crashes, _ = clean_crashes([
        feature(1, year="2021"), feature(2, year="2021", ped="0", bike="1"), feature(3, year="2022"),
    ])
    table = crashes_by_year_and_mode(crashes)
    assert table.loc[2021, "ped"] == 1 and table.loc[2021, "bike"] == 1
    assert table.loc[2022, "ped"] == 1 and table.loc[2022, "bike"] == 0
