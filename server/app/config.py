"""Settings from server/.env plus every tunable number (DESIGN.md §7.2).

Secrets (the Anthropic key, the admin token) live only in server/.env, which git ignores.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./crosscheck.db"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    admin_token: str = ""
    data_dir: Path = Path("./data")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Risk classes (same as the pipeline)
HIGH_PCT = 90
MEDIUM_PCT = 70

# Routing (§7.6)
ALPHA = 3.0                  # how much risky streets "stretch"
BETA_CROSSING_M = 400        # extra effective meters for crossing the riskiest roads
GAMMA_INTERSECTION_M = 200   # extra effective meters for entering a risky intersection from another road
REPORT_PENALTY_M = 150       # extra effective meters per recent confirmed report on an edge
REPORT_MAX_COUNT = 3         # max reports counted per edge
REPORT_WINDOW_DAYS = 180     # older reports stop affecting routes
WALK_SPEED_MPS = 1.2         # about 2.7 mph
BIKE_SPEED_MPS = 4.0         # about 9 mph
SNAP_MAX_M = 250             # max distance from a start point to a walkway
AREA_SLACK = 1.1             # a route start can be up to 110% of the school radius away
LONG_DETOUR_RATIO = 1.6      # add the "a lot longer" note when the lower-risk route is this many times longer

# Reports (§7.8)
REPORT_AREA_SLACK = 1.2      # a report can be up to 120% of the school radius away
REPORT_SNAP_MAX_M = 60       # max distance from a report to a walkway edge
PENDING_TTL_H = 24           # unconfirmed reports are deleted after this many hours
MAX_PHOTO_PX = 1280
JPEG_QUALITY = 80
MAX_UPLOAD_MB = 8
RATE_LIMIT_INSTALL_24H = 10  # reports allowed per day per install
RATE_LIMIT_IP_24H = 30       # reports allowed per day per IP address

# Hazards and summaries (§7.7, §7.10)
HAZARD_GROUP_M = 40          # merge hazards closer than this along a route
WIDE_ROAD_LANES = 4          # "wide road" for the no-signal hazard reason (same as the pipeline)
TOP_SPOT_REPORT_RADIUS_M = 75  # reports this close to a top spot count toward it
SUMMARY_RECENT_DAYS = 90     # window for "student reports in the last 90 days"

# Geometry (flat-earth meters, same constants as the pipeline's exports)
METERS_PER_DEG_LAT = 110540
METERS_PER_DEG_LON_AT_EQUATOR = 111320
EARTH_RADIUS_M = 6371000
