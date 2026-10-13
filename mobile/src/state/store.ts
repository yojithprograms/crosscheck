import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Crypto from "expo-crypto";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type TravelMode = "walk" | "bike";
export type LatLon = { lat: number; lon: number };
export type SavedRoute = { origin: LatLon; mode: TravelMode };
export type Layers = { risk: boolean; crashes: boolean; reports: boolean };

// What is saved on the device (DESIGN.md §8.4, APP_FLOW §1). Nothing here ever goes to the server
// except the random install ID, which is a header with no personal information.
type PersistedState = {
  ageGate: "ok" | "under13" | null; // the neutral age question on S2
  onboarded: boolean;
  installId: string; // random per install
  schoolId: string | null;
  travelMode: TravelMode;
  savedRoute: SavedRoute | null; // stays on the device
  layers: Layers;
};

type AppState = PersistedState & {
  hydrated: boolean; // true once the saved values have been read from the device
  setAgeGate: (answer: "ok" | "under13") => void;
  completeOnboarding: () => void;
  setSchool: (id: string) => void;
  setTravelMode: (mode: TravelMode) => void;
  saveRoute: (route: SavedRoute) => void;
  clearSavedRoute: () => void;
  toggleLayer: (key: keyof Layers) => void;
  resetAll: () => void;
};

const initialPersisted = (): PersistedState => ({
  ageGate: null,
  onboarded: false,
  installId: "",
  schoolId: null,
  travelMode: "walk",
  savedRoute: null,
  layers: { risk: true, crashes: true, reports: true },
});

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      ...initialPersisted(),
      hydrated: false,
      setAgeGate: (ageGate) => set({ ageGate }),
      completeOnboarding: () => set({ onboarded: true }),
      setSchool: (schoolId) => set({ schoolId }),
      setTravelMode: (travelMode) => set({ travelMode }),
      saveRoute: (savedRoute) => set({ savedRoute }),
      clearSavedRoute: () => set({ savedRoute: null }),
      toggleLayer: (key) => set((state) => ({ layers: { ...state.layers, [key]: !state.layers[key] } })),
      resetAll: () => set({ ...initialPersisted(), installId: Crypto.randomUUID() }),
    }),
    {
      name: "crosscheck-store",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state): PersistedState => ({
        ageGate: state.ageGate,
        onboarded: state.onboarded,
        installId: state.installId,
        schoolId: state.schoolId,
        travelMode: state.travelMode,
        savedRoute: state.savedRoute,
        layers: state.layers,
      }),
      // After the saved values load: make an install ID if this is the first launch, and mark ready.
      onRehydrateStorage: () => (state) => {
        const installId = state?.installId || Crypto.randomUUID();
        useAppStore.setState({ installId, hydrated: true });
      },
    },
  ),
);
