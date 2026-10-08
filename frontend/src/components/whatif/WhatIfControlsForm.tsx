import type { CityId, Level, LoanWillingness, TopPriority } from "../../api/client";
import { formatInr } from "../../lib/format";
import { CITY_IDS, CITY_NAMES, LEVEL_LABELS, LOAN_LABELS, PRIORITY_LABELS } from "../../lib/labels";
import type { WhatIfControls } from "../../lib/whatif";
import { RadioGroup, YES_NO, type Option } from "../ui/Choice";
import { Field, Select } from "../ui/Field";
import { MoneyInput } from "../ui/MoneyInput";

const BUDGET_STEP = 10_000;
const BUDGET_SLIDER_MIN_MAX = 20_00_000;

const options = <T extends string>(labels: Record<T, string>): Option<T>[] =>
  (Object.keys(labels) as T[]).map((value) => ({ value, label: labels[value] }));

const LOAN_OPTIONS = options<LoanWillingness>(LOAN_LABELS);
const LEVEL_OPTIONS = options<Level>(LEVEL_LABELS);
const PRIORITY_OPTIONS = options<TopPriority>(PRIORITY_LABELS);

type WhatIfControlsFormProps = {
  original: WhatIfControls;
  value: WhatIfControls;
  onChange: (value: WhatIfControls) => void;
};

/** The §11 What-If inputs. Each change is sent to the engine after a short pause. */
export function WhatIfControlsForm({ original, value, onChange }: WhatIfControlsFormProps) {
  const set = <K extends keyof WhatIfControls>(key: K, next: WhatIfControls[K]) => onChange({ ...value, [key]: next });
  const sliderMax = Math.max(BUDGET_SLIDER_MIN_MAX, Math.ceil((original.budget * 2) / BUDGET_STEP) * BUDGET_STEP);
  const yesNo = (flag: boolean) => (flag ? "yes" : "no");

  return (
    <div className="flex flex-col gap-5">
      <div>
        <MoneyInput
          label="Total education budget"
          hint={`Originally ${formatInr(original.budget)}.`}
          value={value.budget}
          onChange={(budget) => set("budget", budget ?? 0)}
        />
        <input
          type="range"
          className="mt-3 w-full accent-financialFit"
          aria-label="Total education budget slider"
          aria-valuetext={formatInr(value.budget)}
          min={0}
          max={Math.max(sliderMax, value.budget)}
          step={BUDGET_STEP}
          value={value.budget}
          onChange={(event) => set("budget", Number(event.target.value))}
        />
      </div>

      <RadioGroup
        legend="Loan the family would take"
        name="whatif-loan"
        options={LOAN_OPTIONS}
        value={value.loan_willingness}
        onChange={(loan) => set("loan_willingness", loan)}
        compact
      />

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Home city">
          {(control) => (
            <Select {...control} value={value.home_city} onChange={(e) => set("home_city", e.target.value as CityId)}>
              {CITY_IDS.map((city) => (
                <option key={city} value={city}>
                  {CITY_NAMES[city]}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label="Parents' top priority">
          {(control) => (
            <Select
              {...control}
              value={value.top_priority}
              onChange={(e) => set("top_priority", e.target.value as TopPriority)}
            >
              {PRIORITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <RadioGroup
          legend="Student would move to another city"
          name="whatif-relocate"
          options={YES_NO}
          value={yesNo(value.willing_to_relocate)}
          onChange={(answer) => set("willing_to_relocate", answer === "yes")}
          compact
        />
        <RadioGroup
          legend="Student wants higher studies"
          name="whatif-higher-studies"
          options={YES_NO}
          value={yesNo(value.wants_higher_studies)}
          onChange={(answer) => set("wants_higher_studies", answer === "yes")}
          compact
        />
        <RadioGroup
          legend="Student's comfort with risk"
          name="whatif-student-risk"
          options={LEVEL_OPTIONS}
          value={value.risk_tolerance}
          onChange={(level) => set("risk_tolerance", level)}
          compact
        />
        <RadioGroup
          legend="Parents' comfort with risk"
          name="whatif-parent-risk"
          options={LEVEL_OPTIONS}
          value={value.risk_appetite}
          onChange={(level) => set("risk_appetite", level)}
          compact
        />
      </div>
    </div>
  );
}
