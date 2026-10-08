import type { CareerDetail, StretchOption } from "../../api/client";
import { formatInr } from "../../lib/format";
import { IndicativeTag } from "../ui/Badge";
import { Card } from "../ui/Card";
import { AidOptions } from "./AidOptions";

type StretchOptionsProps = {
  options: StretchOption[];
  details: Record<string, CareerDetail>;
  careerName: (careerId: string) => string;
};

/** §7.9 careers that suit the student but cost more than the family can cover, with ways to make them possible. */
export function StretchOptions({ options, details, careerName }: StretchOptionsProps) {
  return (
    <Card
      title="Stretch options with aid"
      description="Careers that suit the student well but cost more than the budget and loan plan allow. They are not ruled out."
    >
      {options.length === 0 ? (
        <p>Every career that suits the student well fits within the budget and loan plan, so nothing needs extra aid.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {options.map((option) => (
            <li key={option.career_id} className="rounded-lg border border-line p-3 sm:p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h4 className="font-heading text-lg font-semibold">{careerName(option.career_id)}</h4>
                <span className="flex flex-wrap items-center gap-2">
                  <span>
                    Funding gap <span className="font-medium">{formatInr(option.funding_gap)}</span>
                  </span>
                  <IndicativeTag />
                </span>
              </div>
              <p className="mt-1 text-sm text-ink/70">
                Student Fit {(option.student_fit * 100).toFixed(1)} of 100, among the best matches for the student.
              </p>
              <AidOptions option={option} detail={details[option.career_id]} careerName={careerName} />
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
