"""★ Step 2.4 — Hazards: find, group, title, and explain the dangerous spots on a route (DESIGN.md §7.7).

A "hazard" is a place along the route worth a student's attention:
- walking along or across a high-risk street, or along a street with recent student reports;
- entering an intersection with a high-risk road (you cross or join that road there).
Nearby hazards are merged so a long stretch beside one busy road is one numbered spot, not ten.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from app import config
from app.graph_io import edge_polyline
from app.hazard_types import SHORT_LABEL
from app.names import display_road_name
from app.schemas import Hazard

if TYPE_CHECKING:
    from app.store import SchoolData

NO_SIGNAL_REASON = "No traffic signal where you cross"
REPORTS_WINDOW_MONTHS = round(config.REPORT_WINDOW_DAYS / 30)
# If two hazards in a group are equally risky, the more specific one names the group.
KIND_RANK = {"crossing": 3, "intersection": 2, "along": 1, "reported": 0}


@dataclass
class RouteAnalysis:
    hazards: list[Hazard] = field(default_factory=list)
    high_count: int = 0
    medium_count: int = 0
    report_spot_count: int = 0


@dataclass
class _Candidate:
    """One hazard before grouping: an edge, or an intersection node, at a distance along the route."""

    kind: str
    start_m: float
    end_m: float
    risk_pct: float
    risk_class: str
    seg_id: str | None
    road_name: str
    report_count: int
    report_types: Counter


# ---------------------------------------------------------------- step 1: find candidates

def find_candidates(school: SchoolData, path: list[int]) -> list[_Candidate]:
    """Walk the path edge by edge (u -> v) and note every edge hazard and intersection hazard, in order."""
    graph = school.graph.graph
    found: list[_Candidate] = []
    travelled = 0.0
    for u, v in zip(path, path[1:]):
        edge = graph[u][v]
        start, end = travelled, travelled + edge["length"]
        travelled = end

        is_reported = edge["report_count"] > 0
        if edge["risk_class"] == "high" or is_reported:
            if edge["is_crossing"]:
                kind = "crossing"
            elif edge["risk_class"] != "high":
                kind = "reported"        # only the reports make this a hazard
            else:
                kind = "along"
            found.append(_Candidate(
                kind, start, end, edge["risk_pct"], edge["risk_class"], edge["seg_id"], edge["road_name"],
                edge["report_count"], Counter(edge.get("report_types", {})),
            ))

        # Entering (or crossing) a high-risk road at v: only when this edge is NOT that road.
        node = graph.nodes[v]
        if node["node_risk"] >= config.HIGH_PCT and edge["seg_id"] != node["major_seg"]:
            major = school.segments.get(node["major_seg"], {})
            found.append(_Candidate(
                "intersection", end, end, node["node_risk"], "high", node["major_seg"], major.get("name", ""),
                0, Counter(),
            ))
    return found


# ---------------------------------------------------------------- step 2: group nearby hazards

def group_candidates(candidates: list[_Candidate]) -> list[list[_Candidate]]:
    """Merge hazards that are within HAZARD_GROUP_M of each other along the path (in path order)."""
    groups: list[list[_Candidate]] = []
    group_end = -math.inf
    for candidate in candidates:
        if groups and candidate.start_m - group_end <= config.HAZARD_GROUP_M:
            groups[-1].append(candidate)
            group_end = max(group_end, candidate.end_m)
        else:
            groups.append([candidate])
            group_end = candidate.end_m
    return groups


def representative(group: list[_Candidate]) -> _Candidate:
    """The member that names the group: the riskiest (ties: crossing > intersection > along > reported)."""
    return max(group, key=lambda c: (c.risk_pct, KIND_RANK[c.kind]))


# ---------------------------------------------------------------- step 3: titles, reasons, position

def road_label(school: SchoolData, seg_id: str | None, road_name: str) -> str | None:
    """A student-friendly road name, or None if the hazard isn't linked to any road."""
    if seg_id is None:
        return None
    return display_road_name(road_name, school.segments.get(seg_id, {}).get("highway"))


