import { RadioGroup } from "../ui/Choice";
import type { StepErrors } from "./steps";

type LikertStepProps = {
  intro: string;
  items: { id: string; prompt: string }[];
  scale: string[];
  answers: Record<string, number>;
  onChange: (answers: Record<string, number>) => void;
  errors: StepErrors;
};

/** Statements rated on a 1–5 scale, each with its own words for the scale points. */
export function LikertStep({ intro, items, scale, answers, onChange, errors }: LikertStepProps) {
  return (
    <div className="flex flex-col gap-6">
      <p className="text-ink/80">{intro}</p>
      {items.map((item) => (
        <RadioGroup
          key={item.id}
          legend={item.prompt}
          name={item.id}
          compact
          options={scale.map((label, index) => ({ value: String(index + 1), label }))}
          value={answers[item.id] === undefined ? null : String(answers[item.id])}
          onChange={(value) => onChange({ ...answers, [item.id]: Number(value) })}
          error={errors[item.id]}
        />
      ))}
    </div>
  );
}
