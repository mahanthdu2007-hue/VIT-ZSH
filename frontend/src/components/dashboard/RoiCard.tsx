import type { CareerDetail } from "../../api/client";
import { formatInr } from "../../lib/format";
import { IndicativeTag } from "../ui/Badge";
import { Card } from "../ui/Card";
import { CountUp } from "../ui/CountUp";

const INR_PER_LAKH = 100_000;

/** §10 return on the course cost: effective cost, starting pay and break-even years, as three large figures. */
export function RoiCard({ detail }: { detail: CareerDetail }) {
  const { roi } = detail;
  const [entryLow, entryHigh] = detail.career.salary_inr_lpa.entry;
  const sharePercent = Math.round(roi.salary_share * 100);
  return (
    <Card title="Is the course worth the cost?" actions={<IndicativeTag />}>
      <dl className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl bg-paper p-5">
          <dt className="text-sm text-ink/60">Course cost after expected scholarships</dt>
          <dd className="mt-2 text-xl font-semibold tracking-tight">
            <CountUp value={roi.effective_cost} format={formatInr} />
          </dd>
        </div>
        <div className="rounded-xl bg-paper p-5">
          <dt className="text-sm text-ink/60">Starting pay a year</dt>
          <dd className="mt-2 text-xl font-semibold tracking-tight">
            {formatInr(entryLow * INR_PER_LAKH)} to {formatInr(entryHigh * INR_PER_LAKH)}
          </dd>
        </div>
        <div className="rounded-xl bg-ink p-5 text-surface">
          <dt className="text-sm text-surface/60">Years to earn the cost back</dt>
          <dd className="mt-2 text-xl font-semibold tracking-tight">
            <CountUp value={roi.break_even_years} format={(v) => v.toFixed(1)} />
          </dd>
        </div>
      </dl>
      <p className="mt-4 text-sm text-ink/60">Assumes {sharePercent}% of starting pay goes to paying back the course.</p>
    </Card>
  );
}
