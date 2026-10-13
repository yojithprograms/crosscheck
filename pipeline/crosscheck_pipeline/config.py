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

# Step 1.2 — crashes (D1)
VDOT_CRASH_URL = "https://services.arcgis.com/p5v98VHDX9Atv3l7/ArcGIS/rest/services/Full_Crash/FeatureServer/0"
CRASH_WHERE = "(PED_NONPED = '1' OR BIKE_NONBIKE = '1')"
CRASH_OUT_FIELDS = (
    "DOCUMENT_NBR,CRASH_YEAR,CRASH_DT,CRASH_SEVERITY,PED_NONPED,BIKE_NONBIKE,"
    "PEDESTRIANS_KILLED,PEDESTRIANS_INJURED,LIGHT_CONDITION,INTERSECTION_TYPE,"
    "TRAFFIC_CONTROL_TYPE,SCHOOL_ZONE,ROUTE_OR_STREET_NM,PHYSICAL_JURIS,LAT,LON"
)
ARCGIS_PAGE_SIZE = 2000       # the server's maxRecordCount
ARCGIS_PAUSE_S = 0.5          # wait between page requests
KA_SEVERITIES = ("K", "A")    # fatal, severe

# Step 1.3 — OpenStreetMap
STUDY_AREA_MODE = "pilot"      # "pilot": circles around the pilot schools (light on memory); "county": whole study area
PILOT_AREA_RADIUS_M = 8000     # "pilot" mode: circle around each pilot school
OSM_NETWORK_TYPE = "drive_service"
OSM_POINT_TAGS = {"highway": ["traffic_signals", "crossing", "bus_stop"]}
OSM_SIDEWALK_TAGS = {"footway": "sidewalk"}

# Step 1.4 — sidewalks and coverage check
COUNTY_SIDEWALKS_URL = "https://services1.arcgis.com/ioennV6PpG5Xodq0/ArcGIS/rest/services/Sidewalks_Centerline/FeatureServer/0"
COUNTY_SIDEWALK_TYPES = ("SIDEWALK",)     # D3 TYPE values that are sidewalks
COUNTY_CROSSWALK_TYPES = ("CONNECTOR",)   # D3 TYPE values that are crosswalk connectors (crossings)
COVERAGE_CELL_M = 1000                    # coverage grid cell size
GAP_MIN_ROAD_M = 2000                     # a cell needs at least this much road to be judged
GAP_MAX_COUNTY_RATIO = 0.05               # county sidewalk length / road length below this = "gap"
GAP_ROAD_EXCLUDE = ("motorway", "motorway_link", "service")  # roads left out of the coverage denominator
