import type { Config } from "tailwindcss";
import { colors, fontSizes, fontWeights, fonts, layout, radii, shadows, spacing } from "./src/theme/tokens";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    colors: { ...colors, transparent: "transparent", current: "currentColor" },
    fontFamily: {
      heading: [...fonts.heading],
      body: [...fonts.body],
    },
    fontSize: fontSizes,
    fontWeight: {
      normal: String(fontWeights.body),
      medium: String(fontWeights.bodyStrong),
      semibold: String(fontWeights.heading),
    },
    spacing,
    borderRadius: radii,
    boxShadow: shadows,
    extend: {
      minHeight: { "career-row": layout.careerRowMinHeight },
    },
  },
  plugins: [],
} satisfies Config;
