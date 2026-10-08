import type { SkillPlan } from "../../api/client";
import { Card } from "../ui/Card";

/** §8 timeline: the roadmap placed on calendar years, one tile per year. */
export function Timeline({ plan }: { plan: SkillPlan }) {
  const thisYear = plan.timeline[0]?.year;
  return (
    <Card title="Year by year" description="When each step could happen, starting this year.">
      <ol className="flex flex-col gap-3">
        {plan.timeline.map((year, index) => (
          <li
            key={year.year}
            className={`flex gap-4 rounded-lg border p-4 ${year.year === thisYear ? "border-ink/30 bg-paper" : "border-line"}`}
          >
            <div className="w-16 shrink-0">
              <p className="font-heading text-lg leading-none">{year.year}</p>
              <p className="mt-1 text-sm text-ink/60">{index === 0 ? "This year" : `Year ${index + 1}`}</p>
            </div>
            <ul className="flex flex-1 flex-col gap-1.5 border-l border-line pl-4">
              {year.steps.map((step, i) => (
                <li key={`${i}-${step}`} className="leading-snug">
                  {step}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </Card>
  );
}
