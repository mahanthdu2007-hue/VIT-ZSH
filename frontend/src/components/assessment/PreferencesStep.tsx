import type { CityId, Level } from "../../api/client";
import { CITY_IDS, CITY_NAMES, LEVEL_LABELS, STUDENT_RISK_HINTS } from "../../lib/labels";
import { CheckboxGroup, RadioGroup, YES_NO } from "../ui/Choice";
import type { StepProps } from "./types";

const yesNo = (value: boolean | null) => (value === null ? null : value ? "yes" : "no");

export function PreferencesStep({ draft, update, errors }: StepProps) {
  return (
    <div className="flex flex-col gap-6">
      <CheckboxGroup<CityId>
        legend="Which cities would you like to work in?"
        hint="Leave empty if any city is fine."
        options={CITY_IDS.map((id) => ({ value: id, label: CITY_NAMES[id] }))}
        value={draft.preferred_cities}
        onChange={(preferred_cities) => update({ preferred_cities })}
      />
      <RadioGroup
        legend="Would you move to another city for study or work?"
        name="willing_to_relocate"
        options={YES_NO}
        value={yesNo(draft.willing_to_relocate)}
        onChange={(value) => update({ willing_to_relocate: value === "yes" })}
        error={errors.willing_to_relocate}
      />
      <RadioGroup
        legend="Do you want to study further after your first degree?"
        hint="For example a master's degree or a specialisation."
        name="wants_higher_studies"
        options={YES_NO}
        value={yesNo(draft.wants_higher_studies)}
        onChange={(value) => update({ wants_higher_studies: value === "yes" })}
        error={errors.wants_higher_studies}
      />
      <RadioGroup<Level>
        legend="How comfortable are you with risk in your career?"
        name="risk_tolerance"
        options={(Object.keys(LEVEL_LABELS) as Level[]).map((level) => ({
          value: level,
          label: LEVEL_LABELS[level],
          hint: STUDENT_RISK_HINTS[level],
        }))}
        value={draft.risk_tolerance}
        onChange={(risk_tolerance) => update({ risk_tolerance })}
        error={errors.risk_tolerance}
      />
    </div>
  );
}
