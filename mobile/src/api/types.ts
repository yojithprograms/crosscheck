// Types that mirror the server's API contract exactly (DESIGN.md §7.5). Coordinates from the server are
// GeoJSON order [lon, lat]; convert with toLatLng() before giving them to the map.

export type RiskClass = "low" | "medium" | "high";
export type SchoolLevel = "ES" | "MS" | "HS";
export type LonLat = [number, number];

export type School = {
  id: string;
  name: string;
  level: SchoolLevel;
  lat: number; // the main entrance
  lon: number;
  radius_m: number;
  bbox: [number, number, number, number]; // [min_lon, min_lat, max_lon, max_lat]
};

export type GeoJsonLine = { type: "LineString"; coordinates: LonLat[] };
export type GeoJsonMultiLine = { type: "MultiLineString"; coordinates: LonLat[][] };
export type GeoJsonPoint = { type: "Point"; coordinates: LonLat };

export type RiskFeature = {
  type: "Feature";
  geometry: GeoJsonLine | GeoJsonMultiLine;
  properties: {
    seg_id: string;
    seg_ids: string[];
    name: string;
    risk_class: RiskClass;
    risk_pct: number;
    crashes_recent: number;
  };
};

export type CrashFeature = {
  type: "Feature";
  geometry: GeoJsonPoint;
  properties: { year: number; month: number; severity: "K" | "A" | "B" | "C" | "O"; mode: "ped" | "bike"; prelim: boolean };
};

export type FeatureCollection<F> = { type: "FeatureCollection"; features: F[] };

export type SegmentDetail = {
  seg_id: string;
  name: string;
  risk_pct: number;
  risk_class: RiskClass;
  reasons: string[];
  speed_mph: number;
  speed_imputed: boolean;
  lanes: number;
  sidewalk_cov: number;
  sidewalk_known: boolean;
  crashes_recent: number;
  crashes_recent_ka: number;
  crashes_prelim: number;
  reports_recent: number;
};

export type HazardKind = "crossing" | "intersection" | "along" | "reported";

export type Hazard = {
  n: number;
  kind: HazardKind;
  title: string;
  lon: number;
  lat: number;
  risk_pct: number;
  risk_class: RiskClass;
  reasons: string[];
  report_count: number;
  report_types: string[];
  seg_id: string | null;
};

export type Route = {
  distance_m: number;
  duration_min: number;
  polyline: LonLat[];
  high_count: number;
  medium_count: number;
  report_spot_count: number;
  mean_risk_pct: number;
  hazards: Hazard[];
};

export type RouteKind = "fastest" | "lower_risk"; // which of the two routes in a RouteComparison

// The body of POST /routes. The origin is sent for this one call and is never stored on the server.
export type RouteRequest = {
  school_id: string;
  origin: { lat: number; lon: number };
  mode: "walk" | "bike";
};

export type RouteComparison = {
  school_id: string;
  mode: "walk" | "bike";
  same_route: boolean;
  fastest: Route;
  lower_risk: Route;
  notes: string[];
};

export type Meta = {
  data_through: string;
  data_through_date: string;
  windows: Record<string, unknown>;
  metrics: { full_top10_capture: number; full_lift: number } & Record<string, unknown>;
  model_version: string;
  generated_at: string;
};
