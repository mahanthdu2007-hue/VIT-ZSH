import { type ReactNode, useId } from "react";
import { FieldError } from "./Field";

export type Option<T extends string> = { value: T; label: ReactNode; hint?: ReactNode };

type GroupShell = { legend: ReactNode; hint?: ReactNode; error?: string; children: ReactNode; compact?: boolean };

function Group({ legend, hint, error, children, compact }: GroupShell) {
  const id = useId();
  return (
    <fieldset aria-describedby={error ? `${id}-error` : undefined} aria-invalid={Boolean(error)}>
      <legend className="font-medium">{legend}</legend>
      {hint && <p className="mt-0.5 text-sm text-ink/70">{hint}</p>}
      <div className={`mt-2 flex flex-wrap ${compact ? "gap-1.5" : "gap-2"}`}>{children}</div>
      <FieldError id={`${id}-error`} error={error} />
    </fieldset>
  );
}

const optionClass =
  "flex cursor-pointer items-start gap-2 rounded-lg border border-line bg-surface px-3 py-2 has-[:checked]:border-studentFit has-[:checked]:bg-studentFit/10 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-studentFit";

type RadioGroupProps<T extends string> = Omit<GroupShell, "children"> & {
  name: string;
  options: Option<T>[];
  value: T | null;
  onChange: (value: T) => void;
};

/** One choice from a few options, shown as selectable cards. */
export function RadioGroup<T extends string>({ name, options, value, onChange, ...shell }: RadioGroupProps<T>) {
  return (
    <Group {...shell}>
      {options.map((option) => (
        <label key={option.value} className={`${optionClass} ${shell.compact ? "" : "min-w-32 flex-1"}`}>
          <input
            type="radio"
            className="mt-1 accent-studentFit focus-visible:outline-none"
            name={name}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span>
            <span className="block">{option.label}</span>
            {option.hint && <span className="block text-sm text-ink/70">{option.hint}</span>}
          </span>
        </label>
      ))}
    </Group>
  );
}

type CheckboxGroupProps<T extends string> = Omit<GroupShell, "children"> & {
  options: Option<T>[];
  value: T[];
  onChange: (value: T[]) => void;
};

/** Any number of choices, shown as toggle chips. */
export function CheckboxGroup<T extends string>({ options, value, onChange, ...shell }: CheckboxGroupProps<T>) {
  const toggle = (item: T) => onChange(value.includes(item) ? value.filter((v) => v !== item) : [...value, item]);
  return (
    <Group {...shell} compact>
      {options.map((option) => (
        <label key={option.value} className={optionClass}>
          <input
            type="checkbox"
            className="mt-1 accent-studentFit focus-visible:outline-none"
            checked={value.includes(option.value)}
            onChange={() => toggle(option.value)}
          />
          <span>
            <span className="block">{option.label}</span>
            {option.hint && <span className="block text-sm text-ink/70">{option.hint}</span>}
          </span>
        </label>
      ))}
    </Group>
  );
}

export const YES_NO: Option<"yes" | "no">[] = [
  { value: "yes", label: "Yes" },
  { value: "no", label: "No" },
];
