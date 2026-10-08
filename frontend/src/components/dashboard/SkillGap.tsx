import type { SkillPlan } from "../../api/client";
import { Card } from "../ui/Card";

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
          <ul className="flex flex-col gap-3">
            {gaps.map((g) => (
              <li key={g.skill}>
                <div className="flex justify-between gap-2 text-sm">
                  <span className="font-medium">{g.skill}</span>
                  <span>
                    now {percent(g.current)}, needs {percent(g.level_required)}
                  </span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-line" title={`Gap ${percent(g.gap)} of 100`}>
                  <div className="h-full rounded-full bg-studentFit" style={{ width: `${(g.gap / largest) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
          {learningOrder.length > 0 && (
            <div className="mt-6">
              <h3 className="text-base">What to learn first</h3>
              <ol className="mt-2 list-decimal pl-5">
                {learningOrder.map((step, i) => (
                  <li key={`${i}-${step.text}`}>{step.text}</li>
                ))}
              </ol>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
