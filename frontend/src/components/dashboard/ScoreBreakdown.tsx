import type { CareerDetail } from "../../api/client";
import { formatPoints } from "../../lib/format";
import { COMPONENTS } from "../../lib/labels";
import { componentColors } from "../../theme/tokens";

/** The five PRISM Score components: points earned of the maximum, with what each one means. */
export function ScoreBreakdown({ detail }: { detail: CareerDetail }) {
  const { points, score } = detail.score;
  return (
    <section aria-labelledby="breakdown-heading">
      <h3 id="breakdown-heading" className="text-lg">
        How the score adds up
      </h3>
      <ul className="mt-3 flex flex-col gap-3">
        {COMPONENTS.map((c) => {
          const earned = points[c.key] ?? 0;
          return (
            <li key={c.key}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="flex items-center gap-2 font-medium">
                  <span className="h-3 w-3 rounded-sm" style={{ backgroundColor: componentColors[c.key] }} aria-hidden="true" />
                  {c.label}
                </span>
                <span className="text-sm">
                  <span className="font-medium">{formatPoints(earned)}</span> of {c.max}
                </span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-line" aria-hidden="true">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${(earned / c.max) * 100}%`, backgroundColor: componentColors[c.key] }}
                />
              </div>
              <p className="mt-1 text-sm text-ink/70">{c.meaning}</p>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 flex justify-between border-t border-line pt-3 font-medium">
        <span>PRISM Score</span>
        <span>{formatPoints(score)} of 100</span>
      </p>
    </section>
  );
}
