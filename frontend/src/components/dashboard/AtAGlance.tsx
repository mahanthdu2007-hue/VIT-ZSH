import { motion, useInView, useReducedMotion } from "framer-motion";
import { type CSSProperties, type ReactNode, useRef } from "react";
import type { AssessmentResult } from "../../api/client";
import { formatInr, formatPoints } from "../../lib/format";
import { COMPONENTS, CONFLICT_DIMENSIONS } from "../../lib/labels";
import { useReveal } from "../../lib/useReveal";
import { colors, componentColors, timing } from "../../theme/tokens";
import { CountUp } from "../ui/CountUp";
import { Meter } from "../ui/Meter";

const RING_R = 42;
const RING_C = 2 * Math.PI * RING_R;
const GAUGE_ARC = "M10 50 A40 40 0 0 1 90 50";
const DARK_TRACK = `${colors.surface}26`;

/** A ring split into the five PRISM components, sized by points earned out of 100; it draws itself segment by segment. */
function ScoreRing({ points, score }: { points: Record<string, number>; score: number }) {
  const ref = useRef<SVGSVGElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  let offset = 0;
  return (
    <div className="relative h-40 w-40 shrink-0 sm:h-56 sm:w-56">
      <svg ref={ref} viewBox="0 0 100 100" className="h-full w-full" role="img" aria-label={`PRISM Score ${formatPoints(score)} of 100`}>
        <circle cx="50" cy="50" r={RING_R} fill="none" stroke={DARK_TRACK} strokeWidth="8" />
        {COMPONENTS.map(({ key }, i) => {
          const length = ((points[key] ?? 0) / 100) * RING_C;
          const drawn = `${length} ${RING_C - length}`;
          const segment = (
            <motion.circle
              key={key}
              cx="50"
              cy="50"
              r={RING_R}
              fill="none"
              stroke={componentColors[key]}
              strokeWidth="8"
              strokeDashoffset={-offset}
              transform="rotate(-90 50 50)"
              initial={{ strokeDasharray: reduce ? drawn : `0 ${RING_C}` }}
              animate={{ strokeDasharray: inView || reduce ? drawn : `0 ${RING_C}` }}
              transition={{ duration: timing.base, ease: timing.ease, delay: reduce ? 0 : i * timing.stagger * 2 }}
            />
          );
          offset += length;
          return segment;
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center" aria-hidden="true">
        <CountUp value={score} format={formatPoints} className="text-2xl font-semibold tracking-tight sm:text-3xl" />
        <span className="text-sm text-surface/60">of 100</span>
      </div>
    </div>
  );
}

/** A half-circle meter from 0 to 100 that sweeps to its value. */
function Gauge({ value, color, label }: { value: number; color: string; label: string }) {
  const ref = useRef<SVGSVGElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const share = Math.max(0, Math.min(100, value)) / 100;
  return (
    <div className="relative w-40">
      <svg ref={ref} viewBox="0 0 100 58" className="w-full" role="img" aria-label={label}>
        <path d={GAUGE_ARC} fill="none" stroke={colors.line} strokeWidth="9" strokeLinecap="round" />
        <motion.path
          d={GAUGE_ARC}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          initial={{ pathLength: reduce ? share : 0 }}
          animate={{ pathLength: inView || reduce ? share : 0 }}
          transition={{ duration: timing.slow, ease: timing.ease }}
        />
      </svg>
      <div className="absolute inset-x-0 bottom-0 text-center" aria-hidden="true">
        <CountUp value={value} format={(v) => String(Math.round(v))} className="text-xl font-semibold tracking-tight" />
      </div>
    </div>
  );
}

function Tile({ title, children, order }: { title: string; children: ReactNode; order: number }) {
  const { ref, shown } = useReveal<HTMLDivElement>();
  const delay: CSSProperties = { transitionDelay: `${order * timing.stagger}s` };
  return (
    <div
      ref={ref}
      data-shown={shown || undefined}
      style={delay}
      className="reveal flex h-full flex-col rounded-2xl bg-surface p-6 shadow sm:p-8"
    >
      <h3 className="text-sm font-medium text-ink/60">{title}</h3>
      <div className="mt-4 flex flex-1 flex-col items-center justify-center gap-4 text-center">{children}</div>
    </div>
  );
}

function BestMatch({ result, onExplore }: { result: AssessmentResult; onExplore: () => void }) {
  const { ref, shown } = useReveal<HTMLElement>();
  const top = result.ranking[0];
  if (!top) return null;
  return (
    <article
      ref={ref}
      data-shown={shown || undefined}
      aria-labelledby="best-match-heading"
      className="reveal flex flex-col items-center gap-8 overflow-hidden rounded-2xl bg-ink p-6 text-surface shadow-lg sm:p-10 lg:flex-row lg:justify-between"
    >
      <div className="flex w-full min-w-0 flex-col gap-6 lg:max-w-xl">
        <div>
          <p className="text-sm font-medium text-surface/60">Best match for you · {top.domain}</p>
          <h3 id="best-match-heading" className="mt-2 text-2xl leading-tight sm:text-3xl">
            {top.name}
          </h3>
        </div>
        <ul className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          {COMPONENTS.map((c) => (
            <li key={c.key} className="flex flex-col gap-1.5">
              <span className="flex items-center gap-1.5 text-sm text-surface/70">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: componentColors[c.key] }} aria-hidden="true" />
                {c.label}
              </span>
              <span className="text-lg font-semibold">
                <CountUp value={top.points[c.key] ?? 0} format={formatPoints} />
                <span className="text-sm font-normal text-surface/50"> / {c.max}</span>
              </span>
              <Meter value={(top.points[c.key] ?? 0) / c.max} color={componentColors[c.key]} height="h-1.5" track="dark" />
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={onExplore}
          className="self-start rounded-full bg-surface px-5 py-2 font-medium text-ink transition duration-200 hover:bg-surface/90 active:scale-95"
        >
          See why it ranks first
        </button>
      </div>
      <ScoreRing points={top.points} score={top.score} />
    </article>
  );
}

/** The answers to the family's first questions, before any detail: best match, agreement, cost and certainty. */
export function AtAGlance({ result, onExplore }: { result: AssessmentResult; onExplore: () => void }) {
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
    <section id="overview" aria-labelledby="glance-heading" className="flex scroll-mt-32 flex-col gap-4">
      <h2 id="glance-heading" className="sr-only">
        At a glance
      </h2>
      <BestMatch result={result} onExplore={onExplore} />
      <div className="grid gap-4 md:grid-cols-3">
        <Tile title="Family agreement" order={0}>
          <Gauge
            value={agreement}
            color={agreement >= 70 ? colors.financialFit : agreement >= 50 ? colors.marketDemand : colors.parentAlignment}
            label={`Family agreement ${Math.round(agreement)} of 100`}
          />
          <p className="text-sm text-ink/70">
            {agreement >= 70 ? "Mostly on the same page." : agreement >= 50 ? "Some differences to talk through." : "Big differences to talk through."}
            {hotspot && (
              <span className="mt-1 block font-medium text-ink">Biggest gap: {CONFLICT_DIMENSIONS[hotspot]?.label ?? hotspot}</span>
            )}
          </p>
        </Tile>
        {finance && (
          <Tile title="Can the family afford it?" order={1}>
            <div className="flex w-full flex-col gap-3 text-left">
              {bars.map((bar) => (
                <div key={bar.label}>
                  <div className="mb-1.5 flex justify-between text-sm">
                    <span className="text-ink/60">{bar.label}</span>
                    <span className="font-medium">{formatInr(bar.value)}</span>
                  </div>
                  <Meter value={bar.value / scaleMax} color={bar.color} />
                </div>
              ))}
              <p className="text-sm text-ink/50">For the #1 career. Indicative estimate.</p>
            </div>
          </Tile>
        )}
        {confidence && (
          <Tile title="How sure we are" order={2}>
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
