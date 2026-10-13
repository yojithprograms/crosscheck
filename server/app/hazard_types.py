"""Near-miss hazard types, their labels, and who can fix them (DESIGN.md Appendix B)."""
from enum import Enum


class HazardType(str, Enum):
    driver_failed_to_yield = "driver_failed_to_yield"
    turning_vehicle = "turning_vehicle"
    speeding = "speeding"
    no_sidewalk = "no_sidewalk"
    blocked_sidewalk = "blocked_sidewalk"
    hard_to_cross = "hard_to_cross"
    poor_visibility = "poor_visibility"
    drop_off_congestion = "drop_off_congestion"
    bike_conflict = "bike_conflict"
    other = "other"


# What the student sees when picking a type (the app keeps its own copy in strings.ts).
APP_LABEL: dict[str, str] = {
    "driver_failed_to_yield": "Driver didn't stop for me",
    "turning_vehicle": "Turning car cut me off",
    "speeding": "Cars going too fast",
    "no_sidewalk": "No sidewalk",
    "blocked_sidewalk": "Sidewalk blocked or broken",
    "hard_to_cross": "Hard to cross",
    "poor_visibility": "Hard to see or be seen",
    "drop_off_congestion": "Drop-off/pick-up chaos",
    "bike_conflict": "Bike or scooter problem",
    "other": "Something else",
}

# Used in summaries and sentences ("mostly: turning cars").
SHORT_LABEL: dict[str, str] = {
    "driver_failed_to_yield": "Drivers not yielding",
    "turning_vehicle": "Turning cars",
    "speeding": "Speeding",
    "no_sidewalk": "No sidewalk",
    "blocked_sidewalk": "Blocked sidewalks",
    "hard_to_cross": "Hard crossings",
    "poor_visibility": "Poor visibility",
    "drop_off_congestion": "Drop-off chaos",
    "bike_conflict": "Bike/scooter problems",
    "other": "Other",
}

# "Road owner" is usually VDOT for roads in Fairfax County and the city for streets in the City of Fairfax.
WHO_CAN_FIX: dict[str, str] = {
    "driver_failed_to_yield": "Police (enforcement)",
    "turning_vehicle": "Police; signal timing (road owner)",
    "speeding": "Police; road owner (traffic calming)",
    "no_sidewalk": "Road owner",
    "blocked_sidewalk": "Road owner or property owner",
    "hard_to_cross": "Road owner; task force (crossing guards)",
    "poor_visibility": "Road owner",
    "drop_off_congestion": "School (FCPS)",
    "bike_conflict": "Road owner",
    "other": "Task force (to route it)",
}

SEVERITY_LABEL: dict[int, str] = {1: "Felt unsafe", 2: "Close call", 3: "Very close or contact"}
