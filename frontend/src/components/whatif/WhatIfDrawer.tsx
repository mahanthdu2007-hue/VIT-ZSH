import { useEffect, useMemo, useRef, useState } from "react";
import type { AssessRequest, RankedCareer } from "../../api/client";
import { useWhatIf } from "../../api/queries";
import { useDebouncedValue } from "../../lib/useDebouncedValue";
import { controlsFrom, overridesBetween } from "../../lib/whatif";
import { Button } from "../ui/Button";
import { WhatIfControlsForm } from "./WhatIfControlsForm";
import { WhatIfRanking } from "./WhatIfRanking";

const DEBOUNCE_MS = 250;

type WhatIfDrawerProps = {
  open: boolean;
  onClose: () => void;
  assessmentId: string;
  inputs: AssessRequest;
  ranking: RankedCareer[];
};

/** §11 What-If simulator: change a few answers and watch the ranking re-order, with a reason for each big move. */
export function WhatIfDrawer({ open, onClose, assessmentId, inputs, ranking }: WhatIfDrawerProps) {
  const dialog = useRef<HTMLDialogElement>(null);
  const original = useMemo(() => controlsFrom(inputs), [inputs]);
  const [controls, setControls] = useState(original);
  const pending = useMemo(() => overridesBetween(original, controls), [original, controls]);
  const overrides = useDebouncedValue(pending, DEBOUNCE_MS);
  const changed = Object.keys(overrides).length > 0;
  const whatIf = useWhatIf(assessmentId, overrides);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);

  const result = changed ? whatIf.data : undefined;
  const status = !changed
    ? "Showing your original ranking. Change an answer to see what moves."
    : whatIf.isError
      ? "The engine could not re-run this change. Try again in a moment."
      : whatIf.isFetching || !result
        ? "Re-ranking…"
        : `Re-ranked in ${Math.round(result.elapsed_ms)} ms.`;

  return (
    <dialog
      ref={dialog}
      aria-labelledby="whatif-heading"
      onClose={onClose}
      className="m-0 ml-auto h-full max-h-none w-full max-w-2xl overflow-y-auto xl:max-w-6xl bg-paper p-0 text-ink shadow-lg backdrop:bg-ink/40"
    >
      <div className="flex flex-col gap-6 p-4 sm:p-6">
        <header className="flex items-start justify-between gap-3">
          <div>
            <h2 id="whatif-heading" className="text-xl">
              Try a what-if
            </h2>
            <p className="mt-1 text-sm text-ink/70">
              Change an answer to see how the ranking would move. Your original answers stay saved.
            </p>
          </div>
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </header>

        <div className="grid items-start gap-6 xl:grid-cols-2">
          <section
            aria-label="What-if answers"
            className="rounded-xl border border-line bg-surface p-4 xl:sticky xl:top-0"
          >
            <WhatIfControlsForm original={original} value={controls} onChange={setControls} />
            <Button
              variant="secondary"
              className="mt-5"
              onClick={() => setControls(original)}
              disabled={Object.keys(pending).length === 0}
            >
              Back to original
            </Button>
          </section>

          <section aria-labelledby="whatif-ranking-heading">
            <h3 id="whatif-ranking-heading" className="text-lg">
              Your top careers
            </h3>
            <p className="mt-1 text-sm text-ink/70" role="status">
              {status}
            </p>
            <div className="mt-3">
              <WhatIfRanking ranking={result?.ranking ?? ranking} changes={result?.changes ?? null} />
            </div>
          </section>
        </div>
      </div>
    </dialog>
  );
}
