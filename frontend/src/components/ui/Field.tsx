import { type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes, useId } from "react";

export const controlClass =
  "w-full rounded-lg border border-line bg-surface px-3 py-2 text-base text-ink placeholder:text-ink/40 aria-[invalid=true]:border-danger";

export type ControlProps = { id: string; "aria-describedby"?: string; "aria-invalid": boolean };

type FieldProps = {
  label: ReactNode;
  hint?: ReactNode;
  error?: string;
  optional?: boolean;
  children: (control: ControlProps) => ReactNode;
};

/** A labelled control with optional helper text and an inline error, wired up for screen readers. */
export function Field({ label, hint, error, optional, children }: FieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div>
      <label htmlFor={id} className="block font-medium">
        {label}
        {optional && <span className="ml-1 text-sm font-normal text-ink/60">(optional)</span>}
      </label>
      {hint && (
        <p id={hintId} className="mt-0.5 text-sm text-ink/70">
          {hint}
        </p>
      )}
      <div className="mt-1.5">{children({ id, "aria-describedby": describedBy, "aria-invalid": Boolean(error) })}</div>
      <FieldError id={errorId} error={error} />
    </div>
  );
}

export function FieldError({ id, error }: { id?: string; error?: string }) {
  if (!error) return null;
  return (
    <p id={id} className="mt-1 text-sm font-medium text-danger" role="alert">
      {error}
    </p>
  );
}

export function TextInput(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={controlClass} {...props} />;
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={`${controlClass} min-h-24`} rows={4} {...props} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={controlClass} {...props} />;
}
