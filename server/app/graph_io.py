"""Walking graph files (made by the pipeline's Step 1.10) -> networkx graphs for routing."""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np


@dataclass
class SchoolGraph:
    """One school's walking graph plus numpy arrays for fast "nearest node" lookups."""

    school_id: str
    entrance_node: int
    graph: nx.DiGraph            # every undirected edge is stored in both directions
    node_ids: np.ndarray
    node_lons: np.ndarray
    node_lats: np.ndarray
    undirected_edge_count: int


def build_graph(payload: dict[str, Any]) -> SchoolGraph:
    """Build the directed graph from the file's structure (DESIGN §6 Step 1.10).

    Each undirected edge in the file becomes two directed edges. They share one `coords` list (the
    reverse direction sets `reversed=True` instead of copying), so memory stays small.
    `report_count` starts at 0 and is raised when student reports are confirmed.
    """
    graph = nx.DiGraph()
    for node in payload["nodes"]:
        graph.add_node(node["id"], lon=node["lon"], lat=node["lat"],
                       node_risk=node["node_risk"], major_seg=node["major_seg"])
    for edge in payload["edges"]:
        attrs = {
            "length": edge["length"], "coords": edge["coords"], "seg_id": edge["seg_id"],
            "road_name": edge["road_name"], "risk_pct": edge["risk_pct"], "risk_class": edge["risk_class"],
            "is_crossing": edge["is_crossing"], "is_steps": edge["is_steps"], "report_count": 0,
        }
        graph.add_edge(edge["u"], edge["v"], reversed=False, **attrs)
        graph.add_edge(edge["v"], edge["u"], reversed=True, **attrs)
    nodes = payload["nodes"]
    return SchoolGraph(
        school_id=payload["school_id"],
        entrance_node=payload["entrance_node"],
        graph=graph,
        node_ids=np.array([n["id"] for n in nodes], dtype=np.int64),
        node_lons=np.array([n["lon"] for n in nodes], dtype=np.float64),
        node_lats=np.array([n["lat"] for n in nodes], dtype=np.float64),
        undirected_edge_count=len(payload["edges"]),
    )


def load_graph(path: Path) -> SchoolGraph:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return build_graph(json.load(f))


def edge_polyline(graph: nx.DiGraph, u: int, v: int) -> list[list[float]]:
    """The [lon, lat] points of the edge when walking from u to v (the stored list is read-only)."""
    data = graph[u][v]
    return data["coords"][::-1] if data["reversed"] else data["coords"]
