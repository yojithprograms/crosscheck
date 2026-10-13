import { useRouter } from "expo-router";
import { useMemo } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import MapView from "react-native-maps";

import { useCrashes, useRiskLayer, useSchools } from "@/api/hooks";
import { Banner } from "@/components/Banner";
import { Chip } from "@/components/Chip";
import { EmptyState } from "@/components/EmptyState";
import { Legend } from "@/components/Legend";
import { PrimaryButton } from "@/components/PrimaryButton";
import { SecondaryButton } from "@/components/SecondaryButton";
import { strings } from "@/copy/strings";
import { CrashLayer } from "@/map/CrashLayer";
import { RiskLayer } from "@/map/RiskLayer";
import { SchoolMarker } from "@/map/SchoolMarker";
import { useAppStore, type Layers } from "@/state/store";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";
import { regionForRadius } from "@/utils/geo";

const LAYER_KEYS: (keyof Layers)[] = ["risk", "crashes", "reports"];

/** S4 · the home tab: your school's risk map. */
export default function MapTab() {
  const router = useRouter();
  const schoolId = useAppStore((state) => state.schoolId);
  const layers = useAppStore((state) => state.layers);
  const toggleLayer = useAppStore((state) => state.toggleLayer);

  const schools = useSchools();
  const school = schools.data?.find((s) => s.id === schoolId);
  const risk = useRiskLayer(school?.id ?? null);
  const crashes = useCrashes(school?.id ?? null);

  const region = useMemo(() => (school ? regionForRadius(school.lat, school.lon, school.radius_m) : undefined), [school]);

  const changeSchool = () => router.push({ pathname: "/onboarding/school", params: { from: "settings" } });

  if (schools.isPending) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brand} />
        <Text style={styles.muted}>{strings.map.loadingMap}</Text>
      </View>
    );
  }
  if (schools.isError) {
    return (
      <EmptyState
        icon="cloud-offline-outline"
        title={strings.schoolPicker.unreachableTitle}
        body={strings.schoolPicker.unreachableBody}
        action={<PrimaryButton title={strings.schoolPicker.tryAgain} onPress={() => void schools.refetch()} />}
      />
    );
  }
  if (!school || !region) {
    return (
      <EmptyState
        icon="map-outline"
        title={strings.map.notReadyTitle}
        body={strings.map.notReadyBody}
        action={<PrimaryButton title={strings.map.changeSchool} onPress={changeSchool} />}
      />
    );
  }

  const layerFailed = risk.isError || crashes.isError;
  const retryLayers = () => {
    if (risk.isError) void risk.refetch();
    if (crashes.isError) void crashes.refetch();
  };

  return (
    <View style={styles.screen}>
      <MapView
        key={school.id}
        style={StyleSheet.absoluteFill}
        initialRegion={region}
        rotateEnabled={false}
        pitchEnabled={false}
        toolbarEnabled={false}
      >
        {layers.risk ? <RiskLayer layer={risk.data} onSelect={() => undefined} /> : null}
        {layers.crashes ? <CrashLayer layer={crashes.data} onSelect={() => undefined} /> : null}
        <SchoolMarker school={school} />
      </MapView>

      <View style={styles.top} pointerEvents="box-none">
        {layerFailed ? (
          <Banner kind="error" text={strings.map.loadError} actionLabel={strings.map.retry} onAction={retryLayers} />
        ) : null}
        <View style={styles.chips}>
          {LAYER_KEYS.map((key) => (
            <Chip key={key} label={strings.map.layers[key]} selected={layers[key]} onPress={() => toggleLayer(key)} />
          ))}
        </View>
      </View>

      <View style={[styles.legend, { bottom: BOTTOM_PANEL_HEIGHT + spacing.sm }]} pointerEvents="box-none">
        <Legend />
      </View>

      <View style={styles.panel}>
        <PrimaryButton title={strings.map.planRoute} onPress={() => router.navigate("/route")} />
        <SecondaryButton title={strings.map.reportCloseCall} onPress={() => router.navigate("/report")} />
      </View>
    </View>
  );
}

const BOTTOM_PANEL_HEIGHT = shape.buttonHeight * 2 + spacing.sm * 3;

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: spacing.sm },
  muted: { ...type.caption, color: colors.textMuted },
  top: { position: "absolute", top: 0, left: 0, right: 0 },
  chips: { flexDirection: "row", gap: spacing.sm, padding: spacing.sm },
  legend: { position: "absolute", left: spacing.sm },
  panel: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colors.bg,
    padding: spacing.sm,
    paddingHorizontal: shape.screenPadding,
    gap: spacing.sm,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
});
