import { RadioGroup } from "../ui/Choice";
import type { StepProps } from "./types";

// Five plain levels mapped onto the §6 0–100 self-rating.
const LEVELS = [
  { value: "0", label: "None" },
  { value: "25", label: "Beginner" },
  { value: "50", label: "Okay" },
  { value: "75", label: "Good" },
  { value: "100", label: "Strong" },
];

export function SkillsStep({ draft, update, errors, questions }: StepProps) {
  return (
    <div className="flex flex-col gap-6">
      <p className="text-ink/80">Rate yourself honestly. Your ratings shape the skill gaps and the learning plan for each career.</p>
      {(questions.skills ?? []).map((skill) => (
        <RadioGroup
          key={skill}
          legend={skill}
          name={`skill-${skill}`}
          compact
          options={LEVELS}
          value={draft.self_rated_skills[skill] === undefined ? null : String(draft.self_rated_skills[skill])}
          onChange={(value) => update({ self_rated_skills: { ...draft.self_rated_skills, [skill]: Number(value) } })}
          error={errors[skill]}
        />
      ))}
    </div>
  );
}
