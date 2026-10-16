// Colors (DESIGN.md §9.1): a soft, pastel blue family for the app's own surfaces, plus fixed risk colors
// that carry meaning on the map. Never show risk by color alone: pair it with line style, width, a label, or an icon.
export const colors = {
  // Brand blues. `brand` is the one saturated blue (buttons, links, active tab); the rest are pastel tints of it.
  brand: "#2F6BE8", // buttons, active tab, school marker (white text on it is 4.78:1)
  brandDark: "#1F4FB8", // pressed buttons, links on tinted backgrounds
  brandSoft: "#DCEAFF", // icon circles, the active tab pill, selected chips
  brandTint: "#EAF2FF", // the selected route card, soft highlight blocks
  brandSky: "#BBD6FF", // decorative circles and illustrations
  onBrand: "#FFFFFF",

  // Surfaces
  bg: "#F5F9FF", // screen background: a very pale blue
  surface: "#FFFFFF", // cards, panels, and sheets sit on the background in white
  border: "#DCE7F7",
  hairline: "#E8F0FB", // thin dividers
  shadow: "#1E3A8A", // the tint of every soft shadow

  // Text
  text: "#0B1B3A", // deep navy
  textMuted: "#52627F",

  // Risk and map colors: these carry meaning, so the pastel theme doesn't touch them.
  riskHigh: "#DC2626", // red, solid thick line
  riskMedium: "#F59E0B", // amber, dashed line
  riskLow: "#94A3B8",
  routeFast: "#64748B", // gray dashed
  routeLower: "#2563EB", // blue solid
  report: "#7C3AED", // purple pins = student reports
  crash: "#111827", // dark dots = past crashes
  success: "#16A34A",

  // Message strips
  warnBg: "#FEF3C7",
  warnText: "#78350F",
  errorBg: "#FEE2E2",
  errorText: "#7F1D1D",
  infoBg: "#E3EEFF",
  infoText: "#0C3B7A",

  // Disabled controls
  disabledBg: "#D5E2F7",
  disabledText: "#6B7F9E",
} as const;
