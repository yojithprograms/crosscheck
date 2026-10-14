import { Ionicons } from "@expo/vector-icons";
import { useMemo, useRef, useState } from "react";
import { Pressable, StyleSheet, View } from "react-native";
import MapView, { type Region } from "react-native-maps";

import type { School } from "@/api/types";
import { Banner } from "@/components/Banner";
import { PrimaryButton } from "@/components/PrimaryButton";
import { strings } from "@/copy/strings";
import { CenterPin } from "@/map/CenterPin";
import { CoverageCircle } from "@/map/CoverageCircle";
import { SchoolMarker } from "@/map/SchoolMarker";
import type { LatLon } from "@/state/store";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { insideCircle, pointToLatLng, regionForRadius } from "@/utils/geo";

const START_ZOOM_RADIUS_M = 550; // reopened at a pin: zoom to about 1.2 km across so the nearby streets are easy to see

type Props = {
  school: School;
  start?: LatLon; // where to put the pin first (for example, where it was when no street was nearby). Default: the school.
  notice?: string; // shown first when the student arrives here from a failed "Use my location" or route
  onBack: () => void;
  onConfirm: (point: LatLon) => void;
};

/** S7 · a full-screen map with a fixed pin in the center. Start here only works inside the school's circle. */
export function PinPicker({ school, start, notice, onBack, onConfirm }: Props) {
  const schoolCenter = useMemo(() => ({ latitude: school.lat, longitude: school.lon }), [school]);
  const region = useMemo(
    () =>
      start
        ? regionForRadius(start.lat, start.lon, START_ZOOM_RADIUS_M)
        : regionForRadius(school.lat, school.lon, school.radius_m),
    [school, start],
  );

  // The map's center is the pin. Keep it in a ref (it changes on every frame while dragging) and only
  // put "inside the circle or not" into state, so the screen re-renders just when that answer flips.
  const center = useRef<LatLon>(start ?? { lat: school.lat, lon: school.lon });
  const [inside, setInside] = useState(() =>
    start ? insideCircle(pointToLatLng(start), schoolCenter, school.radius_m) : true,
  );
  const [moved, setMoved] = useState(false);

  const isInside = (point: LatLon) => insideCircle(pointToLatLng(point), schoolCenter, school.radius_m);

  const onRegionChange = (next: Region) => {
    center.current = { lat: next.latitude, lon: next.longitude };
    setInside(isInside(center.current));
  };

  const confirm = () => {
    if (isInside(center.current)) onConfirm(center.current); // check again: the button can lag the map by a frame
  };

  let banner: { kind: "info" | "warn"; text: string } = { kind: "info", text: strings.pin.instruction };
  if (!inside) banner = { kind: "warn", text: strings.pin.moveInside };
  else if (notice && !moved) banner = { kind: "warn", text: notice };

  return (
    <View style={styles.screen}>
      <MapView
        style={StyleSheet.absoluteFill}
        initialRegion={region}
        rotateEnabled={false}
        pitchEnabled={false}
        toolbarEnabled={false}
        onPanDrag={() => setMoved(true)}
        onRegionChange={onRegionChange}
        onRegionChangeComplete={onRegionChange}
      >
        <CoverageCircle school={school} />
        <SchoolMarker school={school} />
      </MapView>
      <CenterPin tint={inside ? colors.brand : colors.riskHigh} />

      <View style={styles.top} pointerEvents="box-none">
        <Banner kind={banner.kind} text={banner.text} />
        <Pressable
          onPress={onBack}
          accessibilityRole="button"
          accessibilityLabel={strings.pin.back}
          style={styles.back}
          hitSlop={8}
        >
          <Ionicons name="arrow-back" size={24} color={colors.text} />
        </Pressable>
      </View>

      <View style={styles.panel}>
        <PrimaryButton title={strings.pin.startHere} onPress={confirm} disabled={!inside} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  top: { position: "absolute", top: 0, left: 0, right: 0 },
  back: {
    marginTop: spacing.sm,
    marginLeft: spacing.sm,
    width: shape.minTouchTarget,
    height: shape.minTouchTarget,
    borderRadius: shape.minTouchTarget / 2,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  panel: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colors.bg,
    padding: spacing.sm,
    paddingHorizontal: shape.screenPadding,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
});
