// Design tokens (§15). The only source of colours, fonts, type sizes and spacing.

export const colors = {
  ink: "#141413",
  paper: "#FAF9F5",
  surface: "#FFFFFF",
  line: "#E8E6DC",
  studentFit: "#6C4CF1",
  financialFit: "#0E9F8E",
  marketDemand: "#D9930D",
  growth: "#2F7DE1",
  parentAlignment: "#D63F74",
  danger: "#B42318",
} as const;

export const fonts = {
  heading: ['"Source Serif 4"', "Georgia", "serif"],
  body: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
} as const;

export const fontWeights = {
  heading: 600,
  body: 400,
  bodyStrong: 500,
} as const;

export const fontSizes = {
  sm: "14px",
  base: "16px",
  lg: "20px",
  xl: "28px",
  "2xl": "40px",
} as const;

// 4 px spacing grid; keys follow Tailwind's names so p-4 = 16 px.
export const spacing = {
  px: "1px",
  0: "0px",
  0.5: "2px",
  1: "4px",
  1.5: "6px",
  2: "8px",
  3: "12px",
  4: "16px",
  5: "20px",
  6: "24px",
  8: "32px",
  10: "40px",
  12: "48px",
  16: "64px",
  20: "80px",
  24: "96px",
  32: "128px",
  56: "224px",
  64: "256px",
} as const;

export const radii = {
  none: "0px",
  sm: "4px",
  DEFAULT: "6px",
  lg: "10px",
  xl: "16px",
  full: "9999px",
} as const;

export const shadows = {
  none: "none",
  DEFAULT: "none",
  lg: "0 8px 24px rgba(20, 20, 19, 0.10)",
} as const;

// The five PRISM Score components (§7.8) and their fixed colours (§15).
export const componentColors = {
  student_fit: colors.studentFit,
  financial_fit: colors.financialFit,
  market_demand: colors.marketDemand,
  growth: colors.growth,
  parent_alignment: colors.parentAlignment,
} as const;
