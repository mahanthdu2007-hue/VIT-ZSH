import type { Confidence } from "../../api/client";
import { formatPoints } from "../../lib/format";
import { missingInputHints } from "../../lib/labels";
import { Badge } from "../ui/Badge";

const TONE = { High: "good", Medium: "warn", Low: "low" } as const;

/** §7.8 confidence band, with the missing inputs that would raise it shown as hints. */
export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  const hints = missingInputHints(confidence.missing_inputs);
  return (
    <section aria-labelledby="confidence-heading" className="rounded-lg border border-line bg-paper p-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 id="confidence-heading" className="text-base">
          How sure we are
        </h3>
        <Badge tone={TONE[confidence.band]}>
          {confidence.band} confidence · {formatPoints(confidence.score)} of 100
        </Badge>
      </div>
      <p className="mt-2 text-sm text-ink/70">
        Based on how complete the answers are, how clearly the written answers could be read, and how complete our data
        on this career is.
      </p>
      {hints.length > 0 ? (
        <div className="mt-2 text-sm">
          <p className="font-medium">To make this more certain:</p>
          <ul className="mt-1 list-disc pl-5">
            {hints.map((hint) => (
              <li key={hint}>{hint}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="mt-2 text-sm">Every question was answered.</p>
      )}
    </section>
  );
}
