import { Ionicons } from "@expo/vector-icons";
import { memo } from "react";
import { StyleSheet, View } from "react-native";
import { Marker } from "react-native-maps";

import type { CrashFeature, FeatureCollection } from "@/api/types";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { toLatLng } from "@/utils/geo";

type Props = {
  layer: FeatureCollection<CrashFeature> | undefined;
  onSelect: (feature: CrashFeature) => void; // tapping a dot opens the crash card
};

/** Small dark dots with a walking or bike icon. Serious and fatal crashes get a red ring. */
export const CrashLayer = memo(function CrashLayer({ layer, onSelect }: Props) {
  if (!layer) return null;
  return (
    <>
      {layer.features.map((feature, index) => {
        const { mode, severity, year } = feature.properties;
        const serious = severity === "K" || severity === "A";
        return (
          <Marker
            key={`${year}-${index}`}
            coordinate={toLatLng(feature.geometry.coordinates)}
            anchor={{ x: 0.5, y: 0.5 }}
            tracksViewChanges={false}
            accessibilityLabel={strings.map.crashMarker(mode, year)}
            onPress={() => onSelect(feature)}
          >
            <View style={[styles.dot, serious && styles.ring]}>
              <Ionicons name={mode === "ped" ? "walk" : "bicycle"} size={12} color="white" />
            </View>
          </Marker>
        );
      })}
    </>
  );
});

const styles = StyleSheet.create({
  dot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.crash,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: "white",
  },
  ring: { borderColor: colors.riskHigh, borderWidth: 3 },
});
