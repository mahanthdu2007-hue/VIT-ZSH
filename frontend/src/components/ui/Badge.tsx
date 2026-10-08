import type { ReactNode } from "react";

type Tone = "neutral" | "good" | "warn" | "low";

const TONES: Record<Tone, string> = {
  neutral: "border-line bg-paper text-ink",
  good: "border-financialFit/40 bg-financialFit/10 text-ink",
  warn: "border-marketDemand/50 bg-marketDemand/10 text-ink",
  low: "border-danger/40 bg-danger/10 text-ink",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-sm font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function IndicativeTag() {
  return <Badge>Indicative estimate</Badge>;
}
