"""Checks that everything in server/data/ exists, parses, agrees with itself, and is small enough.

Run: python -m crosscheck_pipeline.validate_exports
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path
from typing import Any

from crosscheck_pipeline import config

SERVER_DATA = Path(__file__).resolve().parents[2] / "server" / "data"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
META_KEYS = {"data_through", "windows", "metrics", "model_version", "generated_at"}
SCHOOL_KEYS = {"id", "name", "level", "lat", "lon", "radius_m", "bbox"}


def _load_json(path: Path, problems: list[str]) -> Any:
    if not path.exists():
        problems.append(f"missing file: {path.parent.name}/{path.name}")
        return None
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return json.load(f)
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        problems.append(f"{path.name} does not parse: {error}")
        return None


def validate(data_dir: Path = SERVER_DATA) -> list[str]:
    """Return a list of problems (an empty list means everything checks out)."""
    problems: list[str] = []
    schools = _load_json(data_dir / "schools.json", problems)
    meta = _load_json(data_dir / "meta.json", problems)
    if meta is not None and not META_KEYS <= set(meta):
        problems.append(f"meta.json is missing keys: {sorted(META_KEYS - set(meta))}")
    if not schools:
        return problems or ["schools.json is empty"]
    ids = [s.get("id") for s in schools]
    if len(set(ids)) != len(ids):
        problems.append("schools.json has duplicate ids")

    for school in schools:
        sid = school.get("id")
        missing_keys = SCHOOL_KEYS - set(school)
        if missing_keys:
            problems.append(f"{sid}: schools.json entry is missing {sorted(missing_keys)}")
        graph_path = data_dir / "graphs" / f"{sid}.json.gz"
        graph = _load_json(graph_path, problems)
        segments = _load_json(data_dir / "segments" / f"{sid}.json", problems)
        risk = _load_json(data_dir / "layers" / f"{sid}_risk.geojson", problems)
        crashes = _load_json(data_dir / "layers" / f"{sid}_crashes.geojson", problems)
        report = _load_json(data_dir / "reports" / f"{sid}.json", problems)

        png = data_dir / "reports" / f"{sid}_map.png"
        if not png.exists():
            problems.append(f"{sid}: missing reports/{sid}_map.png")
        elif png.read_bytes()[:8] != PNG_SIGNATURE:
            problems.append(f"{sid}: reports/{sid}_map.png is not a PNG")

        if graph_path.exists() and graph_path.stat().st_size > config.MAX_GRAPH_FILE_MB * 1e6:
            problems.append(f"{sid}: graph is bigger than {config.MAX_GRAPH_FILE_MB} MB")
        risk_path = data_dir / "layers" / f"{sid}_risk.geojson"
        if risk_path.exists() and risk_path.stat().st_size > config.MAX_RISK_LAYER_KB * 1000:
            problems.append(f"{sid}: risk layer is bigger than {config.MAX_RISK_LAYER_KB} KB")

        if graph is not None:
            if graph.get("school_id") != sid:
                problems.append(f"{sid}: graph school_id is {graph.get('school_id')!r}")
            node_ids = {n["id"] for n in graph["nodes"]}
            if graph["entrance_node"] not in node_ids:
                problems.append(f"{sid}: entrance_node is not in the graph")
            if any(e["u"] not in node_ids or e["v"] not in node_ids for e in graph["edges"]):
                problems.append(f"{sid}: an edge points to a node that isn't in the graph")
            if any(e["u"] >= e["v"] for e in graph["edges"]):
                problems.append(f"{sid}: an edge has u >= v")
            if segments is not None:
                unknown = {e["seg_id"] for e in graph["edges"] if e["seg_id"] is not None} - set(segments)
                if unknown:
                    problems.append(f"{sid}: {len(unknown)} graph segment ids are missing from segments/{sid}.json")
        if risk is not None and segments is not None:
            layer_ids = {i for f in risk["features"] for i in f["properties"]["seg_ids"]}
            if layer_ids - set(segments):
                problems.append(f"{sid}: risk layer has segment ids that are missing from segments/{sid}.json")
        if crashes is not None:
            leaked = {"doc_nbr", "date", "street"} & {k for f in crashes["features"] for k in f["properties"]}
            if leaked:
                problems.append(f"{sid}: crash layer exposes {sorted(leaked)}")
        if report is not None:
            if report.get("school_id") != sid:
                problems.append(f"{sid}: report school_id is {report.get('school_id')!r}")
            if segments is not None:
                missing = [s["seg_id"] for s in report["top_spots"] if s["seg_id"] not in segments]
                if missing:
                    problems.append(f"{sid}: top spots reference unknown segments {missing}")
    return problems


def main() -> None:
    problems = validate()
    if problems:
        print(f"Validation found {len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    print("Validation passed: every export exists, parses, agrees across files, and is under its size limit.")


if __name__ == "__main__":
    main()
