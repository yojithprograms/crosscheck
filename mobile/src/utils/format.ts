// Small helpers that turn numbers from the server into the words students see (DESIGN.md §8.9).
// The words themselves live in copy/strings.ts.
import { strings } from "@/copy/strings";

const METERS_PER_MILE = 1609.344;

/** 0.6 mi */
export function miles(meters: number): string {
  return `${(meters / METERS_PER_MILE).toFixed(1)} mi`;
}

/** 12 min */
export function minutes(count: number): string {
  return `${count} min`;
}

/** Riskier than 92% of Fairfax-area streets */
export function percentileText(riskPct: number): string {
  return strings.risk.percentile(Math.round(riskPct));
}

/** "Oct 2026" from a year and a month number (1 to 12). */
export function monthYear(year: number, month: number): string {
  return `${strings.months[month - 1]} ${year}`;
}

/** Puts "≈" in front of values that were estimated rather than measured: "≈ 35". */
export function approx(value: string | number, estimated: boolean): string {
  return estimated ? `≈ ${value}` : `${value}`;
}

/** The plain-words name of a crash's severity code (K, A, B, C, O). */
export function crashSeverityText(code: string): string {
  return strings.crash.severity[code as keyof typeof strings.crash.severity] ?? strings.crash.severity.O;
}

// How much sidewalk counts as "Yes" and "Partly" (the pipeline treats under 0.25 as "no sidewalk").
const SIDEWALK_YES_AT = 0.75;
const SIDEWALK_PARTLY_AT = 0.25;

/** "Yes", "Partly", "No", or "Unknown" (where the county sidewalk data doesn't cover the area). */
export function sidewalkText(coverage: number, known: boolean): string {
  const values = strings.cards.sidewalkValues;
  if (!known) return values.unknown;
  if (coverage >= SIDEWALK_YES_AT) return values.yes;
  if (coverage >= SIDEWALK_PARTLY_AT) return values.partly;
  return values.no;
}
