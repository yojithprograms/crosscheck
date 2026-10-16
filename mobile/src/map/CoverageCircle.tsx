import { memo } from "react";
import { Circle } from "react-native-maps";

import type { School } from "@/api/types";
import { colors } from "@/theme/colors";

const FILL = "rgba(47, 107, 232, 0.12)"; // light blue (colors.brand at 12% opacity)

/** A light blue circle around the school showing the area CrossCheck covers (S7). */
export const CoverageCircle = memo(function CoverageCircle({ school }: { school: School }) {
  return (
    <Circle
      center={{ latitude: school.lat, longitude: school.lon }}
      radius={school.radius_m}
      strokeColor={colors.brand}
      strokeWidth={2}
      fillColor={FILL}
    />
  );
});
