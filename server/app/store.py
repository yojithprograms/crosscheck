"""The in-memory data store: everything the pipeline exported, loaded once at startup."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.graph_io import SchoolGraph, load_graph
from app.routing import compute_costs

logger = logging.getLogger("crosscheck.store")


@dataclass
class SchoolData:
    info: dict[str, Any]                 # one entry of schools.json
    graph: SchoolGraph
    segments: dict[str, dict[str, Any]]  # seg_id -> street details
    risk_layer: dict[str, Any]           # GeoJSON
    crash_layer: dict[str, Any]          # GeoJSON
    report: dict[str, Any]               # top spots + stats (precomputed)
    map_png: Path                        # schematic map for the printed report


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class DataStore:
    """Schools, graphs, segments, layers, and report data, all held in memory."""

    def __init__(self, meta: dict[str, Any], schools: dict[str, SchoolData]) -> None:
        self.meta = meta
        self.schools = schools

    @classmethod
    def load(cls, data_dir: Path) -> "DataStore":
        """Read every file the pipeline wrote. Raises FileNotFoundError if schools.json is missing."""
        data_dir = Path(data_dir)
        schools_file = data_dir / "schools.json"
        if not schools_file.exists():
            raise FileNotFoundError(f"{schools_file} not found. Run the pipeline (python -m crosscheck_pipeline.run_all).")
        meta = _read_json(data_dir / "meta.json")
        schools: dict[str, SchoolData] = {}
        for info in _read_json(schools_file):
            sid = info["id"]
            graph = load_graph(data_dir / "graphs" / f"{sid}.json.gz")
            compute_costs(graph.graph)
            schools[sid] = SchoolData(
                info=info,
                graph=graph,
                segments=_read_json(data_dir / "segments" / f"{sid}.json"),
                risk_layer=_read_json(data_dir / "layers" / f"{sid}_risk.geojson"),
                crash_layer=_read_json(data_dir / "layers" / f"{sid}_crashes.geojson"),
                report=_read_json(data_dir / "reports" / f"{sid}.json"),
                map_png=data_dir / "reports" / f"{sid}_map.png",
            )
            logger.info("loaded %s: %d nodes, %d edges, %d segments",
                        sid, graph.graph.number_of_nodes(), graph.undirected_edge_count, len(schools[sid].segments))
        return cls(meta, schools)

    def school_list(self) -> list[dict[str, Any]]:
        return [s.info for s in self.schools.values()]
