import { LayoutGroup, MotionConfig, motion, useReducedMotion } from "framer-motion";
import type { CareerChange, RankedCareer } from "../../api/client";
import { formatPoints } from "../../lib/format";
import { COMPONENTS } from "../../lib/labels";
import { componentColors } from "../../theme/tokens";
import { PrismBar } from "../dashboard/PrismBar";

const SHOWN_DELTA = 0.05;
// §15's single motion moment: rows re-order and PrismBar segments re-flow together.
const REFLOW = { layout: { type: "spring", duration: 0.6, bounce: 0.15 } } as const;

const signed = (value: number) => `${value > 0 ? "+" : value < 0 ? "−" : ""}${formatPoints(Math.abs(value))}`;

function RankChange({ change }: { change: CareerChange | undefined }) {
  if (!change || change.rank_before === null || change.rank_change === null) {
    return change && change.rank_before === null ? <span className="text-sm font-medium">Newly affordable</span> : null;
  }
  if (change.rank_change === 0) return <span className="text-sm text-ink/60">Same place</span>;
  const up = change.rank_change > 0;
  return (
    <span className={`text-sm font-medium ${up ? "text-financialFit" : "text-danger"}`}>
      <span aria-hidden="true">{up ? "↑" : "↓"}</span> {up ? "Up" : "Down"} {Math.abs(change.rank_change)}
      <span className="font-normal text-ink/60"> from #{change.rank_before}</span>
    </span>
  );
}

function PointDeltas({ change }: { change: CareerChange }) {
  const moved = COMPONENTS.filter((c) => Math.abs(change.point_deltas[c.key] ?? 0) >= SHOWN_DELTA);
  if (moved.length === 0) return null;
  return (
    <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-sm">
      {moved.map((c) => (
        <li key={c.key} className="flex items-center gap-1.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: componentColors[c.key] }}
            aria-hidden="true"
          />
          {c.label} {signed(change.point_deltas[c.key] ?? 0)}
        </li>
      ))}
    </ul>
  );
}

type WhatIfRankingProps = {
  ranking: RankedCareer[];
  changes: CareerChange[] | null;
};

/** The re-ranked top careers with rank arrows, point deltas and §11 reason sentences. */
export function WhatIfRanking({ ranking, changes }: WhatIfRankingProps) {
  // Framer's reducedMotion="user" still moves layout projections, so turn the layout animation off entirely.
  const animate = !useReducedMotion();
  const byId = new Map(changes?.map((c) => [c.career_id, c]));
  const shownIds = new Set(ranking.map((r) => r.career_id));
  const droppedOut = (changes ?? []).filter(
    (c) => c.rank_before !== null && c.rank_before <= ranking.length && !shownIds.has(c.career_id),
  );

  return (
    <MotionConfig transition={REFLOW}>
      <LayoutGroup>
        <ol className="flex flex-col gap-2">
          {ranking.map((career) => {
            const change = byId.get(career.career_id);
            return (
              <motion.li
                layout={animate}
                key={career.career_id}
                className="rounded-lg border border-line bg-surface px-3 py-2"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span>
                    <span className="mr-2 text-sm text-ink/60">#{career.rank}</span>
                    <span className="font-medium">{career.name}</span>
                  </span>
                  <span className="flex items-baseline gap-3">
                    <RankChange change={change} />
                    <span className="font-heading text-lg font-semibold">{formatPoints(career.score)}</span>
                  </span>
                </div>
                <div className="mt-2">
                  <PrismBar points={career.points} score={career.score} size="sm" animated={animate} />
                </div>
                {change && change.score_delta !== 0 && (
                  <p className="mt-1 text-sm text-ink/70">
                    Score {signed(change.score_delta)} (was {formatPoints(change.score_before)})
                  </p>
                )}
                {change && <PointDeltas change={change} />}
                {change?.reason && <p className="mt-2 rounded bg-paper p-2 text-sm">{change.reason}</p>}
              </motion.li>
            );
          })}
        </ol>
      </LayoutGroup>
      {droppedOut.length > 0 && (
        <div className="mt-4">
          <h3 className="text-base">Moved out of this list</h3>
          <ul className="mt-2 flex flex-col gap-2 text-sm">
            {droppedOut.map((c) => (
              <li key={c.career_id} className="rounded-lg border border-line p-2">
                <span className="font-medium">{c.name}</span>{" "}
                {c.status_after === "feasible"
                  ? `now #${c.rank_after}, score ${formatPoints(c.score_after)}`
                  : "now needs scholarships or a loan to afford"}
                {c.reason && <span className="mt-1 block">{c.reason}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </MotionConfig>
  );
}
