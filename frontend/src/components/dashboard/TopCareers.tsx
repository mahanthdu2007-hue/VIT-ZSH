import type { RankedCareer } from "../../api/client";
import { formatPoints } from "../../lib/format";
import { Card } from "../ui/Card";
import { PrismBar } from "./PrismBar";

type TopCareersProps = {
  ranking: RankedCareer[];
  selectedId: string;
  onSelect: (careerId: string) => void;
};

export function TopCareers({ ranking, selectedId, onSelect }: TopCareersProps) {
  return (
    <Card title="Your top careers" description="Ranked by PRISM Score out of 100. Choose one to see why.">
      <ul className="flex flex-col gap-2">
        {ranking.map((career) => {
          const selected = career.career_id === selectedId;
          return (
            <li key={career.career_id}>
              <button
                type="button"
                aria-pressed={selected}
                onClick={() => onSelect(career.career_id)}
                className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                  selected ? "border-studentFit bg-studentFit/10" : "border-line hover:border-ink/40"
                }`}
              >
                <span className="flex items-baseline justify-between gap-3">
                  <span>
                    <span className="mr-2 text-sm text-ink/60">#{career.rank}</span>
                    <span className="font-medium">{career.name}</span>
                    <span className="block text-sm text-ink/70">{career.domain}</span>
                  </span>
                  <span className="font-heading text-lg font-semibold">{formatPoints(career.score)}</span>
                </span>
                <span className="mt-2 block">
                  <PrismBar points={career.points} score={career.score} size="sm" />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
