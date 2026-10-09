import { motion, useReducedMotion } from "framer-motion";
import type { RankedCareer } from "../../api/client";
import { formatPoints } from "../../lib/format";
import { timing } from "../../theme/tokens";
import { Card } from "../ui/Card";
import { PrismBar } from "./PrismBar";

type TopCareersProps = {
  ranking: RankedCareer[];
  selectedId: string;
  onSelect: (careerId: string) => void;
};

/** The ranked list; a highlight glides to the chosen career. On wide screens it fills the height of the detail beside it. */
export function TopCareers({ ranking, selectedId, onSelect }: TopCareersProps) {
  const reduce = useReducedMotion();
  return (
    <Card
      title="Your top careers"
      description="Ranked by PRISM Score out of 100. Choose one to see why."
      className="lg:absolute lg:inset-0"
    >
      <ul className="scroll-fade -mx-3 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-3 pb-6 pt-1">
        {ranking.map((career) => {
          const selected = career.career_id === selectedId;
          return (
            <li key={career.career_id}>
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => onSelect(career.career_id)}
                className={`relative w-full rounded-xl px-4 py-3 text-left transition-colors ${selected ? "" : "hover:bg-paper/70"}`}
              >
                {selected && (
                  <motion.span
                    layoutId={reduce ? undefined : "top-career-highlight"}
                    className="absolute inset-0 rounded-xl bg-paper ring-1 ring-ink/10"
                    transition={timing.pill}
                    aria-hidden="true"
                  />
                )}
                <span className="relative flex items-center gap-3">
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium transition-colors ${
                      selected ? "bg-ink text-surface" : "bg-paper text-ink/70"
                    }`}
                  >
                    {career.rank}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{career.name}</span>
                    <span className="block truncate text-sm text-ink/60">{career.domain}</span>
                  </span>
                  <span className="text-lg font-semibold tabular-nums tracking-tight">{formatPoints(career.score)}</span>
                </span>
                <span className="relative mt-3 block">
                  <PrismBar points={career.points} score={career.score} size="sm" />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
