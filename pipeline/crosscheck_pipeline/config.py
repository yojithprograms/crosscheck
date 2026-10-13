"""Tunable constants for the pipeline (DESIGN.md §6.0). No tunable numbers live anywhere else."""

# Study area
STUDY_AREA_QUERIES = ["Fairfax County, Virginia, USA", "City of Fairfax, Virginia, USA"]
SCHOOL_BUFFER_EXTRA_M = 500                    # study area also covers (radius_m + this) around each pilot school
CRS_METERS = "EPSG:32618"                      # UTM zone 18N, meters
CRASH_BBOX = (-77.60, 38.55, -77.00, 39.10)    # lon/lat box around the study area plus a margin (clipped later)

# Time windows (inclusive years)
TRAIN_HIST = (2017, 2020)
TRAIN_LABEL = (2021, 2024)
SERVE_HIST = (2022, 2025)
MAP_CRASHES_FROM = 2022
PRELIM_YEAR = 2026

# Geometry (meters)
ASSIGN_MAX_DIST_M = 30        # crash → road segment
SIDEWALK_BUFFER_M = 15
SIGNAL_SNAP_M = 20
CROSSING_SNAP_M = 15
BUS_STOP_RADIUS_M = 200
WALK_TO_ROAD_MAX_M = 25       # walkway edge midpoint → road segment
DEFAULT_RADIUS_M = {"ES": 1600, "MS": 2400, "HS": 2400}
MAX_GRAPH_EDGES = 12000       # per school walk graph (undirected edges)
AADT_SNAP_M = 15              # Step 1.9

# Feature and reason thresholds
FAST_MPH = 35                 # "fast road"
WIDE_ROAD_LANES = 4           # "wide road"
NO_SIDEWALK_COV = 0.25        # sidewalk_cov below this = "no sidewalk"
BUS_STOP_CAP = 10

# Risk classes (percentile among all non-freeway road segments)
HIGH_PCT = 90
MEDIUM_PCT = 70

# Validation and reports
GRID_CELL_M = 2000
CV_FOLDS = 5
RANDOM_SEED = 42
TOP_SPOTS = 5
TOP_SPOT_MIN_SPACING_M = 150

# Step 1.1 — pilot schools
FCPS_SCHOOLS_URL = "https://www.fairfaxcounty.gov/gispubsf1/rest/services/FRD/Tier_II_Facilities/MapServer/1"
SCHOOL_LEVELS = ("ES", "MS", "HS")
SCHOOL_LEVEL_TYPES = {"ES": "Elementary School", "MS": "Middle School", "HS": "High School"}  # D4 TYPE_DESC
SCHOOL_REF_MAX_DIST_M = 400   # entrance farther than this from the FCPS layer's point → "check this one"
HTTP_TIMEOUT_S = 60
HTTP_RETRIES = 3
