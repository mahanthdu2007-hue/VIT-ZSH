import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { AssessmentResult } from "../api/client";
import { useAssessment, useAssessmentInputs, useCareers, useExplanations } from "../api/queries";
import { CareerDetailPanel } from "../components/dashboard/CareerDetailPanel";
import { CareerDeepDive } from "../components/dashboard/CareerDeepDive";
import { ConflictPanel } from "../components/dashboard/ConflictPanel";
import { MiddlePathCard } from "../components/dashboard/MiddlePathCard";
import { StretchOptions } from "../components/dashboard/StretchOptions";
import { SwotGrid } from "../components/dashboard/SwotGrid";
import { TopCareers } from "../components/dashboard/TopCareers";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { WhatIfDrawer } from "../components/whatif/WhatIfDrawer";

export function Dashboard() {
  const { id = "" } = useParams();
  const assessment = useAssessment(id);

  if (assessment.isPending) {
    return (
      <p role="status" className="py-12 text-center">
        Loading your results…
      </p>
    );
  }
  if (assessment.isError) {
    return (
      <Card className="mx-auto max-w-xl text-center">
        <h1 className="text-xl">These results are no longer open</h1>
        <p className="mt-2 text-ink/80">
          Results are kept only while this tab stays open, so reloading the page clears them. Run the assessment again
          or try a demo family.
        </p>
        <Link to="/" className="mt-4 inline-block font-medium text-studentFit underline">
          Back to the start
        </Link>
      </Card>
    );
  }
  return <DashboardView result={assessment.data} />;
}

const WIDE_LAYOUT = "(min-width: 1024px)";

function DashboardView({ result }: { result: AssessmentResult }) {
  const careers = useCareers();
  const inputs = useAssessmentInputs(result.id);
  const explanations = useExplanations(result);
  const [whatIfOpen, setWhatIfOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(result.ranking[0]?.career_id ?? null);
  const detailHeadingRef = useRef<HTMLHeadingElement>(null);

  const careerName = (careerId: string) =>
    result.details[careerId]?.career.name ?? careers.data?.find((c) => c.id === careerId)?.name ?? careerId;

  const select = (careerId: string) => {
    setSelectedId(careerId);
    const heading = detailHeadingRef.current;
    if (!heading) return;
    heading.focus({ preventScroll: true });
    if (!window.matchMedia(WIDE_LAYOUT).matches) heading.scrollIntoView({ block: "start" });
  };

  const selected = selectedId ? result.details[selectedId] : undefined;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl">Your family's career map</h1>
          <p className="mt-1 text-ink/70">
            Every score is worked out from your answers, the family budget and job-market data. Money values are
            indicative estimates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          {inputs.data && <Button onClick={() => setWhatIfOpen(true)}>Try a what-if</Button>}
          <Link to="/" className="rounded font-medium text-studentFit underline">
            Start a new assessment
          </Link>
        </div>
      </header>

      {inputs.data && (
        <WhatIfDrawer
          open={whatIfOpen}
          onClose={() => setWhatIfOpen(false)}
          assessmentId={result.id}
          inputs={inputs.data}
          ranking={result.ranking}
        />
      )}

      {result.ranking.length === 0 || !selected ? (
        <Card title="No affordable careers yet">
          <p>
            None of the careers fit the current budget and loan plan. The stretch options below show scholarships and
            cheaper routes that can close the gap.
          </p>
        </Card>
      ) : (
        <div className="grid items-start gap-6 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <TopCareers ranking={result.ranking} selectedId={selected.career.id} onSelect={select} />
          </div>
          <div className="lg:col-span-3">
            <CareerDetailPanel
              ref={detailHeadingRef}
              detail={selected}
              explanations={explanations.data}
              explanationsRefreshing={explanations.isFetching}
            />
          </div>
        </div>
      )}

      <section aria-labelledby="family-heading" className="flex flex-col gap-4">
        <h2 id="family-heading" className="text-lg">
          Family alignment
        </h2>
        <div className="grid items-start gap-6 lg:grid-cols-2">
          <ConflictPanel conflict={result.conflict} />
          <MiddlePathCard middlePath={result.middle_path} careerName={careerName} onSelect={select} />
        </div>
      </section>

      {selected ? (
        <CareerDeepDive
          detail={selected}
          homeCity={inputs.data?.student.home_city}
          swot={<SwotGrid swot={result.swot} topCareerName={result.ranking[0]?.name} />}
        />
      ) : (
        <SwotGrid swot={result.swot} topCareerName={result.ranking[0]?.name} />
      )}

      <StretchOptions options={result.stretch_options} details={result.details} careerName={careerName} />
    </div>
  );
}
