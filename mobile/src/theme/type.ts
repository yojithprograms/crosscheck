import type { TextStyle } from "react-native";

// Type scale (DESIGN.md §9.2): system font, font scaling stays on.
export const type = {
  screenTitle: { fontSize: 30, lineHeight: 36, fontWeight: "800", letterSpacing: -0.5 },
  sectionTitle: { fontSize: 22, lineHeight: 28, fontWeight: "700", letterSpacing: -0.3 },
  headline: { fontSize: 17, lineHeight: 22, fontWeight: "600" },
  body: { fontSize: 16, lineHeight: 23, fontWeight: "400" },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: "400" },
  eyebrow: { fontSize: 12, lineHeight: 16, fontWeight: "700", letterSpacing: 0.8, textTransform: "uppercase" },
} satisfies Record<string, TextStyle>;
