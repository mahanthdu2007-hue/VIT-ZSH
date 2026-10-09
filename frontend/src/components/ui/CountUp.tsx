import { animate, useInView, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";
import { timing } from "../../theme/tokens";

type CountUpProps = {
  /** The engine's value; the count always lands exactly on it. */
  value: number;
  format: (value: number) => string;
  className?: string;
};

/** A number that rolls up to its value when it first scrolls into view, and rolls to each new value after that. */
export function CountUp({ value, format, className }: CountUpProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const shown = useRef(0);
  const formatRef = useRef(format);
  formatRef.current = format;

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const paint = (current: number) => {
      shown.current = current;
      element.textContent = formatRef.current(current);
    };
    if (reduce) {
      paint(value);
      return;
    }
    if (!inView) return;
    const controls = animate(shown.current, value, { duration: timing.slow, ease: timing.ease, onUpdate: paint });
    return () => controls.stop();
  }, [value, inView, reduce]);

  return (
    <span className={className}>
      <span ref={ref} aria-hidden="true" className="tabular-nums">
        {format(reduce ? value : 0)}
      </span>
      <span className="sr-only">{format(value)}</span>
    </span>
  );
}
