import type { LonLat } from "@/api/types";

const METERS_PER_DEG_LAT = 110540;
const METERS_PER_DEG_LON_AT_EQUATOR = 111320;
const EARTH_RADIUS_M = 6371000;
const MAP_SPAN_OF_RADIUS = 2.2; // the school map starts about 2.2 x the radius wide (DESIGN.md §8.6)

export type LatLng = { latitude: number; longitude: number };

/**
 * Converts the server's GeoJSON order [lon, lat] to what react-native-maps wants. Always use this:
 * swapping the two is the most common map bug.
 */
export function toLatLng([lon, lat]: LonLat): LatLng {
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
