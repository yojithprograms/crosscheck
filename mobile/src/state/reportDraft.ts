import { create } from "zustand";

import type { LatLon } from "@/state/store";

// The close-call report being written (DESIGN.md §8.4). It is not saved on the phone: close the app and
// the draft is gone. Only the location is here so far; the report flow (Phase 5) adds the rest.
type ReportDraft = {
  location: LatLon | null; // where it happened. S11 starts its pin here, for example at a hazard from S9.
  setLocation: (location: LatLon | null) => void;
  reset: () => void;
};

export const useReportDraft = create<ReportDraft>()((set) => ({
  location: null,
  setLocation: (location) => set({ location }),
  reset: () => set({ location: null }),
}));
