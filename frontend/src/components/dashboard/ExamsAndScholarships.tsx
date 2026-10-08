import type { CareerDetail } from "../../api/client";
import { formatInr } from "../../lib/format";
import { SCHOLARSHIP_PORTAL_URL } from "../../lib/labels";
import { ExternalLink } from "../ui/ExternalLink";
import { IndicativeTag } from "../ui/Badge";
import { Card } from "../ui/Card";

/** Entrance exams and scholarship schemes for the selected career's suggested route. */
export function ExamsAndScholarships({ detail }: { detail: CareerDetail }) {
  return (
    <Card title="Exams and scholarships" description={`For the suggested route: ${detail.pathway.label}.`}>
      <div className="grid gap-6 md:grid-cols-2">
        <section>
          <h3 className="text-base">Entrance exams</h3>
          {detail.exams.length > 0 ? (
            <ul className="mt-2 flex flex-col gap-2">
              {detail.exams.map((exam) => (
                <li key={exam.id}>
                  <span className="font-medium">{exam.name}</span>
                  <span className="block text-sm text-ink/70">
                    Usually in {exam.typical_month}. Source: {exam.source}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-ink/70">This route has no entrance exam.</p>
          )}
        </section>
        <section>
          <h3 className="flex flex-wrap items-center gap-2 text-base">
            Scholarships <IndicativeTag />
          </h3>
          {detail.scholarships.length > 0 ? (
            <ul className="mt-2 flex flex-col gap-2">
              {detail.scholarships.map((s) => (
                <li key={s.scholarship_id}>
                  <ExternalLink href={SCHOLARSHIP_PORTAL_URL}>{s.name}</ExternalLink>: up to {formatInr(s.amount_inr_per_year)} a year
                  <span className="block text-sm text-ink/70">
                    {s.restricted_to ? `Only for ${s.restricted_to}.` : "Open to every eligible student."}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-ink/70">No scheme in our list matches this route and family income.</p>
          )}
          <p className="mt-3 text-sm text-ink/70">
            Apply on the government&apos;s{" "}
            <ExternalLink href={SCHOLARSHIP_PORTAL_URL}>National Scholarship Portal</ExternalLink>.
          </p>
        </section>
      </div>
    </Card>
  );
}
