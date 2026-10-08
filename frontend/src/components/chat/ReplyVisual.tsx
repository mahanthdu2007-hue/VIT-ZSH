import type { AssessmentResult, ChatReply } from "../../api/client";
import { SCHOLARSHIP_PORTAL_URL } from "../../lib/labels";
import { PrismBar } from "../dashboard/PrismBar";

function Arrow({ change }: { change: number | null | undefined }) {
  if (!change) return <span className="w-8 text-sm text-ink/40">–</span>;
  const up = change > 0;
  return (
    <span className={`w-8 text-sm font-medium ${up ? "text-financialFit" : "text-danger"}`}>
      {up ? "↑" : "↓"}
      {Math.abs(change)}
    </span>
  );
}

/** A small picture under a chat answer: the new ranking for a what-if, score bars for careers, scholarship tiles. */
export function ReplyVisual({ reply, result }: { reply: ChatReply; result: AssessmentResult }) {
  if (reply.whatif) {
    const changes = new Map(reply.whatif.result.changes.map((c) => [c.career_id, c]));
    return (
      <ol className="mt-2 flex flex-col gap-2 rounded-lg border border-line bg-surface p-3">
        <li className="text-sm font-medium text-ink/60">New top 5</li>
        {reply.whatif.result.ranking.slice(0, 5).map((r) => (
          <li key={r.career_id} className="flex items-center gap-2 text-sm">
            <span className="w-6 text-ink/60">#{r.rank}</span>
            <span className="flex-1 truncate">{r.name}</span>
            <Arrow change={changes.get(r.career_id)?.rank_change} />
            <span className="w-10 text-right font-medium">{r.score.toFixed(1)}</span>
          </li>
        ))}
      </ol>
    );
  }
  const careers = reply.sources
    .filter((s) => s.kind === "career")
    .map((s) => result.ranking.find((r) => r.career_id === s.id))
    .filter((r) => r !== undefined);
  const schemes = reply.sources.filter((s) => s.kind === "scholarship");
  if (reply.intent === "scholarships" && schemes.length > 0) {
    return (
      <ul className="mt-2 flex flex-col gap-2">
        {schemes.map((s) => (
          <li key={s.id} className="rounded-lg border border-line bg-surface">
            <p className="p-3 text-sm font-medium">{s.label}</p>
            <a
              href={SCHOLARSHIP_PORTAL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex justify-between border-t border-line px-3 py-2 text-sm hover:bg-paper"
            >
              Apply on National Scholarship Portal <span aria-hidden="true">↗</span>
            </a>
          </li>
        ))}
      </ul>
    );
  }
  if (careers.length > 0 && (reply.intent === "explain" || reply.intent === "compare")) {
    return (
      <ul className="mt-2 flex flex-col gap-3 rounded-lg border border-line bg-surface p-3">
        {careers.map((r) => (
          <li key={r.career_id}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="font-medium">
                #{r.rank} {r.name}
              </span>
              <span>{r.score.toFixed(1)}</span>
            </div>
            <PrismBar points={r.points} score={r.score} size="sm" />
          </li>
        ))}
      </ul>
    );
  }
  return null;
}
