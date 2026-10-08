import type { CareerDetail, StretchOption } from "../../api/client";
import { formatInr } from "../../lib/format";

type AidOptionsProps = {
  option: StretchOption;
  detail: CareerDetail | undefined;
  careerName: (careerId: string) => string;
};

/** Ways to close a funding gap: scholarships, cheaper pathways and nearby careers that already fit the budget. */
export function AidOptions({ option, detail, careerName }: AidOptionsProps) {
  const pathwayLabel = (id: string) => detail?.career.pathways.find((p) => p.id === id)?.label ?? id;
  return (
    <div className="mt-3 grid gap-4 md:grid-cols-3">
      <div>
        <h5 className="font-medium">Scholarships</h5>
        {option.scholarships.length > 0 ? (
          <ul className="mt-1 flex flex-col gap-2 text-sm">
            {option.scholarships.map((s) => (
              <li key={s.scholarship_id}>
                <span className="font-medium">{s.name}</span>: up to {formatInr(s.amount_inr_per_year)} a year
                {s.restricted_to && <span className="block text-ink/70">Only for {s.restricted_to}.</span>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-ink/70">No scheme in our list matches this pathway and income.</p>
        )}
      </div>
      <div>
        <h5 className="font-medium">Cheaper ways in</h5>
        {option.cheaper_pathways.length > 0 ? (
          <ul className="mt-1 flex flex-col gap-2 text-sm">
            {option.cheaper_pathways.map((p) => (
              <li key={p.pathway_id}>
                <span className="font-medium">{pathwayLabel(p.pathway_id)}</span>: about {formatInr(p.effective_cost)}
                {p.funding_gap > 0 ? `, still ${formatInr(p.funding_gap)} short` : ", fits the budget"}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-ink/70">This is already the cheapest pathway for your stage.</p>
        )}
      </div>
      <div>
        <h5 className="font-medium">Similar careers that fit the budget</h5>
        {option.adjacent_feasible.length > 0 ? (
          <ul className="mt-1 list-disc pl-5 text-sm">
            {option.adjacent_feasible.map((id) => (
              <li key={id}>{careerName(id)}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-sm text-ink/70">None of the closely related careers fit the budget either.</p>
        )}
      </div>
    </div>
  );
}
