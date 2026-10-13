from typing import Any

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, box

from crosscheck_pipeline import config
from crosscheck_pipeline.s04_sidewalks import (
    cells_gdf,
    combine_sidewalks,
    coverage_table,
    download_county_sidewalks,
    features_to_gdf,
    length_by_cell,
    split_county,
)

AREA = box(-77.30, 38.83, -77.25, 38.87)  # lon/lat study-area stand-in


def feat(lon: float, lat: float, kind: str = "SIDEWALK") -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": {"TYPE": kind},
        "geometry": {"type": "LineString", "coordinates": [[lon, lat], [lon + 0.0005, lat]]},
    }


INSIDE = (-77.28, 38.85)
OUTSIDE = (-77.10, 38.85)


class FakeResponse:
    def __init__(self, features: list[dict[str, Any]]) -> None:
        self._features = features

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"features": self._features}


class FakeLayer:
    def __init__(self, features: list[dict[str, Any]]) -> None:
        self.features = features
        self.offsets: list[int] = []

    def get(self, url: str, params: dict[str, Any], timeout: float) -> FakeResponse:
        start = params["resultOffset"]
        self.offsets.append(start)
        return FakeResponse(self.features[start : start + params["resultRecordCount"]])


# ---- download

def test_features_to_gdf_keeps_only_features_touching_the_area() -> None:
    gdf = features_to_gdf([feat(*INSIDE), feat(*OUTSIDE)], AREA)
    assert len(gdf) == 1 and list(gdf.columns) == ["TYPE", "geometry"]


def test_features_to_gdf_handles_an_empty_page() -> None:
    assert len(features_to_gdf([], AREA)) == 0


def test_download_pages_and_clips(tmp_path) -> None:
    layer = FakeLayer([feat(*INSIDE), feat(*OUTSIDE), feat(*INSIDE, "CONNECTOR"), feat(*INSIDE)])
    result = download_county_sidewalks(AREA, tmp_path, page_size=2, get=layer.get, sleep=lambda s: None)
    assert layer.offsets == [0, 2, 4]  # exact multiple of the page size ends on an empty page
    assert sorted(result["TYPE"]) == ["CONNECTOR", "SIDEWALK", "SIDEWALK"]


def test_download_resumes_from_saved_pages(tmp_path) -> None:
    layer = FakeLayer([feat(*INSIDE), feat(*INSIDE), feat(*INSIDE)])
    download_county_sidewalks(AREA, tmp_path, page_size=2, get=layer.get, sleep=lambda s: None)
    first_run = list(layer.offsets)
    assert first_run == [0, 2]

    # Simulate an interrupted run: delete the last part, then run again.
    (tmp_path / "page_00000002.parquet").unlink()
    layer.offsets.clear()
    result = download_county_sidewalks(AREA, tmp_path, page_size=2, get=layer.get, sleep=lambda s: None)
    assert layer.offsets == [2]  # page 0 was not downloaded again
    assert len(result) == 3


def test_split_county_separates_sidewalks_and_connectors() -> None:
    county = features_to_gdf([feat(*INSIDE), feat(*INSIDE, "CONNECTOR"), feat(*INSIDE, "CONNECTOR")], AREA)
    sidewalks, crosswalks, counts = split_county(county)
    assert len(sidewalks) == 1 and len(crosswalks) == 2
    assert counts == {"CONNECTOR": 2, "SIDEWALK": 1}


def test_combine_adds_a_source_column() -> None:
    a = features_to_gdf([feat(*INSIDE)], AREA)
    b = gpd.GeoDataFrame({"highway": ["footway"]}, geometry=[LineString([(-77.28, 38.85), (-77.279, 38.85)])], crs="EPSG:4326")
    both = combine_sidewalks(a, b)
    assert both["source"].tolist() == ["county", "osm"]
    assert both.crs.to_epsg() == 4326


# ---- coverage

def lines(*segments: tuple[tuple[float, float], tuple[float, float]]) -> gpd.GeoSeries:
    return gpd.GeoSeries([LineString(s) for s in segments], crs=config.CRS_METERS)


def test_length_by_cell_uses_the_midpoint_cell() -> None:
    # 600 m line from x=800 to x=1400: midpoint x=1100 -> cell ix=1
    result = length_by_cell(lines(((800, 100), (1400, 100))), cell_m=1000)
    assert result.to_dict() == {(1, 0): pytest.approx(600)}


def test_length_by_cell_sums_within_a_cell() -> None:
    result = length_by_cell(lines(((0, 0), (100, 0)), ((0, 10), (50, 10))), cell_m=1000)
    assert result.to_dict() == {(0, 0): pytest.approx(150)}


def test_length_by_cell_empty() -> None:
    assert len(length_by_cell(gpd.GeoSeries([], crs=config.CRS_METERS))) == 0


def test_coverage_table_flags_cells_where_the_county_layer_is_empty() -> None:
    # Cell (0,0): 3 km of road, plenty of county sidewalk -> fine.
    # Cell (1,0): 3 km of road, no county sidewalk (OSM has some) -> gap.
    # Cell (2,0): only 500 m of road -> too little road to judge.
    roads = lines(*[((0, y), (900, y)) for y in (100, 200, 300, 400)][:3],
                  *[((1000, y), (1900, y)) for y in (100, 200, 300, 400)][:3],
                  ((2000, 100), (2500, 100)))
    county = lines(*[((0, y), (900, y)) for y in (110, 210, 310)])
    osm = lines(((1000, 110), (1500, 110)))
    table = coverage_table(county, osm, roads, cell_m=1000, min_road_m=2000, max_ratio=0.05)
    by_cell = table.set_index(["ix", "iy"])
    assert not by_cell.loc[(0, 0), "gap"]
    assert by_cell.loc[(1, 0), "gap"]
    assert by_cell.loc[(1, 0), "osm_m"] == pytest.approx(500)
    assert not by_cell.loc[(2, 0), "gap"]


def test_cells_gdf_makes_square_polygons() -> None:
    table = pd.DataFrame({"ix": [2], "iy": [-1], "gap": [True]})
    cell = cells_gdf(table, cell_m=1000).geometry.iloc[0]
    assert cell.bounds == (2000, -1000, 3000, 0)
