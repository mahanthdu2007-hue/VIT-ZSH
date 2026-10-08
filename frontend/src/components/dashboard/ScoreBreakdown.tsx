import type { CareerDetail } from "../../api/client";
import { formatPoints } from "../../lib/format";
import { COMPONENTS } from "../../lib/labels";
import { componentColors } from "../../theme/tokens";
import { Meter } from "../ui/Meter";

/** The five PRISM Score components: points earned of the maximum, with what each one means. */
export function ScoreBreakdown({ detail }: { detail: CareerDetail }) {
  const { points, score } = detail.score;
  return (
    <section aria-labelledby="breakdown-heading">
      <h3 id="breakdown-heading" className="text-lg">
        How the score adds up
      </h3>
      <ul className="mt-4 grid gap-x-8 gap-y-5 sm:grid-cols-2">
        {COMPONENTS.map((c) => {
          const earned = points[c.key] ?? 0;
          return (
            <li key={c.key} className="flex flex-col gap-1.5">
              <div className="flex items-baseline justify-between gap-3">
                <span className="flex items-center gap-2 font-medium">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: componentColors[c.key] }} aria-hidden="true" />
                  {c.label}
                </span>
                <span className="text-sm tabular-nums">
                  <span className="font-medium">{formatPoints(earned)}</span>
                  <span className="text-ink/50"> of {c.max}</span>
                </span>
              </div>
              <Meter value={earned / c.max} color={componentColors[c.key]} />
              <p className="text-sm leading-snug text-ink/60">{c.meaning}</p>
            </li>
          );
        })}
        <li className="flex items-center justify-between rounded-xl bg-paper px-4 py-3 font-medium">
          <span>PRISM Score</span>
          <span className="tabular-nums">{formatPoints(score)} of 100</span>
        </li>
      </ul>
    </section>
  );
}
