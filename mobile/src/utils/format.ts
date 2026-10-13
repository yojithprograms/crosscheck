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
