// "Use my location" (S6). The position is read once, kept only in memory by the caller, and never
// logged or saved. See CLAUDE.md: route origins may be near a student's home.
import * as Location from "expo-location";

import type { LatLon } from "@/state/store";

const LOCATION_TIMEOUT_MS = 15000; // GPS can hang indoors; give up after this long

export type LocationResult =
  | { status: "ok"; point: LatLon }
  | { status: "denied" } // permission refused, or Location is turned off in the phone's settings
  | { status: "unavailable" }; // permission is fine, but no position came back in time

/** Asks for permission the first time, then reads the phone's current position once. */
export async function getCurrentPoint(): Promise<LocationResult> {
  try {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (permission.status !== "granted") return { status: "denied" };
    if (!(await Location.hasServicesEnabledAsync())) return { status: "denied" };

    const position = await Promise.race([
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), LOCATION_TIMEOUT_MS)),
    ]);
    if (!position) return { status: "unavailable" };
    return { status: "ok", point: { lat: position.coords.latitude, lon: position.coords.longitude } };
  } catch {
    return { status: "unavailable" };
  }
}
