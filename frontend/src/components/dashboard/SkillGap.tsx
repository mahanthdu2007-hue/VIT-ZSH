import type { SkillPlan } from "../../api/client";
import { colors } from "../../theme/tokens";
import { Card } from "../ui/Card";
import { Meter } from "../ui/Meter";

const percent = (value: number) => Math.round(value * 100);

/** §8 skill gaps sorted by size, and the order to learn them in. */
export function SkillGap({ plan }: { plan: SkillPlan }) {
  const gaps = plan.gaps.filter((g) => g.gap > 0);
  const learningOrder = plan.roadmap.filter((step) => step.kind === "learning");
  const largest = Math.max(...gaps.map((g) => g.gap), 0);

  return (
    <Card
      title="Skills to build"
      description="Each gap is how far the current level is below what the career needs, weighted by how much the skill matters."
    >
      {gaps.length === 0 ? (
        <p>Your current level already meets every skill this career needs. Keep practising to stay there.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-4">
            {gaps.map((g) => (
              <li key={g.skill} className="flex flex-col gap-1.5">
                <div className="flex justify-between gap-2 text-sm">
                  <span className="font-medium">{g.skill}</span>
                  <span className="tabular-nums text-ink/60">
                    now {percent(g.current)}, needs {percent(g.level_required)}
                  </span>
                </div>
                <Meter value={g.gap / largest} color={colors.studentFit} title={`Gap ${percent(g.gap)} of 100`} />
              </li>
            ))}
          </ul>
          {learningOrder.length > 0 && (
            <div className="mt-auto pt-8">
              <h3 className="text-base">What to learn first</h3>
              <ol className="mt-3 flex flex-col gap-2">
                {learningOrder.map((step, i) => (
                  <li key={`${i}-${step.text}`} className="flex items-start gap-3 rounded-xl bg-paper px-4 py-3 text-sm">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-studentFit text-sm font-medium text-surface">
                      {i + 1}
                    </span>
                    <span className="pt-0.5">{step.text}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
