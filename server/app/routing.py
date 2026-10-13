"""★ Step 2.3 — Routing: the fastest route and the lower-risk route (DESIGN.md §7.6).

The idea in plain words: risky streets count as longer than they really are. A street riskier than
90% of streets counts as almost 3 times its length, crossing it adds about 250 m, and each recent
student report adds 150 m. The app then finds the shortest path using those "effective meters".
The fastest route ignores risk and uses real length only.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

import networkx as nx

from app import config, hazards
from app.errors import ApiError
from app.geo import flat_distance_m, nearest_index
from app.graph_io import SchoolGraph, edge_polyline
from app.schemas import Route, RouteComparison

if TYPE_CHECKING:
    from app.store import DataStore, SchoolData

LONG_DETOUR_NOTE = "It's a lot longer, so talk with your family about which makes sense."


# ---------------------------------------------------------------- the risk curve and edge costs

def risk_curve(risk_pct: float) -> float:
    """g(r) = max(0, (r - 50) / 50)².

    0 at or below the median street, 0.16 at the 70th percentile, 0.64 at the 90th, 1.0 at the 100th.
    So below-average streets cost nothing extra, and the riskiest streets cost a lot.
    """
    return max(0.0, (risk_pct - 50) / 50) ** 2


def edge_cost_low(graph: nx.DiGraph, u: int, v: int) -> float:
    """The lower-risk cost of walking the directed edge u -> v, in "effective meters"."""
    edge = graph[u][v]
    g = risk_curve(edge["risk_pct"])
    cost = edge["length"] * (1 + config.ALPHA * g)
    if edge["is_crossing"]:
        cost += config.BETA_CROSSING_M * g
    # Entering a risky intersection from a different road than the risky one.
    node = graph.nodes[v]
    if node["node_risk"] >= config.MEDIUM_PCT and edge["seg_id"] != node["major_seg"]:
        cost += config.GAMMA_INTERSECTION_M * risk_curve(node["node_risk"])
    cost += config.REPORT_PENALTY_M * min(edge["report_count"], config.REPORT_MAX_COUNT)
    return cost


def compute_costs(graph: nx.DiGraph) -> None:
    """Set `cost_low` on every directed edge. Run at startup, so weights can be tuned without
    rerunning the pipeline."""
    for u, v in graph.edges:
        graph[u][v]["cost_low"] = edge_cost_low(graph, u, v)


def add_report(graph: nx.DiGraph, u: int, v: int, delta: int = 1) -> None:
    """Add (or remove, with a negative delta) a confirmed student report on the edge, in both directions."""
    for a, b in ((u, v), (v, u)):
        edge = graph[a][b]
        edge["report_count"] = max(0, edge["report_count"] + delta)
        edge["cost_low"] = edge_cost_low(graph, a, b)


# ---------------------------------------------------------------- building a route

def snap_to_node(sg: SchoolGraph, lon: float, lat: float) -> int:
    """The walking-graph node nearest the point, or NO_NEARBY_PATH if none is close enough."""
    position, distance = nearest_index(sg.node_lons, sg.node_lats, lon, lat)
    if distance > config.SNAP_MAX_M:
        raise ApiError(422, "NO_NEARBY_PATH", "We couldn't find a sidewalk or street near there. Try moving the pin.")
    return int(sg.node_ids[position])


def route_view(graph: nx.DiGraph, mode: str) -> nx.DiGraph:
    """Walking can use every edge. Bikes and scooters can't use steps."""
    if mode == "walk":
        return graph
    return nx.subgraph_view(graph, filter_edge=lambda u, v: not graph[u][v]["is_steps"])


def route_polyline(graph: nx.DiGraph, path: list[int]) -> list[list[float]]:
    """[lon, lat] points along the path. Each edge's points are read in the direction of travel, and
    the repeated joint point between edges is skipped."""
    points: list[list[float]] = []
    for a, b in zip(path, path[1:]):
        edge_points = edge_polyline(graph, a, b)
        points.extend(edge_points if not points else edge_points[1:])
    if not points:  # origin and entrance are the same node
        node = graph.nodes[path[0]]
        points = [[node["lon"], node["lat"]]]
    return points