def hazard_title(kind: str, road: str | None, mode: str) -> str:
    if kind == "crossing":
        return f"Crossing {road}"
    if kind == "intersection":
        return f"Intersection with {road}"
    if kind == "along":
        return f"{'Walking' if mode == 'walk' else 'Riding'} along {road}"
    return f"Students reported a problem on {road}" if road else "Students reported a problem here"


def report_sentence(count: int, types: Counter) -> str:
    plural = "report" if count == 1 else "reports"
    text = f"{count} student {plural} here in the last {REPORTS_WINDOW_MONTHS} months"
    if types:
        top_type = types.most_common(1)[0][0]
        text += f", mostly: {SHORT_LABEL.get(top_type, SHORT_LABEL['other']).lower()}"
    return text


def hazard_reasons(school: SchoolData, rep: _Candidate, report_count: int, report_types: Counter) -> list[str]:
    """The segment's stored reasons, with the no-signal reason first for crossings and intersections
    on wide roads, and the student-report sentence last."""
    segment = school.segments.get(rep.seg_id, {}) if rep.seg_id else {}
    reasons = list(segment.get("reasons", []))
    if (rep.kind in ("crossing", "intersection") and segment.get("lanes", 0) >= config.WIDE_ROAD_LANES
            and segment.get("signal_end", 1) == 0):
        reasons.insert(0, NO_SIGNAL_REASON)
    if report_count > 0:
        reasons.append(report_sentence(report_count, report_types))
    return reasons


def point_along_route(school: SchoolData, path: list[int], distance_m: float) -> tuple[float, float]:
    """(lon, lat) of the point `distance_m` along the route, following each edge's real shape."""
    graph = school.graph.graph
    travelled = 0.0
    for u, v in zip(path, path[1:]):
        length = graph[u][v]["length"]
        if distance_m <= travelled + length or (u, v) == (path[-2], path[-1]):
            fraction = 0.0 if length == 0 else min(1.0, max(0.0, (distance_m - travelled) / length))
            return _point_at_fraction(edge_polyline(graph, u, v), fraction)
        travelled += length
    node = graph.nodes[path[0]]
    return node["lon"], node["lat"]


def _point_at_fraction(coords: list[list[float]], fraction: float) -> tuple[float, float]:
    """The point a fraction of the way along a polyline (measured by distance along its segments)."""
    steps = [math.dist(a, b) for a, b in zip(coords, coords[1:])]
    total = sum(steps)
    if total == 0:
        return coords[0][0], coords[0][1]
    target = fraction * total
    for (a, b), step in zip(zip(coords, coords[1:]), steps):
        if target <= step and step > 0:
            t = target / step
            return a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
        target -= step
    return coords[-1][0], coords[-1][1]


# ---------------------------------------------------------------- the whole analysis

def analyze_route(school: SchoolData, path: list[int], mode: str) -> RouteAnalysis:
    """Hazards (numbered in path order) and the counts shown on the route cards."""
    graph = school.graph.graph
    groups = group_candidates(find_candidates(school, path))

    hazards: list[Hazard] = []
    for number, group in enumerate(groups, start=1):
        rep = representative(group)
        report_count = sum(c.report_count for c in group)
        report_types: Counter = Counter()
        for c in group:
            report_types.update(c.report_types)
        lon, lat = point_along_route(school, path, (min(c.start_m for c in group) + max(c.end_m for c in group)) / 2)
        hazards.append(Hazard(
            n=number, kind=rep.kind, title=hazard_title(rep.kind, road_label(school, rep.seg_id, rep.road_name), mode),
            lon=round(lon, 6), lat=round(lat, 6), risk_pct=rep.risk_pct, risk_class=rep.risk_class,
            reasons=hazard_reasons(school, rep, report_count, report_types),
            report_count=report_count, report_types=[t for t, _ in report_types.most_common()],
            seg_id=rep.seg_id,
        ))

    medium_segments = {
        graph[u][v]["seg_id"] for u, v in zip(path, path[1:])
        if graph[u][v]["risk_class"] == "medium" and graph[u][v]["seg_id"] is not None
    }
    return RouteAnalysis(
        hazards=hazards,
        high_count=sum(h.risk_class == "high" for h in hazards),
        medium_count=len(medium_segments),
        report_spot_count=sum(h.report_count > 0 for h in hazards),
    )
