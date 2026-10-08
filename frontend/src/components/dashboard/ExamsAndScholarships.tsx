import type { CareerDetail } from "../../api/client";
import { formatInr } from "../../lib/format";
import { SCHOLARSHIP_PORTAL_URL } from "../../lib/labels";
import { IndicativeTag } from "../ui/Badge";

/** Scholarships and entrance exams for the selected career's suggested route, one tile each. */
export function ExamsAndScholarships({ detail }: { detail: CareerDetail }) {
  return (
    <div className="flex flex-col gap-8">
      <section aria-labelledby="scholarships-heading">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 id="scholarships-heading" className="text-lg">
            Scholarships
          </h3>
          <IndicativeTag />
        </div>
        <p className="mt-1 text-sm text-ink/60">For {detail.pathway.label}, at your family income.</p>
        {detail.scholarships.length > 0 ? (
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {detail.scholarships.map((s) => (
              <li key={s.scholarship_id} className="flex flex-col rounded-lg border border-line bg-surface">
                <div className="flex-1 p-4">
                  <p className="font-medium leading-snug">{s.name}</p>
                  <p className="mt-2 font-heading text-xl">
                    {formatInr(s.amount_inr_per_year)}
                    <span className="font-body text-sm text-ink/60"> a year</span>
                  </p>
                  <p className="mt-2 text-sm text-ink/60">
                    {s.restricted_to ? `Only for ${s.restricted_to}.` : "Open to every eligible student."}
                  </p>
                </div>
                <a
                  href={SCHOLARSHIP_PORTAL_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-b-lg border-t border-line px-4 py-3 text-sm font-medium hover:bg-paper"
                >
                  Apply on National Scholarship Portal
                  <span aria-hidden="true">↗</span>
                  <span className="sr-only"> (opens in a new tab)</span>
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 rounded-lg bg-paper p-4 text-sm text-ink/70">
            No scheme in our list matches this route and family income.
          </p>
        )}
      </section>

      <section aria-labelledby="exams-heading">
        <h3 id="exams-heading" className="text-lg">
          Entrance exams
        </h3>
        {detail.exams.length > 0 ? (
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {detail.exams.map((exam) => (
              <li key={exam.id} className="flex flex-col rounded-lg border border-line p-4">
                <p className="font-medium leading-snug">{exam.name}</p>
                <p className="mt-2 inline-flex self-start rounded-full bg-paper px-2 py-0.5 text-sm">
                  Usually in {exam.typical_month}
                </p>
                <p className="mt-2 text-sm text-ink/60">Source: {exam.source}</p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 rounded-lg bg-paper p-4 text-sm text-ink/70">This route has no entrance exam.</p>
        )}
      </section>
    </div>
  );
}
