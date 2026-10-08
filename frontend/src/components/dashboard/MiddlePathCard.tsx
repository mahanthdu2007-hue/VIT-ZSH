import type { MiddlePath } from "../../api/client";
import { formatSignedHundredths } from "../../lib/format";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";

type MiddlePathCardProps = {
  middlePath: MiddlePath | null;
  careerName: (careerId: string) => string;
  onSelect: (careerId: string) => void;
};

const outOf100 = (utility: number) => (utility * 100).toFixed(1);

type SideProps = {
  title: string;
  measure: string;
  utility: number;
  gain: number;
  change: number;
  ownTopId: string;
  middleId: string;
  careerName: (careerId: string) => string;
};

function Side({ title, measure, utility, gain, change, ownTopId, middleId, careerName }: SideProps) {
  return (
    <div className="flex-1 rounded-lg border border-line p-3">
      <h4 className="font-medium">{title}</h4>
      <p className="mt-1">
        {measure}: <span className="font-medium">{outOf100(utility)}</span> of 100
      </p>
      <p className="mt-1 text-sm">
        <span className="font-medium">{formatSignedHundredths(gain)}</span> compared with a typical affordable career.
      </p>
      <p className="mt-1 text-sm text-ink/70">
        {ownTopId === middleId
          ? "This is also their own first choice, so they give up nothing."
          : `${formatSignedHundredths(change)} compared with their own first choice, ${careerName(ownTopId)}.`}
      </p>
    </div>
  );
}

/** §7.6 Nash bargaining middle path, with what each side gains. */
export function MiddlePathCard({ middlePath, careerName, onSelect }: MiddlePathCardProps) {
  if (!middlePath) {
    return (
      <Card title="A middle path for the family">
        <p>There are no affordable careers to compare yet, so no middle path could be found.</p>
      </Card>
    );
  }
  const name = careerName(middlePath.career_id);
  return (
    <Card
      title="A middle path for the family"
      description={
        middlePath.method === "nash"
          ? "Of the affordable careers, this one gives the student and the parents the best gain together over a typical career."
          : "No career did better than typical for both sides, so this is the one where the less happy side is happiest."
      }
    >
      <p className="font-heading text-xl font-semibold">{name}</p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
        <Side
          title="What the student gains"
          measure="Student Fit"
          utility={middlePath.u_s}
          gain={middlePath.student_gain}
          change={middlePath.student_change}
          ownTopId={middlePath.student_top_career_id}
          middleId={middlePath.career_id}
          careerName={careerName}
        />
        <Side
          title="What the parents gain"
          measure="Parent Alignment"
          utility={middlePath.u_p}
          gain={middlePath.parent_gain}
          change={middlePath.parent_change}
          ownTopId={middlePath.parent_top_career_id}
          middleId={middlePath.career_id}
          careerName={careerName}
        />
      </div>
      <Button variant="secondary" className="mt-4" onClick={() => onSelect(middlePath.career_id)}>
        See why {name} fits
      </Button>
    </Card>
  );
}
