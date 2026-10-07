// Design tokens (§15). The only source of colours, fonts and type sizes.

export const colors = {
  ink: "#1B1F3B",
  paper: "#F7F8FB",
  surface: "#FFFFFF",
  line: "#E3E6EF",
  studentFit: "#6C4CF1",
  financialFit: "#0E9F8E",
  marketDemand: "#D9930D",
  growth: "#2F7DE1",
  parentAlignment: "#D63F74",
} as const;

export const fonts = {
  heading: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
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
