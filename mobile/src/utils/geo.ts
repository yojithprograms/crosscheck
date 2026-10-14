import type { LonLat } from "@/api/types";
import type { LatLon } from "@/state/store";

const METERS_PER_DEG_LAT = 110540;
const METERS_PER_DEG_LON_AT_EQUATOR = 111320;
const EARTH_RADIUS_M = 6371000;
const MAP_SPAN_OF_RADIUS = 2.2; // the school map starts about 2.2 x the radius wide (DESIGN.md §8.6)
const FIT_PADDING_FACTOR = 1.5; // regionFitting leaves this much room around the points
const MIN_FIT_SPAN_DEG = 0.004; // about 450 m, so two nearby points don't zoom in absurdly far

export type LatLng = { latitude: number; longitude: number };

/**
 * Converts the server's GeoJSON order [lon, lat] to what react-native-maps wants. Always use this:
 * swapping the two is the most common map bug.
 */
export function toLatLng([lon, lat]: LonLat): LatLng {
  return { latitude: lat, longitude: lon };
}

/** A {lat, lon} point (what the store and the API use) as react-native-maps wants it. */
export function pointToLatLng({ lat, lon }: LatLon): LatLng {
  return { latitude: lat, longitude: lon };
}

/** A map region centered on a point and about `MAP_SPAN_OF_RADIUS` times the radius across. */
export function regionForRadius(lat: number, lon: number, radiusM: number) {
  const spanM = radiusM * MAP_SPAN_OF_RADIUS;
  return {
    latitude: lat,
    longitude: lon,
    latitudeDelta: spanM / METERS_PER_DEG_LAT,
    longitudeDelta: spanM / (METERS_PER_DEG_LON_AT_EQUATOR * Math.cos((lat * Math.PI) / 180)),
  };
}

/**
 * A map region that shows all the given points with some room around them. Used for the first view of the
 * route results (start point and school), before the routes arrive and `fitToCoordinates` takes over.
 */
export function regionFitting(points: LatLng[]) {
  const lats = points.map((p) => p.latitude);
  const lons = points.map((p) => p.longitude);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  return {
    latitude: (minLat + maxLat) / 2,
    longitude: (minLon + maxLon) / 2,
    latitudeDelta: Math.max((maxLat - minLat) * FIT_PADDING_FACTOR, MIN_FIT_SPAN_DEG),
    longitudeDelta: Math.max((maxLon - minLon) * FIT_PADDING_FACTOR, MIN_FIT_SPAN_DEG),
  };
}

/** Great-circle (haversine) distance in meters. */
export function distanceMeters(a: LatLng, b: LatLng): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(b.latitude - a.latitude);
  const dLon = toRad(b.longitude - a.longitude);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

/** True if the point is within `radiusM` meters of the center. */
export function insideCircle(point: LatLng, center: LatLng, radiusM: number): boolean {
  return distanceMeters(point, center) <= radiusM;
}
