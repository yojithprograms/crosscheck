"""Step 1.3 — OpenStreetMap roads, signals/crossings/bus stops, and mapped sidewalks (D2).

Run: python -m crosscheck_pipeline.s03_osm
Outputs (data/interim/): study_area.gpkg, drive.graphml, osm_points.gpkg, osm_sidewalks.gpkg.
The study area follows config.STUDY_AREA_MODE ("pilot" circles, or the whole "county").
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from crosscheck_pipeline import config
from crosscheck_pipeline.s01_schools import load_pilot
from crosscheck_pipeline.utils.osm_parse import configure_osmnx

INTERIM_DIR = Path(__file__).resolve().parents[1] / "data" / "interim"
STUDY_AREA_GPKG = INTERIM_DIR / "study_area.gpkg"
DRIVE_GRAPHML = INTERIM_DIR / "drive.graphml"
POINTS_GPKG = INTERIM_DIR / "osm_points.gpkg"
SIDEWALKS_GPKG = INTERIM_DIR / "osm_sidewalks.gpkg"
PLOT_PNG = INTERIM_DIR / "osm_check.png"


def _circles_m(pilot: pd.DataFrame, radii_m: list[float]) -> list[BaseGeometry]:
    """Circles (in meters) around each school entrance."""
    points = gpd.GeoSeries(
        gpd.points_from_xy(pilot["entrance_lon"], pilot["entrance_lat"]), crs="EPSG:4326"
    ).to_crs(config.CRS_METERS)
    return [pt.buffer(r) for pt, r in zip(points, radii_m)]


def build_study_area(pilot: pd.DataFrame, mode: str = config.STUDY_AREA_MODE) -> BaseGeometry:
    """Study-area polygon in lon/lat.

    Always includes a circle of (radius_m + SCHOOL_BUFFER_EXTRA_M) around every pilot school, so
    streets just over a border still get scores. "pilot" adds a larger circle around each school;
    "county" adds the OSM boundaries of STUDY_AREA_QUERIES.
    """
    school_zones = _circles_m(pilot, [r + config.SCHOOL_BUFFER_EXTRA_M for r in pilot["radius_m"]])
    if mode == "pilot":
        base = _circles_m(pilot, [config.PILOT_AREA_RADIUS_M] * len(pilot))
    elif mode == "county":
        boundary = ox.geocoder.geocode_to_gdf(config.STUDY_AREA_QUERIES)
        base = [boundary.to_crs(config.CRS_METERS).union_all()]
    else:
        raise ValueError(f"STUDY_AREA_MODE must be 'pilot' or 'county', not {mode!r}")
    area_m = unary_union([*base, *school_zones])
    return gpd.GeoSeries([area_m], crs=config.CRS_METERS).to_crs("EPSG:4326").iloc[0]


def keep_points(features: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only Point features, with the `highway` and `crossing` columns (added if missing)."""
    pts = features[features.geometry.geom_type == "Point"].reset_index(drop=True)
    for col in ("highway", "crossing"):
        if col not in pts.columns:
            pts[col] = None
    return pts[["highway", "crossing", "geometry"]]


def keep_lines(features: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only line features (mapped sidewalks), with a small, file-friendly set of columns."""
    lines = features[features.geometry.geom_type.isin(["LineString", "MultiLineString"])].reset_index(drop=True)
    for col in ("highway", "footway"):
        if col not in lines.columns:
            lines[col] = None
    return lines[["highway", "footway", "geometry"]]


def plot_osm(graph, area: BaseGeometry, pilot: pd.DataFrame, path: Path = PLOT_PNG) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    edges = ox.convert.graph_to_gdfs(graph, nodes=False)
    fig, ax = plt.subplots(figsize=(10, 10))
    edges.plot(ax=ax, linewidth=0.3, color="dimgray")
    gpd.GeoSeries([area], crs="EPSG:4326").boundary.plot(ax=ax, color="teal", linewidth=1)
    ax.scatter(pilot["entrance_lon"], pilot["entrance_lat"], marker="*", s=160, color="crimson", zorder=3)
    ax.set_title(f"Road network ({config.STUDY_AREA_MODE} study area): {len(edges)} edges")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    configure_osmnx()
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    pilot = load_pilot()
    area = build_study_area(pilot)
    area_gdf = gpd.GeoDataFrame({"mode": [config.STUDY_AREA_MODE]}, geometry=[area], crs="EPSG:4326")
    area_gdf.to_file(STUDY_AREA_GPKG, driver="GPKG")
    area_km2 = gpd.GeoSeries([area], crs="EPSG:4326").to_crs(config.CRS_METERS).area.iloc[0] / 1e6
    print(f"Study area ({config.STUDY_AREA_MODE}): {area_km2:.0f} km² -> {STUDY_AREA_GPKG}")

    print("Downloading the road network (this can take several minutes)...")
    graph = ox.graph.graph_from_polygon(
        area, network_type=config.OSM_NETWORK_TYPE, simplify=True, retain_all=True
    )
    ox.io.save_graphml(graph, DRIVE_GRAPHML)
    print(f"Road graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges -> {DRIVE_GRAPHML}")

    print("Downloading signals, crossings, and bus stops...")
    points = keep_points(ox.features.features_from_polygon(area, tags=config.OSM_POINT_TAGS))
    points.to_file(POINTS_GPKG, driver="GPKG")
    print(f"OSM points: {points['highway'].value_counts().to_dict()} -> {POINTS_GPKG}")

    print("Downloading mapped sidewalks...")
    sidewalks = keep_lines(ox.features.features_from_polygon(area, tags=config.OSM_SIDEWALK_TAGS))
    sidewalks.to_file(SIDEWALKS_GPKG, driver="GPKG")
    print(f"OSM sidewalks: {len(sidewalks)} lines -> {SIDEWALKS_GPKG}")

    print(f"Plot saved to {plot_osm(graph, area, pilot)}")


if __name__ == "__main__":
    main()