def build_route(school: SchoolData, path: list[int], mode: str) -> Route:
    graph = school.graph.graph
    edges = [graph[a][b] for a, b in zip(path, path[1:])]
    distance = sum(e["length"] for e in edges)
    speed = config.WALK_SPEED_MPS if mode == "walk" else config.BIKE_SPEED_MPS
    mean_risk = sum(e["length"] * e["risk_pct"] for e in edges) / distance if distance > 0 else 0.0
    analysis = hazards.analyze_route(school, path, mode)
    return Route(
        distance_m=round(distance),
        duration_min=math.ceil(distance / speed / 60),
        polyline=route_polyline(graph, path),
        high_count=analysis.high_count,
        medium_count=analysis.medium_count,
        report_spot_count=analysis.report_spot_count,
        mean_risk_pct=round(mean_risk, 1),
        hazards=analysis.hazards,
    )


def route_notes(same_route: bool, fastest: Route, lower_risk: Route) -> list[str]:
    """The short sentences shown under the two route cards.

    The second half of each sentence only claims what is true of this pair of routes: fewer high-risk
    spots, or a lower average risk, or fewer student-reported spots; otherwise it says the risk is similar.
    """
    if same_route:
        return ["Your fastest route is also the lower-risk route."]
    extra_minutes = lower_risk.duration_min - fastest.duration_min
    added = f"{extra_minutes} min" if extra_minutes > 0 else "less than a minute"
    avoided = fastest.high_count - lower_risk.high_count
    reports_avoided = fastest.report_spot_count - lower_risk.report_spot_count
    if avoided > 0:
        spots = "spot" if avoided == 1 else "spots"
        notes = [f"The lower-risk route adds {added} and avoids {avoided} high-risk {spots}."]
    elif lower_risk.mean_risk_pct < fastest.mean_risk_pct:
        notes = [f"The lower-risk route adds {added} and spends less of the trip on risky streets."]
    elif reports_avoided > 0:
        spots = "spot" if reports_avoided == 1 else "spots"
        notes = [f"The lower-risk route adds {added} and avoids {reports_avoided} {spots} students reported."]
    else:
        notes = [f"The lower-risk route adds {added} and has about the same level of risk."]
    if lower_risk.distance_m > config.LONG_DETOUR_RATIO * fastest.distance_m:
        notes.append(LONG_DETOUR_NOTE)
    return notes


def compare_routes(store: DataStore, school_id: str, origin_lat: float, origin_lon: float, mode: str) -> RouteComparison:
    """The fastest and the lower-risk route from a start point to the school entrance.

    The origin is used to find a path and then forgotten: it is never stored or logged.
    """
    school = store.schools.get(school_id)
    if school is None:
        raise ApiError(404, "UNKNOWN_SCHOOL", "This school's map isn't ready yet.")
    info = school.info
    if flat_distance_m(origin_lon, origin_lat, info["lon"], info["lat"]) > info["radius_m"] * config.AREA_SLACK:
        raise ApiError(422, "OUTSIDE_AREA", f"That's outside the area CrossCheck covers for {info['name']}.")

    sg = school.graph
    start = snap_to_node(sg, origin_lon, origin_lat)
    view = route_view(sg.graph, mode)
    try:
        fastest_path = nx.shortest_path(view, start, sg.entrance_node, weight="length")
        lower_path = nx.shortest_path(view, start, sg.entrance_node, weight="cost_low")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        raise ApiError(422, "NO_ROUTE", "We couldn't find a route from there. Try a different start.") from None

    same_route = fastest_path == lower_path
    fastest = build_route(school, fastest_path, mode)
    lower_risk = fastest if same_route else build_route(school, lower_path, mode)
    return RouteComparison(
        school_id=school_id, mode=mode, same_route=same_route, fastest=fastest, lower_risk=lower_risk,
        notes=route_notes(same_route, fastest, lower_risk),
    )
