import type { MiddlePath } from "../../api/client";
import { formatSignedHundredths } from "../../lib/format";
import { componentColors } from "../../theme/tokens";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { CountUp } from "../ui/CountUp";
import { Meter } from "../ui/Meter";

type MiddlePathCardProps = {
  middlePath: MiddlePath | null;
  careerName: (careerId: string) => string;
  onSelect: (careerId: string) => void;
};

type SideProps = {
  title: string;
  measure: string;
  color: string;
  utility: number;
  gain: number;
  change: number;
  ownTopId: string;
  middleId: string;
  careerName: (careerId: string) => string;
};

function Side({ title, measure, color, utility, gain, change, ownTopId, middleId, careerName }: SideProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl bg-paper p-5">
      <h3 className="text-base">{title}</h3>
      <p>
        <CountUp value={utility * 100} format={(v) => v.toFixed(1)} className="text-xl font-semibold tracking-tight" />
        <span className="text-sm text-ink/60"> of 100 {measure}</span>
      </p>
      <Meter value={utility} color={color} />
      <p className="text-sm">
        <span className="font-medium">{formatSignedHundredths(gain)}</span> compared with a typical affordable career.
      </p>
      <p className="mt-auto text-sm text-ink/60">
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
      <p className="text-xl font-semibold leading-tight tracking-tight sm:text-2xl">{name}</p>
      <div className="mt-6 grid flex-1 gap-3 sm:grid-cols-2">
        <Side
          title="What the student gains"
          measure="Student Fit"
          color={componentColors.student_fit}
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
          color={componentColors.parent_alignment}
          utility={middlePath.u_p}
          gain={middlePath.parent_gain}
          change={middlePath.parent_change}
          ownTopId={middlePath.parent_top_career_id}
          middleId={middlePath.career_id}
          careerName={careerName}
        />
      </div>
      <Button className="mt-6 self-start" onClick={() => onSelect(middlePath.career_id)}>
        See why {name} fits
      </Button>
    </Card>
  );
}
