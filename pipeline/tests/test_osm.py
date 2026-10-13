import math

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, Point, Polygon

from crosscheck_pipeline import config
from crosscheck_pipeline.s03_osm import build_study_area, keep_lines, keep_points


def make_pilot(*coords: tuple[float, float], radius_m: int = 1600) -> pd.DataFrame:
    return pd.DataFrame(
        {"entrance_lat": [c[0] for c in coords], "entrance_lon": [c[1] for c in coords], "radius_m": radius_m}
    )


def area_km2(geom) -> float:
    return gpd.GeoSeries([geom], crs="EPSG:4326").to_crs(config.CRS_METERS).area.iloc[0] / 1e6


def test_pilot_area_is_a_circle_of_the_configured_radius() -> None:
    area = build_study_area(make_pilot((38.836, -77.273)), mode="pilot")
    expected = math.pi * (config.PILOT_AREA_RADIUS_M / 1000) ** 2
    assert area_km2(area) == pytest.approx(expected, rel=0.01)


def test_pilot_area_contains_nearby_points_but_not_far_ones() -> None:
    area = build_study_area(make_pilot((38.836, -77.273)), mode="pilot")
    assert area.contains(Point(-77.273, 38.836))
    assert area.contains(Point(-77.273, 38.836 + 7000 / 110540))   # 7 km north
    assert not area.contains(Point(-77.273, 38.836 + 12000 / 110540))  # 12 km north


def test_two_far_apart_schools_give_two_parts() -> None:
    area = build_study_area(make_pilot((38.836, -77.273), (39.05, -77.0)), mode="pilot")
    assert area.geom_type == "MultiPolygon" and len(area.geoms) == 2


def test_school_zone_is_always_included_even_with_a_big_radius() -> None:
    # radius_m + SCHOOL_BUFFER_EXTRA_M larger than PILOT_AREA_RADIUS_M must still be covered
    big = config.PILOT_AREA_RADIUS_M + 1000
    area = build_study_area(make_pilot((38.836, -77.273), radius_m=big), mode="pilot")
    assert area.contains(Point(-77.273, 38.836 + (big + 200) / 110540))


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        build_study_area(make_pilot((38.836, -77.273)), mode="galaxy")


def test_keep_points_drops_lines_and_adds_missing_columns() -> None:
    features = gpd.GeoDataFrame(
        {"highway": ["bus_stop", "crossing"], "name": ["a", "b"]},
        geometry=[Point(0, 0), LineString([(0, 0), (1, 1)])],
        crs="EPSG:4326",
    )
    pts = keep_points(features)
    assert list(pts.columns) == ["highway", "crossing", "geometry"]
    assert len(pts) == 1 and pts.loc[0, "highway"] == "bus_stop"
    assert pts.loc[0, "crossing"] is None


def test_keep_lines_drops_points_and_polygons() -> None:
    features = gpd.GeoDataFrame(
        {"highway": ["footway"] * 3, "footway": ["sidewalk"] * 3},
        geometry=[LineString([(0, 0), (1, 1)]), Point(0, 0), Polygon([(0, 0), (1, 0), (1, 1)])],
        crs="EPSG:4326",
    )
    lines = keep_lines(features)
    assert len(lines) == 1 and lines.geometry.iloc[0].geom_type == "LineString"
