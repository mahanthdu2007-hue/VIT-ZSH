import { formatIndian, inrInWords, parseIndian } from "../../lib/format";
import { Field } from "./Field";

type MoneyInputProps = {
  label: string;
  hint: string;
  value: number | null;
  onChange: (value: number | null) => void;
  error?: string;
};

/** A rupee amount typed freely and shown with Indian grouping (5,00,000), plus the amount in words. */
export function MoneyInput({ label, hint, value, onChange, error }: MoneyInputProps) {
  const words = value !== null && value > 0 ? ` That is ₹${inrInWords(value)}.` : "";
  return (
    <Field label={label} hint={`${hint}${words}`} error={error}>
      {(control) => (
        <div className="flex items-center rounded-lg border border-line bg-surface focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-studentFit">
          <span className="pl-3 text-ink/70" aria-hidden="true">
            ₹
          </span>
          <input
            {...control}
            className="w-full rounded-lg bg-transparent px-2 py-2 text-base focus-visible:outline-none"
            inputMode="numeric"
            autoComplete="off"
            value={value === null ? "" : formatIndian(value)}
            onChange={(event) => onChange(parseIndian(event.target.value))}
          />
        </div>
      )}
    </Field>
  );
}
