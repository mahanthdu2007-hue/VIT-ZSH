import type { Swot, SwotItem } from "../../api/client";
import { formatInr } from "../../lib/format";
import { CONFLICT_DIMENSIONS, DIMENSION_LABELS } from "../../lib/labels";
import { Card } from "../ui/Card";

const outOf100 = (value: number | null | undefined) => Math.round((value ?? 0) * 100);

/** One §9 item in plain words; the wording depends on the item's kind. */
function describe(item: SwotItem): string {
  switch (item.kind) {
    case "dimension":
      return `${DIMENSION_LABELS[item.label] ?? item.label}: ${outOf100(item.value)} of 100`;
    case "skill_gap":
      return `${item.label}: gap of ${outOf100(item.value)}`;
    case "city_demand":
      return `${item.label}: hiring demand ${outOf100(item.value)} of 100`;
    case "scholarship":
      return `${item.label}: up to ${formatInr(item.value ?? 0)} a year`;
    case "exam":
      return item.value === 0 ? `${item.label}: this month` : `${item.label}: in about ${item.value} months`;
    case "disruption":
      return `New technology may change ${item.label} work: ${outOf100(item.value)} of 100`;
    case "funding_gap":
      return `${item.label} costs ${formatInr(item.value ?? 0)} more than the budget and loan plan`;
    case "conflict":
      return `Biggest family difference: ${(CONFLICT_DIMENSIONS[item.label]?.label ?? item.label).toLowerCase()}`;
    default:
      return item.label;
  }
}

const QUADRANTS: { key: keyof Swot; title: string; empty: string }[] = [
  { key: "strengths", title: "Strengths", empty: "No clear strengths stood out yet." },
  { key: "weaknesses", title: "Weaknesses", empty: "No skill gaps for this career." },
  { key: "opportunities", title: "Opportunities", empty: "No opportunities found in our data." },
  { key: "threats", title: "Threats", empty: "No major threats found." },
];

/** §9 SWOT for the top career, as a 2×2 grid. */
export function SwotGrid({ swot, topCareerName }: { swot: Swot | null; topCareerName: string | undefined }) {
  return (
    <Card
      title="Strengths, weaknesses, opportunities and threats"
      description={topCareerName ? `Worked out for your top career, ${topCareerName}.` : undefined}
    >
      {swot ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {QUADRANTS.map((q) => {
            const items = swot[q.key];
            return (
              <section key={q.key} className="rounded-lg border border-line bg-paper p-3">
                <h3 className="text-base">{q.title}</h3>
                {items.length > 0 ? (
                  <ul className="mt-1 flex flex-col gap-1 text-sm">
                    {items.map((item, i) => (
                      <li key={`${i}-${item.kind}-${item.label}`}>{describe(item)}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm text-ink/70">{q.empty}</p>
                )}
              </section>
            );
          })}
        </div>
      ) : (
        <p>There is no affordable top career yet, so there is no SWOT to show.</p>
      )}
    </Card>
  );
}
