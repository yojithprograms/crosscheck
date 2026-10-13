import NetInfo from "@react-native-community/netinfo";
import { QueryClient, focusManager, onlineManager } from "@tanstack/react-query";
import { AppState } from "react-native";

export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: true } },
});

/**
 * Tells React Query when the phone is online and when the app is in front. Without this, React Query
 * can't notice that the network came back or that the app was reopened.
 * Call once at startup; the returned function undoes it.
 */
export function connectReactQueryToPhone(): () => void {
  onlineManager.setEventListener((setOnline) =>
    NetInfo.addEventListener((state) => setOnline(state.isConnected !== false)),
  );
  const appState = AppState.addEventListener("change", (status) => focusManager.setFocused(status === "active"));
  return () => appState.remove();
}
