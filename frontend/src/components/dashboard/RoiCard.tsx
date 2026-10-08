import type { CareerDetail } from "../../api/client";
import { formatInr } from "../../lib/format";
import { IndicativeTag } from "../ui/Badge";
import { Card } from "../ui/Card";

const INR_PER_LAKH = 100_000;

/** §10 return on the course cost: effective cost, starting pay and break-even years. */
export function RoiCard({ detail }: { detail: CareerDetail }) {
  const { roi } = detail;
  const [entryLow, entryHigh] = detail.career.salary_inr_lpa.entry;
  const sharePercent = Math.round(roi.salary_share * 100);
  return (
    <Card title="Is the course worth the cost?" actions={<IndicativeTag />}>
      <dl className="grid gap-4 sm:grid-cols-3">
        <div>
          <dt className="text-sm text-ink/70">Course cost after expected scholarships</dt>
          <dd className="font-heading text-xl font-semibold">{formatInr(roi.effective_cost)}</dd>
        </div>
        <div>
          <dt className="text-sm text-ink/70">Starting pay a year</dt>
          <dd className="font-heading text-xl font-semibold">
            {formatInr(entryLow * INR_PER_LAKH)} to {formatInr(entryHigh * INR_PER_LAKH)}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-ink/70">Years to earn the cost back</dt>
          <dd className="font-heading text-xl font-semibold">{roi.break_even_years.toFixed(1)}</dd>
        </div>
      </dl>
      <p className="mt-4 rounded-lg bg-paper p-3 text-sm">
        This assumes {sharePercent}% of a typical starting pay of {formatInr(roi.entry_mid_inr)} a year goes towards
        paying back the course cost. Real savings vary from family to family.
      </p>
    </Card>
  );
}
