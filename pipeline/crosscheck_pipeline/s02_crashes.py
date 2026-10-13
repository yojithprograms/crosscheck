"""Step 1.2 — Pedestrian and bicycle crashes from VDOT (D1).

Run: python -m crosscheck_pipeline.s02_crashes
Output: data/interim/crashes.parquet (GeoParquet, EPSG:4326; Step 1.6 projects to meters).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

from crosscheck_pipeline import config
from crosscheck_pipeline.utils.arcgis import fetch_all_features

PIPELINE_DIR = Path(__file__).resolve().parents[1]
OUT_PARQUET = PIPELINE_DIR / "data" / "interim" / "crashes.parquet"
PLOT_PNG = PIPELINE_DIR / "data" / "interim" / "crashes_check.png"

OUTPUT_COLUMNS = [
    "doc_nbr", "year", "date", "severity", "mode", "ka", "ped_killed", "ped_injured",
    "light", "intersection_type", "school_zone", "street", "geometry",
]


def download_crashes() -> list[dict[str, Any]]:
    """Page through D1 for every pedestrian or bicycle crash inside CRASH_BBOX."""
    lon_min, lat_min, lon_max, lat_max = config.CRASH_BBOX
    params = {
        "where": config.CRASH_WHERE,
        "geometry": f"{lon_min},{lat_min},{lon_max},{lat_max}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": config.CRASH_OUT_FIELDS,
        "outSR": 4326,
        "f": "geojson",
    }
    return fetch_all_features(config.VDOT_CRASH_URL, params)


def clean_crashes(features: list[dict[str, Any]]) -> tuple[gpd.GeoDataFrame, dict[str, int]]:
    """Turn raw GeoJSON features into the tidy crash table. Also returns counts of what was dropped.

    Notes:
    - The geometry is used for location (LAT/LON can be empty even when the geometry exists).
    - Yes/no flags are strings: '1' yes, '0' no, '-' unknown.
    - A crash flagged as both pedestrian and bicycle is labeled "ped".
    """
    dropped = {"raw": len(features), "no_geometry": 0, "no_year": 0, "duplicate": 0}
    if not features:
        return gpd.GeoDataFrame(columns=OUTPUT_COLUMNS, geometry="geometry", crs="EPSG:4326"), dropped

    raw = gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    has_geom = raw.geometry.notna() & ~raw.geometry.is_empty
    dropped["no_geometry"] = int((~has_geom).sum())
    raw = raw[has_geom]

    year = pd.to_numeric(raw["CRASH_YEAR"], errors="coerce")
    dropped["no_year"] = int(year.isna().sum())
    raw = raw[year.notna()]
    year = year[year.notna()].astype(int)

    out = gpd.GeoDataFrame(
        {
            "doc_nbr": raw["DOCUMENT_NBR"],
            "year": year,
            "date": pd.to_datetime(raw["CRASH_DT"], unit="ms", utc=True),
            "severity": raw["CRASH_SEVERITY"],
            "mode": raw["PED_NONPED"].eq("1").map({True: "ped", False: "bike"}),
            "ka": raw["CRASH_SEVERITY"].isin(config.KA_SEVERITIES),
            "ped_killed": pd.to_numeric(raw["PEDESTRIANS_KILLED"], errors="coerce").fillna(0).astype(int),
            "ped_injured": pd.to_numeric(raw["PEDESTRIANS_INJURED"], errors="coerce").fillna(0).astype(int),
            "light": raw["LIGHT_CONDITION"],
            "intersection_type": raw["INTERSECTION_TYPE"],
            "school_zone": raw["SCHOOL_ZONE"],
            "street": raw["ROUTE_OR_STREET_NM"],
        },
        geometry=raw.geometry,
        crs="EPSG:4326",
    )

    before = len(out)
    out = out.drop_duplicates(subset="doc_nbr", keep="first")
    dropped["duplicate"] = before - len(out)
    return out[OUTPUT_COLUMNS].reset_index(drop=True), dropped


def crashes_by_year_and_mode(crashes: gpd.GeoDataFrame) -> pd.DataFrame:
    return crashes.pivot_table(index="year", columns="mode", values="doc_nbr", aggfunc="count", fill_value=0)


def plot_crashes(crashes: gpd.GeoDataFrame, path: Path = PLOT_PNG) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 9))
    crashes[crashes["mode"] == "ped"].plot(ax=ax, color="crimson", markersize=2, label="pedestrian")
    crashes[crashes["mode"] == "bike"].plot(ax=ax, color="royalblue", markersize=2, label="bicycle")
    ax.legend(markerscale=5)
    ax.set_title(f"Pedestrian and bicycle crashes, {crashes['year'].min()}–{crashes['year'].max()} (n={len(crashes)})")
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    features = download_crashes()
    crashes, dropped = clean_crashes(features)
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    crashes.to_parquet(OUT_PARQUET)

    print(f"Downloaded {dropped['raw']} crashes; dropped {dropped['no_geometry']} without geometry, "
          f"{dropped['no_year']} without a year, {dropped['duplicate']} duplicates.")
    print(f"Saved {len(crashes)} crashes -> {OUT_PARQUET}\n")
    print("Crashes by year and mode:")
    print(crashes_by_year_and_mode(crashes).to_string())
    print(f"\nSerious or fatal (K/A): {int(crashes['ka'].sum())}")
    print(f"Date range: {crashes['date'].min().date()} to {crashes['date'].max().date()}")
    print(f"Plot saved to {plot_crashes(crashes)}")


if __name__ == "__main__":
    main()
