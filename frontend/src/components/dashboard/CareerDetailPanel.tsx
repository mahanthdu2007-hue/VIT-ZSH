import { forwardRef } from "react";
import type { CareerDetail, Explanations } from "../../api/client";
import { formatInr, formatPoints } from "../../lib/format";
import { Badge, IndicativeTag } from "../ui/Badge";
import { Card } from "../ui/Card";
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

/** The selected career: score bar, breakdown, confidence and the written why / why-not. */
export const CareerDetailPanel = forwardRef<HTMLHeadingElement, CareerDetailPanelProps>(function CareerDetailPanel(
  { detail, explanations, explanationsRefreshing },
  headingRef,
) {
  const { career, finance, pathway, score } = detail;
  const pathwayCost = finance.pathways.find((p) => p.pathway_id === pathway.id)?.effective_cost;
  return (
    <Card as="article" aria-labelledby="career-detail-heading">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-ink/70">
            {career.domain}
            {detail.rank !== null && ` · rank ${detail.rank}`}
          </p>
          <h2 id="career-detail-heading" ref={headingRef} tabIndex={-1} className="text-xl focus-visible:outline-none">
            {career.name}
          </h2>
        </div>
        <p className="text-right">
          <span className="font-heading text-2xl font-semibold">{formatPoints(score.score)}</span>
          <span className="block text-sm text-ink/70">PRISM Score of 100</span>
        </p>
      </header>
      <p className="mt-2 text-ink/80">{career.summary}</p>
      {detail.status === "needs_aid" && (
        <p className="mt-2">
          <Badge tone="warn">Needs aid: {formatInr(finance.funding_gap)} over the budget and loan plan</Badge>
        </p>
      )}

      <div className="mt-6">
        <Tabs
          label={`About ${career.name}`}
          tabs={[
            {
              id: "overview",
              label: "Overview",
              content: (
                <div className="flex flex-col gap-6">
                  <div>
                    <PrismBar points={score.points} score={score.score} />
                    <p className="mt-2 text-sm text-ink/60">Point at, tap or tab to a colour to see what it means.</p>
                  </div>
                  <p className="flex flex-wrap items-center gap-2 rounded-lg bg-paper p-4">
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
    </Card>
  );
});
