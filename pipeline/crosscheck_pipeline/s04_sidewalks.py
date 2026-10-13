"""Step 1.4 — Sidewalks (county layer D3 + OSM) and the coverage check.

Run: python -m crosscheck_pipeline.s04_sidewalks
Outputs (data/interim/): sidewalks.gpkg (column `source` = county | osm), county_crosswalks.gpkg,
sidewalk_gaps.gpkg (1 km cells where the county layer looks empty), sidewalk_coverage.png.

The county layer is huge (about 500,000 features), so each downloaded page is clipped to the study
area and saved as a small parquet part in data/raw/county_sidewalks/. If the download is
interrupted, running again picks up where it stopped.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import osmnx as ox
import pandas as pd
import requests
import shapely
from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

from crosscheck_pipeline import config
from crosscheck_pipeline.utils.arcgis import fetch_page

PIPELINE_DIR = Path(__file__).resolve().parents[1]
RAW_PARTS_DIR = PIPELINE_DIR / "data" / "raw" / "county_sidewalks"
INTERIM_DIR = PIPELINE_DIR / "data" / "interim"
STUDY_AREA_GPKG = INTERIM_DIR / "study_area.gpkg"
DRIVE_GRAPHML = INTERIM_DIR / "drive.graphml"
OSM_SIDEWALKS_GPKG = INTERIM_DIR / "osm_sidewalks.gpkg"
SIDEWALKS_GPKG = INTERIM_DIR / "sidewalks.gpkg"
CROSSWALKS_GPKG = INTERIM_DIR / "county_crosswalks.gpkg"
GAPS_GPKG = INTERIM_DIR / "sidewalk_gaps.gpkg"
COVERAGE_CSV = INTERIM_DIR / "sidewalk_coverage.csv"
PLOT_PNG = INTERIM_DIR / "sidewalk_coverage.png"


# ---------------------------------------------------------------- download

def features_to_gdf(features: list[dict[str, Any]], area: BaseGeometry) -> gpd.GeoDataFrame:
    """One downloaded page -> a small table (TYPE + geometry) of the features that touch the study area."""
    if not features:
        return gpd.GeoDataFrame({"TYPE": []}, geometry=[], crs="EPSG:4326")
    gdf = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")
    gdf = gdf[gdf.geometry.notna()]
    shapely.prepare(area)
    keep = shapely.intersects(gdf.geometry.values, area)
    return gdf.loc[keep, ["TYPE", "geometry"]].reset_index(drop=True)


def download_county_sidewalks(
    area: BaseGeometry,
    parts_dir: Path = RAW_PARTS_DIR,
    *,
    page_size: int | None = None,
    get: Callable[..., requests.Response] = requests.get,
    sleep: Callable[[float], None] = time.sleep,
) -> gpd.GeoDataFrame:
    """Page through D3 for features inside the study area's bounding box; clip each page to the area.

    Only `TYPE` is requested (the other fields aren't used). Each page becomes one parquet part, so
    a rerun skips pages already saved.
    """
    minx, miny, maxx, maxy = area.bounds
    params = {
        "where": "1=1",
        "outFields": "TYPE",
        "outSR": 4326,
        "geometry": f"{minx},{miny},{maxx},{maxy}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "f": "geojson",
    }
    parts_dir.mkdir(parents=True, exist_ok=True)
    page_size = page_size or config.ARCGIS_PAGE_SIZE
    offset = 0
    while True:
        part = parts_dir / f"page_{offset:08d}.parquet"
        if part.exists():  # saved by an earlier run; assume it was a full page and move on
            offset += page_size
            continue
        features = fetch_page(
            config.COUNTY_SIDEWALKS_URL, params, offset, page_size=page_size, get=get, sleep=sleep
        )
        if not features:
            break
        features_to_gdf(features, area).to_parquet(part)
        if len(features) < page_size:
            break
        offset += page_size
        print(f"  ...{offset} features downloaded", flush=True)
        sleep(config.ARCGIS_PAUSE_S)

    parts = sorted(parts_dir.glob("page_*.parquet"))
    frames = [gpd.read_parquet(p) for p in parts]
    frames = [f for f in frames if len(f)]
    if not frames:
        return gpd.GeoDataFrame({"TYPE": []}, geometry=[], crs="EPSG:4326")
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")


def split_county(county: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict[str, int]]:
    """Split the county layer into sidewalks and crosswalk connectors. Returns the TYPE counts too."""
    counts = county["TYPE"].value_counts().to_dict()
    sidewalks = county[county["TYPE"].isin(config.COUNTY_SIDEWALK_TYPES)].reset_index(drop=True)
    crosswalks = county[county["TYPE"].isin(config.COUNTY_CROSSWALK_TYPES)].reset_index(drop=True)
    return sidewalks, crosswalks, counts


def combine_sidewalks(county_sidewalks: gpd.GeoDataFrame, osm_sidewalks: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Stack county and OSM sidewalks into one table with a `source` column."""
    parts = [
        gpd.GeoDataFrame({"source": "county"}, index=county_sidewalks.index, geometry=county_sidewalks.geometry),
        gpd.GeoDataFrame({"source": "osm"}, index=osm_sidewalks.index, geometry=osm_sidewalks.geometry),
    ]
    both = pd.concat([p.to_crs("EPSG:4326") for p in parts], ignore_index=True)
    return gpd.GeoDataFrame(both, geometry="geometry", crs="EPSG:4326")


# ---------------------------------------------------------------- coverage check

def length_by_cell(lines_m: gpd.GeoSeries, cell_m: float = config.COVERAGE_CELL_M) -> pd.Series:
    """Total line length (meters) per grid cell. Each line counts in the cell holding its midpoint.

    `lines_m` must be in a meters CRS. The result is indexed by (ix, iy) cell numbers.
    """
    if len(lines_m) == 0:
        return pd.Series(dtype=float, index=pd.MultiIndex.from_arrays([[], []], names=["ix", "iy"]))
    mids = shapely.line_interpolate_point(lines_m.values, 0.5, normalized=True)
    ix = np.floor(shapely.get_x(mids) / cell_m).astype(int)
    iy = np.floor(shapely.get_y(mids) / cell_m).astype(int)
    frame = pd.DataFrame({"ix": ix, "iy": iy, "length_m": lines_m.length.values})
    return frame.groupby(["ix", "iy"])["length_m"].sum()


def coverage_table(
    county_m: gpd.GeoSeries,
    osm_m: gpd.GeoSeries,
    roads_m: gpd.GeoSeries,
    *,
    cell_m: float = config.COVERAGE_CELL_M,
    min_road_m: float = config.GAP_MIN_ROAD_M,
    max_ratio: float = config.GAP_MAX_COUNTY_RATIO,
) -> pd.DataFrame:
    """Per-cell sidewalk lengths and a gap flag.

    A cell is a "gap" when it has at least `min_road_m` of road but the county layer has less than
    `max_ratio` meters of sidewalk per meter of road — the county layer probably doesn't cover it.
    """
    table = pd.concat(
        {
            "county_m": length_by_cell(county_m, cell_m),
            "osm_m": length_by_cell(osm_m, cell_m),
            "road_m": length_by_cell(roads_m, cell_m),
        },
        axis=1,
    ).fillna(0.0)
    table = table[table["road_m"] > 0].copy()
    table["county_ratio"] = table["county_m"] / table["road_m"]
    table["osm_ratio"] = table["osm_m"] / table["road_m"]
    table["gap"] = (table["road_m"] >= min_road_m) & (table["county_ratio"] < max_ratio)
    return table.reset_index()


def cells_gdf(table: pd.DataFrame, cell_m: float = config.COVERAGE_CELL_M) -> gpd.GeoDataFrame:
    """Square polygons (in CRS_METERS) for each row of a coverage table."""
    geoms = [box(r.ix * cell_m, r.iy * cell_m, (r.ix + 1) * cell_m, (r.iy + 1) * cell_m) for r in table.itertuples()]
    return gpd.GeoDataFrame(table.copy(), geometry=geoms, crs=config.CRS_METERS)


def load_road_lines_m() -> gpd.GeoSeries:
    """Road geometry (meters) for the coverage denominator: roads where sidewalks could exist.

    Freeways and service roads (parking aisles, driveways) are left out, so they don't make
    commercial areas look like they're missing sidewalks.
    """
    graph = ox.io.load_graphml(DRIVE_GRAPHML)
    edges = ox.convert.graph_to_gdfs(graph, nodes=False)
    del graph
    first = edges["highway"].map(lambda v: v[0] if isinstance(v, list) else v)
    roads = edges.loc[~first.isin(config.GAP_ROAD_EXCLUDE), "geometry"]
    return roads.to_crs(config.CRS_METERS).reset_index(drop=True)


def plot_coverage(cells: gpd.GeoDataFrame, pilot: pd.DataFrame, path: Path = PLOT_PNG) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    schools = gpd.GeoSeries(
        gpd.points_from_xy(pilot["entrance_lon"], pilot["entrance_lat"]), crs="EPSG:4326"
    ).to_crs(config.CRS_METERS)
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    panels = [
        ("county_m", "County sidewalks (km per 1 km cell)", 1000, "viridis"),
        ("osm_m", "OSM sidewalks (km per 1 km cell)", 1000, "viridis"),
        ("county_ratio", "County sidewalk / road length (red outline = gap)", 1, "viridis"),
    ]
    for ax, (col, title, scale, cmap) in zip(axes, panels):
        data = cells.assign(value=cells[col] / scale)
        data.plot(ax=ax, column="value", cmap=cmap, legend=True, legend_kwds={"shrink": 0.6})
        if col == "county_ratio":
            cells[cells["gap"]].boundary.plot(ax=ax, color="red", linewidth=1.2)
        schools.plot(ax=ax, marker="*", color="white", edgecolor="black", markersize=140, zorder=3)
        ax.set_title(title)
        ax.set_axis_off()
    fig.savefig(path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    from crosscheck_pipeline.s01_schools import load_pilot

    pilot = load_pilot()
    area = gpd.read_file(STUDY_AREA_GPKG).geometry.iloc[0]

    print("Downloading county sidewalks (a few minutes; safe to stop and rerun)...")
    county = download_county_sidewalks(area)
    county_sidewalks, crosswalks, counts = split_county(county)
    print(f"County features in the study area by TYPE: {counts}")

    osm = gpd.read_file(OSM_SIDEWALKS_GPKG)
    sidewalks = combine_sidewalks(county_sidewalks, osm)
    sidewalks.to_file(SIDEWALKS_GPKG, driver="GPKG")
    crosswalks.to_file(CROSSWALKS_GPKG, driver="GPKG")
    print(f"sidewalks.gpkg: {sidewalks['source'].value_counts().to_dict()} | "
          f"county_crosswalks.gpkg: {len(crosswalks)} connectors")

    print("Building the 1 km coverage grid...")
    table = coverage_table(
        county_sidewalks.to_crs(config.CRS_METERS).geometry,
        osm.to_crs(config.CRS_METERS).geometry,
        load_road_lines_m(),
    )
    table.to_csv(COVERAGE_CSV, index=False)
    cells = cells_gdf(table)
    gaps = cells[cells["gap"]]
    gaps.to_crs("EPSG:4326").to_file(GAPS_GPKG, driver="GPKG")
    print(f"{len(cells)} cells with roads; {len(gaps)} flagged as county-sidewalk gaps -> {GAPS_GPKG}")
    if len(gaps):
        centers = gaps.geometry.centroid.to_crs("EPSG:4326")
        show = gaps.assign(lat=centers.y.round(3).values, lon=centers.x.round(3).values)
        print(show.sort_values("road_m", ascending=False)[
            ["lat", "lon", "road_m", "county_m", "osm_m", "county_ratio"]].head(15).round(2).to_string(index=False))
    print(f"Plot saved to {plot_coverage(cells, pilot)}")


if __name__ == "__main__":
    main()
