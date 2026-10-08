import type { CareerExplanation, Explanations } from "../../api/client";

type WhyWhyNotProps = {
  explanations: Explanations;
  careerId: string;
  isRefreshing: boolean;
};

/** §12 why / why-not for one career; covers the top 5 careers and the middle path. */
export function WhyWhyNot({ explanations, careerId, isRefreshing }: WhyWhyNotProps) {
  const item: CareerExplanation | undefined = explanations.items.find((e) => e.career_id === careerId);
  return (
    <section aria-labelledby="why-heading" aria-busy={isRefreshing}>
      <h3 id="why-heading" className="text-lg">
        Why it fits, and what to watch
      </h3>
      {item ? (
        <>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <div>
              <h4 className="font-medium">Why it fits</h4>
              <ul className="mt-1 list-disc pl-5">
                {item.why.map((line) => (
                  <li key={line} className="mt-1">
                    {line}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-medium">What to watch</h4>
              <ul className="mt-1 list-disc pl-5">
                {item.why_not.map((line) => (
                  <li key={line} className="mt-1">
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <p className="mt-4 rounded-lg bg-paper p-3">{item.roadmap_narrative}</p>
          <p className="mt-2 text-sm text-ink/60">
            {explanations.source === "template"
              ? "Written directly from the engine's numbers."
              : "Reworded by a language model from the engine's numbers."}
          </p>
        </>
      ) : (
        <p className="mt-2 text-ink/80">
          Written reasons are prepared for the top 5 careers and the middle path. The score breakdown above shows how
          this career was scored.
        </p>
      )}
    </section>
  );
}
