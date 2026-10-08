import type { ReactNode } from "react";
import type { AssessmentResult } from "../../api/client";
import { formatInr } from "../../lib/format";
import { COMPONENTS, CONFLICT_DIMENSIONS } from "../../lib/labels";
import { colors, componentColors } from "../../theme/tokens";

const RING_R = 42;
const RING_C = 2 * Math.PI * RING_R;

/** A ring split into the five PRISM components, sized by points earned out of 100. */
function ScoreRing({ points, score }: { points: Record<string, number>; score: number }) {
  let offset = 0;
  return (
    <svg viewBox="0 0 100 100" width={104} height={104} className="shrink-0" role="img" aria-label={`PRISM Score ${score.toFixed(1)} of 100`}>
      <circle cx="50" cy="50" r={RING_R} fill="none" stroke={colors.line} strokeWidth="10" />
      {COMPONENTS.map(({ key }) => {
        const length = ((points[key] ?? 0) / 100) * RING_C;
        const segment = (
          <circle
            key={key}
            cx="50"
            cy="50"
            r={RING_R}
            fill="none"
            stroke={componentColors[key]}
            strokeWidth="10"
            strokeDasharray={`${length} ${RING_C - length}`}
            strokeDashoffset={-offset}
            transform="rotate(-90 50 50)"
          />
        );
        offset += length;
        return segment;
      })}
      <text x="50" y="50" textAnchor="middle" dominantBaseline="central" className="fill-ink font-heading" fontSize="22">
        {score.toFixed(1)}
      </text>
    </svg>
  );
}

/** A half-circle meter from 0 to 100. */
function Gauge({ value, color, label }: { value: number; color: string; label: string }) {
  const arc = Math.PI * 40;
  const filled = (Math.max(0, Math.min(100, value)) / 100) * arc;
  return (
    <svg viewBox="0 0 100 58" width={150} height={87} className="shrink-0" role="img" aria-label={label}>
      <path d="M10 50 A40 40 0 0 1 90 50" fill="none" stroke={colors.line} strokeWidth="10" strokeLinecap="round" />
      <path
        d="M10 50 A40 40 0 0 1 90 50"
        fill="none"
        stroke={color}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${filled} ${arc}`}
      />
      <text x="50" y="47" textAnchor="middle" className="fill-ink font-heading" fontSize="18">
        {Math.round(value)}
      </text>
    </svg>
  );
}

function Tile({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex h-full flex-col rounded-xl border border-line bg-surface p-5">
      <h3 className="text-sm font-medium text-ink/60">{title}</h3>
      <div className="mt-3 flex flex-1 flex-col items-center justify-center gap-3 text-center">{children}</div>
    </div>
  );
}

/** Four pictures that answer the family's first questions before any detail. */
export function AtAGlance({ result }: { result: AssessmentResult }) {
  const top = result.ranking[0];
  const detail = top ? result.details[top.career_id] : undefined;
  const agreement = 100 - result.conflict.index;
  const hotspot = result.conflict.hotspots[0];
  const confidence = result.confidence;
  const finance = detail?.finance;
  const cost = finance?.effective_cost ?? 0;
  const scaleMax = finance ? Math.max(cost, finance.capacity, finance.budget) || 1 : 1;
  const bars = finance
    ? [
        { label: "Course cost", value: cost, color: colors.ink },
        { label: "Family budget", value: finance.budget, color: colors.financialFit },
        { label: "With a loan", value: finance.capacity, color: `${colors.financialFit}80` },
      ]
    : [];

  return (
    <section aria-labelledby="glance-heading" className="flex flex-col gap-4">
      <h2 id="glance-heading" className="text-lg">
        At a glance
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {top && (
          <Tile title="Best match">
            <ScoreRing points={top.points} score={top.score} />
            <div>
              <p className="font-heading text-lg leading-tight">{top.name}</p>
              <ul className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-0.5 text-sm text-ink/70">
                {COMPONENTS.map((c) => (
                  <li key={c.key} className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full" style={{ background: componentColors[c.key] }} />
                    {c.label}
                  </li>
                ))}
              </ul>
            </div>
          </Tile>
        )}
        <Tile title="Family agreement">
          <Gauge
            value={agreement}
            color={agreement >= 70 ? colors.financialFit : agreement >= 50 ? colors.marketDemand : colors.parentAlignment}
            label={`Family agreement ${Math.round(agreement)} of 100`}
          />
          <p className="text-sm text-ink/70">
            {agreement >= 70 ? "Mostly on the same page." : agreement >= 50 ? "Some differences to talk through." : "Big differences to talk through."}
            {hotspot && (
              <span className="mt-1 block text-ink">Biggest gap: {CONFLICT_DIMENSIONS[hotspot]?.label ?? hotspot}</span>
            )}
          </p>
        </Tile>
        {finance && (
          <Tile title="Can the family afford it?">
            <div className="flex w-full flex-col gap-2 text-left">
              {bars.map((bar) => (
                <div key={bar.label}>
                  <div className="flex justify-between text-sm">
                    <span className="text-ink/70">{bar.label}</span>
                    <span className="font-medium">{formatInr(bar.value)}</span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-line">
                    <div
                      className="h-2 rounded-full"
                      style={{ width: `${(bar.value / scaleMax) * 100}%`, background: bar.color }}
                    />
                  </div>
                </div>
              ))}
              <p className="text-sm text-ink/60">For the #1 career. Indicative estimate.</p>
            </div>
          </Tile>
        )}
        {confidence && (
          <Tile title="How sure we are">
            <Gauge
              value={confidence.score}
              color={confidence.band === "High" ? colors.growth : confidence.band === "Medium" ? colors.marketDemand : colors.danger}
              label={`Confidence ${Math.round(confidence.score)} of 100`}
            />
            <p className="text-sm text-ink/70">
              <span className="block font-medium text-ink">{confidence.band} confidence</span>
              Based on how complete the answers and our data are.
            </p>
          </Tile>
        )}
      </div>
    </section>
  );
}
