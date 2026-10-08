import type { CityId, Stream } from "../../api/client";
import { useCareers } from "../../api/queries";
import { CITY_IDS, CITY_NAMES, DOMAINS, STREAMS, SUBJECTS } from "../../lib/labels";
import { CheckboxGroup, RadioGroup } from "../ui/Choice";
import { Field, Select, TextInput, controlClass } from "../ui/Field";
import { STREAM_FROM_CLASS } from "./steps";
import type { BasicStepProps } from "./types";

const CLASSES = [9, 10, 11, 12];
const YEARS = [1, 2, 3, 4, 5];

export function AboutYouStep({ draft, update, errors }: BasicStepProps) {
  const careers = useCareers();
  return (
    <div className="flex flex-col gap-6">
      {draft.track === "school" ? (
        <>
          <RadioGroup
            legend="Which class are you in?"
            name="current_class"
            compact
            options={CLASSES.map((c) => ({ value: String(c), label: `Class ${c}` }))}
            value={draft.current_class === null ? null : String(draft.current_class)}
            onChange={(value) => {
              const current_class = Number(value);
              update({ current_class, stream: current_class >= STREAM_FROM_CLASS ? draft.stream : null });
            }}
            error={errors.current_class}
          />
          {draft.current_class !== null && draft.current_class >= STREAM_FROM_CLASS && (
            <RadioGroup<Stream>
              legend="Which stream are you in?"
              name="stream"
              compact
              options={(Object.keys(STREAMS) as Stream[]).map((s) => ({ value: s, label: STREAMS[s] }))}
              value={draft.stream}
              onChange={(stream) => update({ stream })}
              error={errors.stream}
            />
          )}
        </>
      ) : (
        <>
          <Field label="Which degree are you studying?" hint="For example B.Com, B.Sc Physics or B.Tech ECE." error={errors.degree}>
            {(control) => (
              <TextInput {...control} value={draft.degree} onChange={(e) => update({ degree: e.target.value })} />
            )}
          </Field>
          <RadioGroup
            legend="Which year are you in?"
            name="year"
            compact
            options={YEARS.map((y) => ({ value: String(y), label: `Year ${y}` }))}
            value={draft.year === null ? null : String(draft.year)}
            onChange={(value) => update({ year: Number(value) })}
            error={errors.year}
          />
        </>
      )}

      <Field label="Your latest overall marks, in percent" hint="Your most recent exam. A rough figure is fine." optional error={errors.marks_percent}>
        {(control) => (
          <TextInput
            {...control}
            type="number"
            inputMode="decimal"
            min={0}
            max={100}
            className={`${controlClass} max-w-32`}
            value={draft.marks_percent ?? ""}
            onChange={(e) => update({ marks_percent: e.target.value === "" ? null : Number(e.target.value) })}
          />
        )}
      </Field>

      <CheckboxGroup
        legend="Favourite subjects"
        hint="Pick any that you enjoy."
        options={SUBJECTS.map((s) => ({ value: s, label: s }))}
        value={draft.favourite_subjects}
        onChange={(favourite_subjects) => update({ favourite_subjects })}
      />

      <Field label="Home city" hint="Where your family lives now." error={errors.home_city}>
        {(control) => (
          <Select
            {...control}
            value={draft.home_city ?? ""}
            onChange={(e) => update({ home_city: e.target.value === "" ? null : (e.target.value as CityId) })}
          >
            <option value="">Choose a city</option>
            {CITY_IDS.map((id) => (
              <option key={id} value={id}>
                {CITY_NAMES[id]}
              </option>
            ))}
          </Select>
        )}
      </Field>

      <Field label="Do you have a dream career?" hint="If it is not in your top results, we will show the closest realistic routes to it." optional>
        {(control) => (
          <Select
            {...control}
            value={draft.dream_career_id ?? ""}
            onChange={(e) => update({ dream_career_id: e.target.value === "" ? null : e.target.value })}
          >
            <option value="">No dream career yet</option>
            {DOMAINS.map((domain) => (
              <optgroup key={domain} label={domain}>
                {careers.data
                  ?.filter((c) => c.domain === domain)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </optgroup>
            ))}
          </Select>
        )}
      </Field>
    </div>
  );
}
