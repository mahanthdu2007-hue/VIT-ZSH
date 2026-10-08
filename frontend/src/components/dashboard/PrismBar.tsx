import { motion } from "framer-motion";
import { useState } from "react";
import { formatPoints } from "../../lib/format";
import { COMPONENTS, type ComponentKey } from "../../lib/labels";
import { componentColors } from "../../theme/tokens";

type PrismBarProps = {
  points: Record<string, number>;
  score: number;
  /** Large bars have focusable segments; small ones sit inside a clickable row and are hidden from screen readers. */
  size?: "sm" | "lg";
  /** What-If only (§15's one motion moment): segments re-flow with a layout animation when points change. */
  animated?: boolean;
};

/** §15 signature component: one career's score as five coloured segments sized by the points each part earned. */
export function PrismBar({ points, score, size = "lg", animated = false }: PrismBarProps) {
  const [active, setActive] = useState<ComponentKey | null>(null);
  const interactive = size === "lg";
  let offset = 0;
  const segments = COMPONENTS.map((component) => {
    const earned = points[component.key] ?? 0;
    const segment = { ...component, earned, start: offset };
    offset += earned;
    return segment;
  });
  const shown = segments.find((s) => s.key === active);

  return (
    <div
      className="relative"
      role={interactive ? "group" : undefined}
      aria-label={interactive ? `PRISM Score ${formatPoints(score)} out of 100, split into five parts` : undefined}
      aria-hidden={interactive ? undefined : true}
      onMouseLeave={() => setActive(null)}
    >
      <div className={`flex w-full overflow-hidden rounded-full bg-line ${size === "lg" ? "h-6" : "h-2"}`}>
        {segments.map((s) => (
          <motion.span
            key={s.key}
            layout={animated}
            tabIndex={interactive ? 0 : undefined}
            role={interactive ? "img" : undefined}
            aria-label={
              interactive ? `${s.label}: ${formatPoints(s.earned)} of ${s.max} points. ${s.meaning}` : undefined
            }
            className="h-full border-r border-surface last:border-r-0 focus-visible:outline-offset-0"
            style={{ width: `${s.earned}%`, backgroundColor: componentColors[s.key] }}
            onMouseEnter={() => setActive(s.key)}
            onFocus={() => setActive(s.key)}
            onBlur={() => setActive(null)}
            onClick={() => setActive(active === s.key ? null : s.key)}
          />
        ))}
      </div>
      {shown && (
        <div
          role="tooltip"
          className="pointer-events-none absolute bottom-full z-10 mb-2 w-56 -translate-x-1/2 rounded-lg bg-ink px-3 py-2 text-sm text-surface shadow-lg"
          style={{ left: `clamp(112px, ${shown.start + shown.earned / 2}%, calc(100% - 112px))` }}
        >
          <span className="flex items-center gap-1.5 font-medium">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: componentColors[shown.key] }} />
            {shown.label}: {formatPoints(shown.earned)} of {shown.max}
          </span>
          <span className="mt-0.5 block text-surface/80">{shown.meaning}</span>
        </div>
      )}
    </div>
  );
}
