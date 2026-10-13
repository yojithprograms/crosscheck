"""Step 1.1 — Pilot schools.

Downloads the FCPS reference list (D4) and checks the hand-made data/schools_pilot.csv against it.
Run: python -m crosscheck_pipeline.s01_schools
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from crosscheck_pipeline import config

PIPELINE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = PIPELINE_DIR / "data" / "raw"
PILOT_CSV = PIPELINE_DIR / "data" / "schools_pilot.csv"
REFERENCE_GEOJSON = RAW_DIR / "fcps_schools.geojson"
PLOT_PNG = PIPELINE_DIR / "data" / "interim" / "schools_check.png"

PILOT_COLUMNS = ["school_id", "name", "level", "entrance_lat", "entrance_lon", "radius_m"]
SCHOOL_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def download_reference() -> Path:
    """Query D4 for every facility (one request: the layer is well under maxRecordCount)."""
    params = {"where": "1=1", "outFields": "*", "outSR": 4326, "f": "geojson"}
    last_error: Exception | None = None
    for attempt in range(config.HTTP_RETRIES):
        try:
            resp = requests.get(
                f"{config.FCPS_SCHOOLS_URL}/query", params=params, timeout=config.HTTP_TIMEOUT_S
            )
            resp.raise_for_status()
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            REFERENCE_GEOJSON.write_bytes(resp.content)
            return REFERENCE_GEOJSON
        except requests.RequestException as exc:  # retry a few times, then give up
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not download the FCPS schools layer: {last_error}")


def load_pilot(path: Path = PILOT_CSV) -> pd.DataFrame:
    """Load schools_pilot.csv, fill blank radius_m from DEFAULT_RADIUS_M, and validate it."""
    df = pd.read_csv(path, dtype={"school_id": str, "name": str, "level": str})
    problems = validate_pilot(df)
    if problems:
        raise ValueError("schools_pilot.csv has problems:\n- " + "\n- ".join(problems))
    df["radius_m"] = df.apply(
        lambda r: config.DEFAULT_RADIUS_M[r["level"]] if pd.isna(r["radius_m"]) else r["radius_m"],
        axis=1,
    ).astype(int)
    return df


def validate_pilot(df: pd.DataFrame) -> list[str]:
    """Return a list of human-readable problems (empty list = the file is fine)."""
    problems: list[str] = []
    missing_cols = [c for c in PILOT_COLUMNS if c not in df.columns]
    if missing_cols:
        return [f"missing columns: {missing_cols}"]
    if df.empty:
        return ["no schools listed"]

    for i, row in df.iterrows():
        label = f"row {i + 2} ({row['school_id']})"
        if not isinstance(row["school_id"], str) or not SCHOOL_ID_RE.match(row["school_id"]):
            problems.append(f"{label}: school_id must be lowercase letters/numbers with hyphens")
        if row["level"] not in config.SCHOOL_LEVELS:
            problems.append(f"{label}: level must be one of {config.SCHOOL_LEVELS}")
        if pd.isna(row["entrance_lat"]) or pd.isna(row["entrance_lon"]):
            problems.append(f"{label}: entrance_lat/entrance_lon are required")
            continue
        lon_min, lat_min, lon_max, lat_max = config.CRASH_BBOX
        if not (lat_min <= row["entrance_lat"] <= lat_max and lon_min <= row["entrance_lon"] <= lon_max):
            problems.append(
                f"{label}: entrance is outside the study box {config.CRASH_BBOX} "
                "(are latitude and longitude swapped?)"
            )
        if not pd.isna(row["radius_m"]) and row["radius_m"] <= 0:
            problems.append(f"{label}: radius_m must be positive (or blank for the default)")

    dupes = df["school_id"][df["school_id"].duplicated()].tolist()
    if dupes:
        problems.append(f"duplicate school_id: {dupes}")
    return problems


def compare_to_reference(pilot: pd.DataFrame, reference: gpd.GeoDataFrame) -> pd.DataFrame:
    """For each pilot school, find the nearest FCPS-layer school of the same level (distance in meters).

    Only same-level schools are compared, so an alternative-program site at the same address
    can't be mistaken for the school.
    """
    pilot_gdf = gpd.GeoDataFrame(
        pilot.copy(),
        geometry=gpd.points_from_xy(pilot["entrance_lon"], pilot["entrance_lat"]),
        crs="EPSG:4326",
    ).to_crs(config.CRS_METERS)
    ref = reference.to_crs(config.CRS_METERS)[["SCHOOL_NAME", "TYPE_DESC", "geometry"]]

    parts = []
    for level, group in pilot_gdf.groupby("level"):
        same_level = ref[ref["TYPE_DESC"] == config.SCHOOL_LEVEL_TYPES[level]]
        joined = gpd.sjoin_nearest(group, same_level, how="left", distance_col="ref_dist_m")
        parts.append(joined[~joined.index.duplicated(keep="first")])
    joined = pd.concat(parts).sort_index()
    out = joined[["school_id", "name", "SCHOOL_NAME", "TYPE_DESC", "ref_dist_m"]].copy()
    out["check"] = out["ref_dist_m"] > config.SCHOOL_REF_MAX_DIST_M
    return out.reset_index(drop=True)


def plot_pilot(pilot: pd.DataFrame, reference: gpd.GeoDataFrame, path: Path = PLOT_PNG) -> Path:
    """Save a quick picture: all FCPS facilities in gray, pilot entrances as labeled stars."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 9))
    reference.plot(ax=ax, color="lightgray", markersize=8)
    ax.scatter(pilot["entrance_lon"], pilot["entrance_lat"], marker="*", s=220, color="teal", zorder=3)
    for _, r in pilot.iterrows():
        ax.annotate(r["school_id"], (r["entrance_lon"], r["entrance_lat"]),
                    textcoords="offset points", xytext=(6, 6), fontsize=9)
    pad = 0.03
    ax.set_xlim(pilot["entrance_lon"].min() - pad, pilot["entrance_lon"].max() + pad)
    ax.set_ylim(pilot["entrance_lat"].min() - pad, pilot["entrance_lat"].max() + pad)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_title("Pilot schools (teal stars) vs. all FCPS facilities (gray)")
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    ref_path = download_reference()
    reference = gpd.read_file(ref_path)
    print(f"Downloaded {len(reference)} FCPS facilities -> {ref_path}")

    pilot = load_pilot()
    print(f"Loaded {len(pilot)} pilot schools from {PILOT_CSV}\n")
    report = compare_to_reference(pilot, reference)
    print(report.to_string(index=False))
    flagged = report[report["check"]]
    if len(flagged):
        print(f"\nCheck these (entrance > {config.SCHOOL_REF_MAX_DIST_M} m from the FCPS point):")
        print(flagged[["school_id", "SCHOOL_NAME", "ref_dist_m"]].to_string(index=False))
    print(f"\nPlot saved to {plot_pilot(pilot, reference)}")


if __name__ == "__main__":
    main()
