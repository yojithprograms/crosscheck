import { Ionicons } from "@expo/vector-icons";
import { memo } from "react";
import { Marker } from "react-native-maps";

import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import type { LatLng } from "@/utils/geo";

const PIN_SIZE = 40;

/** The pin the student dropped (or their location), shown where the routes begin. Its tip is the start. */
export const StartMarker = memo(function StartMarker({ point }: { point: LatLng }) {
  return (
    <Marker
      coordinate={point}
      anchor={{ x: 0.5, y: 1 }}
      tracksViewChanges={false}
      accessibilityLabel={strings.results.startMarker}
      zIndex={9}
    >
      <Ionicons name="location-sharp" size={PIN_SIZE} color={colors.brand} />
    </Marker>
  );
});
