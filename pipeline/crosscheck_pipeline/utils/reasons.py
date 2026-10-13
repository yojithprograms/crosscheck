"""Text helpers for road names and segment reasons."""
from collections.abc import Mapping
from dataclasses import dataclass

from crosscheck_pipeline import config


def display_road_name(name: str | None, highway: str | None) -> str:
    """The road's name if it has one, otherwise a plain-English stand-in.

    Anything that shows a road name to a student goes through this (DESIGN §6 Step 1.5).
    """
    if name and name.strip():
        return name.strip()
    if highway == "service":
        return "a driveway or parking lot aisle"
    return "an unnamed street"


# ---------------------------------------------------------------------------
# Segment reasons (Step 1.8, DESIGN Appendix A)
# ---------------------------------------------------------------------------
# Each "explainable" reason is tied to the model feature(s) whose pushes it summarizes. A reason is
# only shown when those features really raise this segment's risk (their summed contribution > 0).
REASON_FEATURES: dict[str, tuple[str, ...]] = {
    "speed": ("speed_mph",),
    "lanes": ("lanes",),
    "no_sidewalk": ("sidewalk_cov", "no_sidewalk_fast"),
    "major_road": ("class_trunk", "class_primary"),
}

# "Ask about" lines for the school report (Appendix A), keyed by reason kind.
ASK_ABOUT: dict[str, str] = {
    "speed": "Could speeds here be lowered or better enforced?",
    "lanes": "Could this crossing get a signal, flashing beacon, median refuge, or crossing guard?",
    "no_sidewalk": "Is a sidewalk or trail planned here?",
    "no_signal": "Could this crossing get a signal or beacon?",
}


@dataclass(frozen=True)
class Reason:
    kind: str       # "crashes", "speed", "lanes", "no_sidewalk", "major_road"
    text: str


def crash_history_text(crashes_recent: int, crashes_recent_ka: int) -> str:
    noun = "crash" if crashes_recent == 1 else "crashes"
    text = f"{crashes_recent} {noun} involving someone walking or biking here since {config.MAP_CRASHES_FROM}"
    if crashes_recent_ka >= 1:
        text += f", {crashes_recent_ka} with serious or fatal injuries"
    return text


# Context reasons: a fallback for medium/high-risk segments that have no Appendix A reason. They
# describe features the model really does use (Step 1.7 coefficients), in plain, factual words.
CONTEXT_FEATURES: dict[str, tuple[str, ...]] = {
    "road_type": ("class_secondary", "class_tertiary"),
    "bus_stops": ("bus_stops_200m",),
    "crossings": ("marked_crossings",),
    "foot_traffic": ("sidewalk_cov",),
    "long_stretch": ("log_length",),
}
GENERIC_CONTEXT_TEXT = {
    "high": "Ranks high among nearby streets overall, based on road type and surroundings",
    "medium": "Ranks above most nearby streets overall, based on road type and surroundings",
}


def context_reason_items(row: Mapping, contribs: Mapping[str, float], risk_class: str) -> list[Reason]:
    """Plain-words reasons for a medium/high segment that has none from Appendix A.

    Same rule as the other reasons: the condition must be true and the model features behind it must
    push risk up. If nothing qualifies, one generic sentence is used, so a colored street always
    has a "why".
    """
    candidates = [
        ("road_type", row["highway"] in ("secondary", "tertiary"), "A busier through street, not a quiet neighborhood road"),
        ("bus_stops", row["bus_stops_200m"] >= 1, "Bus stops nearby"),
        ("crossings", row["marked_crossings"] >= config.FALLBACK_MIN_CROSSINGS, "Many crosswalks nearby"),
        ("foot_traffic", row["sidewalk_cov"] >= config.FALLBACK_BUSY_SIDEWALK_COV,
         "Sidewalks here likely mean more people on foot"),
        ("long_stretch", row["length_m"] >= config.FALLBACK_LONG_SEGMENT_M, "A long stretch of road"),
    ]
    scored = []
    for kind, condition, text in candidates:
        push = sum(contribs[f] for f in CONTEXT_FEATURES[kind])
        if condition and push > 0:
            scored.append((push, Reason(kind, text)))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    items = [reason for _, reason in scored][: config.MAX_CONTEXT_REASONS]
    return items or [Reason("generic", GENERIC_CONTEXT_TEXT[risk_class])]


def segment_reason_items(row: Mapping, contribs: Mapping[str, float], risk_class: str | None = None) -> list[Reason]:
    """Up to MAX_REASONS reasons for one segment.

    - If the segment had a crash since MAP_CRASHES_FROM, the crash-history sentence always comes first.
    - Every other reason needs (a) its Appendix A condition to be true and (b) a positive
      contribution from its model features. They are ordered by contribution, largest first.
    - If there are none and `risk_class` is "medium" or "high", plain-words context reasons are used
      instead (see context_reason_items), so a colored street is never left without a "why".
    """
    items: list[Reason] = []
    if row["crashes_recent"] >= 1:
        items.append(Reason("crashes", crash_history_text(int(row["crashes_recent"]), int(row["crashes_recent_ka"]))))

    speed = int(row["speed_mph"])
    speed_text = f"Speed limit ≈ {speed} mph (estimated)" if row["speed_imputed"] else f"Speed limit is {speed} mph"
    candidates = [
        ("speed", speed >= config.FAST_MPH, speed_text),
        ("lanes", row["lanes"] >= config.WIDE_ROAD_LANES, f"{int(row['lanes'])} lanes of traffic"),
        ("no_sidewalk", row["sidewalk_cov"] < config.NO_SIDEWALK_COV and row["sidewalk_known"] == 1,
         "No sidewalk along most of this stretch"),
        ("major_road", row["highway"] in config.MAJOR_ROAD_CLASSES, "Major road with heavy traffic"),
    ]
    scored = []
    for kind, condition, text in candidates:
        push = sum(contribs[f] for f in REASON_FEATURES[kind])
        if condition and push > 0:
            scored.append((push, Reason(kind, text)))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    items.extend(reason for _, reason in scored)
    if not items and risk_class in ("medium", "high"):
        items = context_reason_items(row, contribs, risk_class)
    return items[: config.MAX_REASONS]
