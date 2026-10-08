import type { CareerExplanation, Explanations } from "../../api/client";
import { LLM_PROVIDER_NAMES } from "../../lib/labels";
import { SourceLinks } from "./SourceLinks";

type WhyWhyNotProps = {
  explanations: Explanations;
  careerId: string;
  isRefreshing: boolean;
};

function ReasonTile({ title, lines, tone }: { title: string; lines: string[]; tone: "good" | "watch" }) {
  const marker = tone === "good" ? "✓" : "!";
  const colours =
    tone === "good" ? "bg-financialFit/15 text-financialFit" : "bg-marketDemand/15 text-marketDemand";
  return (
    <div className="flex h-full flex-col rounded-lg border border-line p-4">
      <h4 className="font-medium">{title}</h4>
      <ul className="mt-3 flex flex-col gap-3">
        {lines.map((line) => (
          <li key={line} className="flex gap-3 leading-snug">
            <span
              aria-hidden="true"
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-sm ${colours}`}
            >
              {marker}
            </span>
            {line}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** §12 why / why-not for one career; covers the top 5 careers and the middle path. */
export function WhyWhyNot({ explanations, careerId, isRefreshing }: WhyWhyNotProps) {
  const item: CareerExplanation | undefined = explanations.items.find((e) => e.career_id === careerId);
  if (!item) {
    return (
      <p className="rounded-lg bg-paper p-4 text-ink/80">
        Written reasons are prepared for the top 5 careers and the middle path. The Overview tab shows how this career
        was scored.
      </p>
    );
  }
  return (
    <section aria-label="Why it fits, and what to watch" aria-busy={isRefreshing} className="flex flex-col gap-4">
      <div className="grid items-stretch gap-4 md:grid-cols-2">
        <ReasonTile title="Why it fits" lines={item.why} tone="good" />
        <ReasonTile title="What to watch" lines={item.why_not} tone="watch" />
      </div>
      <div className="rounded-lg bg-paper p-4">
        <h4 className="font-medium">The route in words</h4>
        <p className="mt-2 leading-relaxed">{item.roadmap_narrative}</p>
      </div>
      <div className="flex flex-col gap-1">
        <p className="text-sm text-ink/60" role="status">
          {sourceNote(explanations, item)}
        </p>
        <SourceLinks citations={item.citations} />
      </div>
    </section>
  );
}

function sourceNote(explanations: Explanations, item: CareerExplanation): string {
  if (explanations.status === "pending")
    return "Written directly from the engine's numbers. A friendlier version is on its way.";
  if (item.source === "template") return "Written directly from the engine's numbers.";
  const provider = LLM_PROVIDER_NAMES[explanations.trace?.provider ?? ""] ?? "an AI model";
  return `Reworded by ${provider} from the engine's results. Every number was checked against the engine.`;
}
