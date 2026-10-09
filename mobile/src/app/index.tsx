import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import MapView from "react-native-maps";

import { strings } from "@/copy/strings";

// Step 0.4 smoke test: a map plus one line of text from GET /health.
// Replaced by the real screens in Phase 3.
const HEALTH_TIMEOUT_MS = 60_000;
const FAIRFAX_REGION = {
  latitude: 38.85,
  longitude: -77.3,
  latitudeDelta: 0.2,
  longitudeDelta: 0.2,
};

type Status = "checking" | "ok" | "unreachable" | "noUrl";

export default function Index() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const baseUrl = process.env.EXPO_PUBLIC_API_URL;
    if (!baseUrl) {
      setStatus("noUrl");
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS);
    fetch(`${baseUrl}/health`, { signal: controller.signal })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("bad status"))))
      .then((body: { status?: string }) =>
        setStatus(body.status === "ok" ? "ok" : "unreachable"),
      )
      .catch(() => setStatus("unreachable"))
      .finally(() => clearTimeout(timer));
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, []);

  return (
    <View style={styles.container}>
      <MapView style={styles.map} initialRegion={FAIRFAX_REGION} />
      <View style={styles.banner}>
        <Text style={styles.bannerText}>{strings.smoke[status]}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  banner: {
    position: "absolute",
    top: 60,
    alignSelf: "center",
    backgroundColor: "white",
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  bannerText: { fontSize: 16, fontWeight: "600" },
});
