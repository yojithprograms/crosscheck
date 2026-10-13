import { onlineManager, useQuery } from "@tanstack/react-query";
import { useEffect, useState, useSyncExternalStore } from "react";

import { apiFetch } from "@/api/client";
import type { CrashFeature, FeatureCollection, Meta, RiskFeature, School } from "@/api/types";

// Waking a sleeping free host can take up to a minute, so keep trying for about that long.
const WAKE_RETRIES = 12;
const WAKE_RETRY_DELAY_MS = 4_000;
const WAKE_BANNER_DELAY_MS = 2_000; // don't flash the banner on a fast launch

export type WakeState = "ok" | "waking" | "offline" | "failed";

/** True while the phone has a network connection (kept up to date by connectReactQueryToPhone). */
export function useOnline(): boolean {
  return useSyncExternalStore(onlineManager.subscribe, () => onlineManager.isOnline());
}

/**
 * Calls GET /health on launch. This both checks the server and wakes a sleeping host, and it drives the
 * "Waking up the server…" banner: ok, waking (still trying), offline (no network), or failed (gave up).
 */
export function useServerWake(): { state: WakeState; retry: () => void } {
  const online = useOnline();
  const query = useQuery({
    queryKey: ["health"],
    queryFn: () => apiFetch<{ status: string }>("/health"),
    retry: WAKE_RETRIES,
    retryDelay: WAKE_RETRY_DELAY_MS,
    networkMode: "always", // try even if the phone says it's offline, so we notice when it comes back
    staleTime: Infinity,
  });

  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (query.isSuccess) {
      setSlow(false);
      return;
    }
    const timer = setTimeout(() => setSlow(true), WAKE_BANNER_DELAY_MS);
    return () => clearTimeout(timer);
  }, [query.isSuccess]);

  let state: WakeState = "ok";
  if (query.isSuccess) state = "ok";
  else if (!online) state = "offline";
  else if (query.isError) state = "failed";
  else if (slow || query.failureCount > 0) state = "waking";

  return { state, retry: () => void query.refetch() };
}

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

/** The pilot schools (GET /schools). They rarely change, so the answer is reused for a day. */
export function useSchools() {
  return useQuery({
    queryKey: ["schools"],
    queryFn: () => apiFetch<School[]>("/schools"),
    staleTime: ONE_DAY_MS,
  });
}

/** Medium and high risk streets near a school (GeoJSON). */
export function useRiskLayer(schoolId: string | null) {
  return useQuery({
    queryKey: ["risk-layer", schoolId],
    queryFn: () => apiFetch<FeatureCollection<RiskFeature>>(`/schools/${schoolId}/risk-layer`),
    enabled: !!schoolId,
    staleTime: ONE_DAY_MS,
  });
}

/** Past pedestrian and bike crashes near a school (GeoJSON points). */
export function useCrashes(schoolId: string | null) {
  return useQuery({
    queryKey: ["crashes", schoolId],
    queryFn: () => apiFetch<FeatureCollection<CrashFeature>>(`/schools/${schoolId}/crashes`),
    enabled: !!schoolId,
    staleTime: ONE_DAY_MS,
  });
}

/** Data dates and model accuracy (GET /meta). */
export function useMeta() {
  return useQuery({
    queryKey: ["meta"],
    queryFn: () => apiFetch<Meta>("/meta"),
    staleTime: ONE_DAY_MS,
  });
}
