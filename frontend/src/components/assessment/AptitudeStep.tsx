import type { QuestionSet } from "../../api/client";
import { RadioGroup } from "../ui/Choice";
import type { StepProps } from "./types";

type Dimension = QuestionSet["aptitude"][number]["dimension"];

const SECTIONS: Record<Dimension, string> = {
  numerical: "Working with numbers",
  logical: "Spotting patterns and logic",
  verbal: "Understanding words",
  spatial: "Picturing shapes",
};

export function AptitudeStep({ draft, update, errors, questions }: StepProps) {
  return (
    <div className="flex flex-col gap-8">
      <p className="text-ink/80">There is no time limit. If you are not sure, make your best guess.</p>
      {(Object.keys(SECTIONS) as Dimension[]).map((dimension) => (
        <section key={dimension} className="flex flex-col gap-5">
          <h3 className="text-lg">{SECTIONS[dimension]}</h3>
          {questions.aptitude
            .filter((q) => q.dimension === dimension)
            .map((q) => (
              <RadioGroup
                key={q.id}
                legend={q.prompt}
                name={q.id}
                compact
                options={q.options.map((option, index) => ({ value: String(index), label: option }))}
                value={draft.aptitude_answers[q.id] === undefined ? null : String(draft.aptitude_answers[q.id])}
                onChange={(value) => update({ aptitude_answers: { ...draft.aptitude_answers, [q.id]: Number(value) } })}
                error={errors[q.id]}
              />
            ))}
        </section>
      ))}
    </div>
  );
}
