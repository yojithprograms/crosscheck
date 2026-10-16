// Spacing and shape (DESIGN.md §9.3).
export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const shape = {
  screenPadding: 20,
  cardRadius: 16,
  sheetRadius: 28, // the top corners of bottom sheets
  pill: 999,
  buttonHeight: 56,
  minTouchTarget: 44,
} as const;
