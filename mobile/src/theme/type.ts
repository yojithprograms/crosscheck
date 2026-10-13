import type { TextStyle } from "react-native";

// Type scale (DESIGN.md §9.2): system font, font scaling stays on.
export const type = {
  screenTitle: { fontSize: 28, lineHeight: 34, fontWeight: "700" },
  sectionTitle: { fontSize: 22, lineHeight: 28, fontWeight: "600" },
  headline: { fontSize: 17, lineHeight: 22, fontWeight: "600" },
  body: { fontSize: 16, lineHeight: 22, fontWeight: "400" },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: "400" },
} satisfies Record<string, TextStyle>;
