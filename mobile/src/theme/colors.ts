// Colors (DESIGN.md §9.1). Never show risk by color alone: pair it with line style, width, a label, or an icon.
export const colors = {
  brand: "#0F766E", // teal: primary buttons, active tab, school marker
  brandDark: "#115E59",
  brandTint: "#F0FDFA", // very light teal: the selected route card
  onBrand: "#FFFFFF",
  bg: "#FFFFFF",
  surface: "#F8FAFC", // cards
  border: "#E2E8F0",
  text: "#0F172A",
  textMuted: "#475569",
  riskHigh: "#DC2626", // red, solid thick line
  riskMedium: "#F59E0B", // amber, dashed line
  riskLow: "#94A3B8",
  routeFast: "#64748B", // gray dashed
  routeLower: "#2563EB", // blue solid
  report: "#7C3AED", // purple pins = student reports
  crash: "#111827", // dark dots = past crashes
  success: "#16A34A",
  warnBg: "#FEF3C7",
  warnText: "#78350F",
  errorBg: "#FEE2E2",
  errorText: "#7F1D1D",
  infoBg: "#E0F2FE",
  infoText: "#0C4A6E",
} as const;
