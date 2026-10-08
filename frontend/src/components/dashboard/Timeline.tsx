import type { SkillPlan } from "../../api/client";
import { Card } from "../ui/Card";

/** §8 timeline: the roadmap placed on calendar years, one tile per year in a row that swipes sideways on small screens. */
export function Timeline({ plan }: { plan: SkillPlan }) {
  return (
    <Card title="Year by year" description="When each step could happen, starting this year. Swipe or scroll sideways for later years.">
      <ol className="no-scrollbar -mx-6 grid snap-x snap-mandatory auto-cols-[minmax(theme(spacing.56),1fr)] grid-flow-col gap-3 overflow-x-auto px-6 pb-1 sm:-mx-8 sm:px-8">
        {plan.timeline.map((year, index) => (
          <li
            key={year.year}
            className={`flex snap-start flex-col rounded-xl p-5 ${index === 0 ? "bg-ink text-surface" : "bg-paper"}`}
          >
            <p className={`text-sm font-medium ${index === 0 ? "text-surface/60" : "text-ink/50"}`}>
              {index === 0 ? "This year" : `Year ${index + 1}`}
            </p>
            <p className="mt-1 text-xl font-semibold tracking-tight">{year.year}</p>
            <ul className={`mt-4 flex flex-col gap-2 border-t pt-4 text-sm ${index === 0 ? "border-surface/15" : "border-ink/10"}`}>
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
