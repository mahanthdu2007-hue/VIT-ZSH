import type { SkillPlan } from "../../api/client";
import { Card } from "../ui/Card";

/** §8 timeline: the roadmap placed on calendar years. */
export function Timeline({ plan }: { plan: SkillPlan }) {
  return (
    <Card title="Year by year" description="When each step could happen, starting this year.">
      <ol className="flex flex-col">
        {plan.timeline.map((year) => (
          <li key={year.year} className="flex gap-4 border-l-2 border-line pb-4 pl-4 last:pb-0">
            <span className="w-12 shrink-0 font-heading font-semibold">{year.year}</span>
            <ul className="flex flex-col gap-1">
              {year.steps.map((step, i) => (
                <li key={`${i}-${step}`}>{step}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </Card>
  );
}
