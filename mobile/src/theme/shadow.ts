import type { ViewStyle } from "react-native";

import { colors } from "@/theme/colors";

// Soft, blue-tinted shadows (DESIGN.md §9.3). Cards float a little; sheets and floating panels float more.
export const shadow = {
  card: {
    shadowColor: colors.shadow,
    shadowOpacity: 0.08,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  raised: {
    shadowColor: colors.shadow,
    shadowOpacity: 0.16,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: -6 },
    elevation: 10,
  },
  floating: {
    shadowColor: colors.shadow,
    shadowOpacity: 0.18,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
} satisfies Record<string, ViewStyle>;
