type StepperProps = { steps: string[]; current: number };

/** Progress through a form: the step names, the current one highlighted, and a bar. */
export function Stepper({ steps, current }: StepperProps) {
  const percent = ((current + 1) / steps.length) * 100;
  return (
    <nav aria-label="Progress">
      <p className="text-sm text-ink/70">
        Step {current + 1} of {steps.length}: <span className="font-medium text-ink">{steps[current]}</span>
      </p>
      <div
        className="mt-2 h-2 overflow-hidden rounded-full bg-line"
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={steps.length}
        aria-valuenow={current + 1}
        aria-label="Form progress"
      >
        <div className="h-full rounded-full bg-studentFit" style={{ width: `${percent}%` }} />
      </div>
      <ol className="mt-3 hidden flex-wrap gap-x-4 gap-y-1 text-sm md:flex">
        {steps.map((step, index) => (
          <li
            key={step}
            aria-current={index === current ? "step" : undefined}
            className={index === current ? "font-medium text-ink" : index < current ? "text-ink/70" : "text-ink/50"}
          >
            {step}
          </li>
        ))}
      </ol>
    </nav>
  );
}
