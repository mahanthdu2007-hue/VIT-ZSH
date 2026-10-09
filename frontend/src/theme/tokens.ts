// Design tokens (§15). The only source of colours, fonts, type sizes, spacing and motion.

export const colors = {
  ink: "#1D1D1F",
  paper: "#F5F5F7",
  surface: "#FFFFFF",
  line: "#E3E3E8",
  studentFit: "#6C4CF1",
  financialFit: "#0E9F8E",
  marketDemand: "#D9930D",
  growth: "#2F7DE1",
  parentAlignment: "#D63F74",
  danger: "#B42318",
} as const;

export const fonts = {
  heading: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
  body: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
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
  "3xl": "56px",
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
  14: "56px",
  16: "64px",
  20: "80px",
  24: "96px",
  32: "128px",
  40: "160px",
  56: "224px",
  64: "256px",
} as const;

export const radii = {
  none: "0px",
  sm: "6px",
  DEFAULT: "8px",
  lg: "14px",
  xl: "20px",
  "2xl": "28px",
  full: "9999px",
} as const;

export const shadows = {
  none: "none",
  DEFAULT: "0 1px 2px rgba(0, 0, 0, 0.04), 0 4px 16px rgba(0, 0, 0, 0.04)",
  lg: "0 2px 6px rgba(0, 0, 0, 0.05), 0 16px 40px rgba(0, 0, 0, 0.10)",
} as const;

// Tall enough for the selected career's detail, so the top-careers list beside it never looks cut short.
export const layout = {
  careerRowMinHeight: "640px",
} as const;

// One easing curve for everything: a fast start that settles gently, like a physical object coming to rest.
export const timing = {
  ease: [0.22, 1, 0.36, 1] as [number, number, number, number],
  fast: 0.2,
  base: 0.6,
  slow: 1.1,
  stagger: 0.08,
  rise: 24,
  pill: { type: "spring", stiffness: 420, damping: 36 } as const,
} as const;

// The five PRISM Score components (§7.8) and their fixed colours (§15).
export const componentColors = {
  student_fit: colors.studentFit,
  financial_fit: colors.financialFit,
  market_demand: colors.marketDemand,
  growth: colors.growth,
  parent_alignment: colors.parentAlignment,
} as const;
