import { useEffect, useRef, useState } from "react";
import type { Citation } from "../../api/client";
import { SOURCE_KIND_LABELS } from "../../lib/labels";
import { Button } from "../ui/Button";

/** §12 small links to the dataset rows an explanation used; each opens the row as it was given to the engine. */
export function SourceLinks({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState<Citation | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);

  if (citations.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-sm text-ink/70">Based on these rows of our data:</p>
      <ul className="mt-1 flex flex-wrap gap-2">
        {citations.map((c) => (
          <li key={`${c.kind}:${c.career_id ?? ""}:${c.id}`}>
            <button
              type="button"
              onClick={() => setOpen(c)}
              className="rounded-full border border-line bg-surface px-2 py-0.5 text-sm underline decoration-line underline-offset-2 hover:border-ink/40"
            >
              {SOURCE_KIND_LABELS[c.kind]}: {c.label}
            </button>
          </li>
        ))}
      </ul>
      <dialog
        ref={dialog}
        aria-labelledby="source-heading"
        onClose={() => setOpen(null)}
        className="w-full max-w-lg rounded-xl bg-surface p-0 text-ink shadow-lg backdrop:bg-ink/40"
      >
        {open && (
          <div className="flex flex-col gap-3 p-4 sm:p-6">
            <p className="text-sm text-ink/70">{SOURCE_KIND_LABELS[open.kind]}</p>
            <h2 id="source-heading" className="text-lg">
              {open.label}
            </h2>
            <p>{open.text}</p>
            <p className="text-sm text-ink/70">
              Data id: {open.career_id && open.kind === "pathway" ? `${open.career_id} / ` : ""}
              {open.id}. Values are indicative estimates.
            </p>
            <Button variant="secondary" className="self-start" onClick={() => setOpen(null)}>
              Close
            </Button>
          </div>
        )}
      </dialog>
    </div>
  );
}
