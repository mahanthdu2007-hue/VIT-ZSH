import { motion, useInView, useReducedMotion } from "framer-motion";
import { useRef } from "react";
import { timing } from "../../theme/tokens";

const TRACKS = { light: "bg-line", dark: "bg-surface/15" } as const;

type MeterProps = {
  /** Share filled, from 0 to 1. */
  value: number;
  color: string;
  /** Track height, as a Tailwind height class. */
  height?: "h-1.5" | "h-2" | "h-3";
  /** "dark" for meters on the dark best-match tile. */
  track?: keyof typeof TRACKS;
  title?: string;
};

/** A rounded bar that fills to its value when it scrolls into view and glides to new values. */
export function Meter({ value, color, height = "h-2", track = "light", title }: MeterProps) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const width = `${Math.max(0, Math.min(1, value)) * 100}%`;
  return (
    <div ref={ref} className={`overflow-hidden rounded-full ${TRACKS[track]} ${height}`} title={title} aria-hidden="true">
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
        initial={{ width: reduce ? width : "0%" }}
        animate={{ width: inView || reduce ? width : "0%" }}
        transition={reduce ? { duration: 0 } : { duration: timing.slow, ease: timing.ease }}
      />
    </div>
  );
}
