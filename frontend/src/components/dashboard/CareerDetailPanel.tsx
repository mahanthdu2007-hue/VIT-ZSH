import { motion } from "framer-motion";
import { forwardRef } from "react";
import type { CareerDetail, Explanations } from "../../api/client";
import { formatInr, formatPoints } from "../../lib/format";
import { timing } from "../../theme/tokens";
import { Badge, IndicativeTag } from "../ui/Badge";
import { Card } from "../ui/Card";
import { CountUp } from "../ui/CountUp";
import { Tabs } from "../ui/Tabs";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { ExamsAndScholarships } from "./ExamsAndScholarships";
import { PrismBar } from "./PrismBar";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { WhyWhyNot } from "./WhyWhyNot";

type CareerDetailPanelProps = {
  detail: CareerDetail;
  explanations: Explanations;
  explanationsRefreshing: boolean;
};

/** The selected career: score bar, breakdown, confidence and the written why / why-not. Content fades in on each switch. */
export const CareerDetailPanel = forwardRef<HTMLHeadingElement, CareerDetailPanelProps>(function CareerDetailPanel(
  { detail, explanations, explanationsRefreshing },
  headingRef,
) {
  const { career, finance, pathway, score } = detail;
  const pathwayCost = finance.pathways.find((p) => p.pathway_id === pathway.id)?.effective_cost;
  return (
    <Card as="article" aria-labelledby="career-detail-heading">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink/60">
            {career.domain}
            {detail.rank !== null && ` · rank ${detail.rank}`}
          </p>
          <h2
            id="career-detail-heading"
            ref={headingRef}
            tabIndex={-1}
            className="mt-1 text-xl leading-tight focus-visible:outline-none sm:text-2xl"
          >
            {career.name}
          </h2>
        </div>
        <p className="text-right">
          <CountUp value={score.score} format={formatPoints} className="text-2xl font-semibold tracking-tight" />
          <span className="block text-sm text-ink/60">PRISM Score of 100</span>
        </p>
      </header>

      <motion.div
        key={career.id}
        className="flex flex-1 flex-col"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: timing.base, ease: timing.ease }}
      >
        <p className="mt-3 leading-relaxed text-ink/70">{career.summary}</p>
        {detail.status === "needs_aid" && (
          <p className="mt-3">
            <Badge tone="warn">Needs aid: {formatInr(finance.funding_gap)} over the budget and loan plan</Badge>
          </p>
        )}

        <div className="mt-8">
          <Tabs
            label={`About ${career.name}`}
            tabs={[
              {
                id: "overview",
                label: "Overview",
                content: (
                  <div className="flex flex-col gap-6">
                    <div className="pt-2">
                      <PrismBar points={score.points} score={score.score} />
                    </div>
                    <p className="flex flex-wrap items-center gap-2 rounded-xl bg-paper p-4">
                      <span>
                        Suggested route: <span className="font-medium">{pathway.label}</span>, about{" "}
                        {pathway.duration_years} years
                        {pathwayCost !== undefined && `, around ${formatInr(pathwayCost)} after expected scholarships`}.
                      </span>
                      <IndicativeTag />
                    </p>
                    <ScoreBreakdown detail={detail} />
                    <ConfidenceBadge confidence={detail.confidence} />
                  </div>
                ),
              },
              {
                id: "why",
                label: "Why it fits",
                content: (
                  <WhyWhyNot explanations={explanations} careerId={career.id} isRefreshing={explanationsRefreshing} />
                ),
              },
              { id: "aid", label: "Scholarships and exams", content: <ExamsAndScholarships detail={detail} /> },
            ]}
          />
        </div>
      </motion.div>
    </Card>
  );
});
