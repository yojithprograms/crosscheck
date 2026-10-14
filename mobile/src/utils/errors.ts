// Turns an error from the server (or from reaching it) into words for a student, plus one next step.
// The messages are APP_FLOW §8; the words live in copy/strings.ts.
import { ApiError } from "@/api/client";
import { strings } from "@/copy/strings";

/** What the screen should offer next. */
export type ErrorAction =
  | "retry" // the same request might work now (no network, a timeout, a server hiccup)
  | "move-pin" // the pin is too far from any sidewalk or street: reopen the pin picker where they left it
  | "drop-pin" // the pin is outside the covered area: pick a new one
  | "change-start" // nothing connects from there: back to the start screen
  | "change-school"; // the server has no map for this school

export type FriendlyError = { message: string; action: ErrorAction };

/** What went wrong when asking for routes, in plain words, and what the student can do about it. */
export function friendlyRouteError(error: unknown, schoolName: string): FriendlyError {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "OUTSIDE_AREA":
        return { message: strings.start.outside(schoolName), action: "drop-pin" };
      case "NO_NEARBY_PATH":
        return { message: strings.errors.noNearbyPath, action: "move-pin" };
      case "NO_ROUTE":
        return { message: strings.errors.noRoute, action: "change-start" };
      case "UNKNOWN_SCHOOL":
        return { message: strings.errors.unknownSchool, action: "change-school" };
    }
    // Any other 4xx means this start point won't work, and asking again won't change that.
    if (error.status >= 400 && error.status < 500) return { message: strings.errors.noRoute, action: "change-start" };
  }
  // No connection, a timeout, or a server error: worth trying again.
  return { message: strings.errors.routesFailed, action: "retry" };
}
