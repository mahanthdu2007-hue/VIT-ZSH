import { motion } from "framer-motion";
import { type ReactNode, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { AssessmentResult } from "../api/client";
import { useAssessment, useAssessmentInputs, useCareers, useExplanations } from "../api/queries";
import { ChatPanel } from "../components/chat/ChatPanel";
import { AtAGlance } from "../components/dashboard/AtAGlance";
import { CareerDetailPanel } from "../components/dashboard/CareerDetailPanel";
import { CareerDeepDive } from "../components/dashboard/CareerDeepDive";
import { ConflictPanel } from "../components/dashboard/ConflictPanel";
import { MiddlePathCard } from "../components/dashboard/MiddlePathCard";
import { StretchOptions } from "../components/dashboard/StretchOptions";
import { SwotGrid } from "../components/dashboard/SwotGrid";
import { TopCareers } from "../components/dashboard/TopCareers";
import { type NavSection, SectionNav } from "../components/layout/SectionNav";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { SectionHeading } from "../components/ui/SectionHeading";
import { WhatIfDrawer } from "../components/whatif/WhatIfDrawer";
import { timing } from "../theme/tokens";

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

const SECTIONS: NavSection[] = [
  { id: "overview", label: "Overview" },
  { id: "careers", label: "Careers" },
  { id: "family", label: "Family" },
  { id: "closer", label: "Closer look" },
  { id: "stretch", label: "Stretch options" },
];

function DashboardView({ result }: { result: AssessmentResult }) {
  const careers = useCareers();
  const inputs = useAssessmentInputs(result.id);
  const explanations = useExplanations(result);
  const [whatIfOpen, setWhatIfOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(result.ranking[0]?.career_id ?? null);
  const [page, setPage] = useState(SECTIONS[0]?.id ?? "overview");
  const detailHeadingRef = useRef<HTMLHeadingElement>(null);

  const openPage = (id: string) => {
    setPage(id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const careerName = (careerId: string) =>
    result.details[careerId]?.career.name ?? careers.data?.find((c) => c.id === careerId)?.name ?? careerId;

  const select = (careerId: string) => {
    setSelectedId(careerId);
    if (page !== "careers") {
      openPage("careers");
      return;
    }
    const heading = detailHeadingRef.current;
    if (!heading) return;
    heading.focus({ preventScroll: true });
    if (!window.matchMedia(WIDE_LAYOUT).matches) heading.scrollIntoView({ block: "start" });
  };

  const selected = selectedId ? result.details[selectedId] : undefined;

  const navActions = (
    <>
      <Button variant="ghost" className="min-h-8 px-4 py-1 text-sm" onClick={() => setChatOpen(true)}>
        Ask PRISM
      </Button>
      {inputs.data && (
        <Button className="min-h-8 px-4 py-1 text-sm" onClick={() => setWhatIfOpen(true)}>
          Try a what-if
        </Button>
      )}
    </>
  );

  return (
    <div className="flex flex-col gap-8 sm:gap-12">
      <header className="flex flex-col gap-6">
        <div className="max-w-3xl">
          <p className="text-sm font-medium text-studentFit">Your results</p>
          <h1 className="mt-2 text-2xl leading-tight sm:text-3xl">Your family's career map</h1>
          <p className="mt-3 text-lg leading-relaxed text-ink/60">
            Every score is worked out from your answers, the family budget and job-market data. Money values are
            indicative estimates.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => setChatOpen(true)}>Ask PRISM</Button>
          {inputs.data && (
            <Button variant="secondary" onClick={() => setWhatIfOpen(true)}>
              Try a what-if
            </Button>
          )}
          <Link to="/" className="rounded px-2 font-medium text-studentFit hover:underline">
            Start a new assessment
          </Link>
        </div>
      </header>

      <SectionNav sections={SECTIONS} active={page} onSelect={openPage} actions={navActions} />

      {inputs.data && (
        <WhatIfDrawer
          open={whatIfOpen}
          onClose={() => setWhatIfOpen(false)}
          assessmentId={result.id}
          inputs={inputs.data}
          ranking={result.ranking}
        />
      )}

      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        result={result}
        careerName={careerName}
        dreamCareerId={inputs.data?.student.dream_career_id}
      />

      <Page id="overview" page={page} onNext={openPage}>
        <AtAGlance result={result} onExplore={() => openPage("careers")} />
      </Page>

      <Page id="careers" page={page} onNext={openPage}>
      <section id="careers" aria-labelledby="careers-heading" className="flex scroll-mt-32 flex-col gap-6">
        <SectionHeading
          id="careers-heading"
          eyebrow="Ranked for your family"
          title="Your careers, one by one"
          description="Choose a career to see how its score adds up, why it fits, and the scholarships and exams on its route."
        />
        {result.ranking.length === 0 || !selected ? (
          <Card title="No affordable careers yet">
            <p>
              None of the careers fit the current budget and loan plan. The stretch options below show scholarships and
              cheaper routes that can close the gap.
            </p>
          </Card>
        ) : (
          <div className="grid gap-4 lg:min-h-career-row lg:grid-cols-5">
            <div className="relative lg:col-span-2">
              <TopCareers ranking={result.ranking} selectedId={selected.career.id} onSelect={select} />
            </div>
            <div className="min-w-0 lg:col-span-3">
              <CareerDetailPanel
                ref={detailHeadingRef}
                detail={selected}
                explanations={explanations.data}
                explanationsRefreshing={explanations.isFetching}
              />
            </div>
          </div>
        )}
      </section>
      </Page>

      <Page id="family" page={page} onNext={openPage}>
      <section id="family" aria-labelledby="family-heading" className="flex scroll-mt-32 flex-col gap-6">
        <SectionHeading id="family-heading" eyebrow="Family alignment" title="Where you differ, and a path you can share" />
        <div className="grid gap-4 lg:grid-cols-2">
          <ConflictPanel conflict={result.conflict} />
          <MiddlePathCard middlePath={result.middle_path} careerName={careerName} onSelect={select} />
        </div>
      </section>
      </Page>

      <Page id="closer" page={page} onNext={openPage}>
      {selected ? (
        <CareerDeepDive
          detail={selected}
          homeCity={inputs.data?.student.home_city}
          swot={<SwotGrid swot={result.swot} topCareerName={result.ranking[0]?.name} />}
        />
      ) : (
        <section id="closer" className="scroll-mt-32">
          <SwotGrid swot={result.swot} topCareerName={result.ranking[0]?.name} />
        </section>
      )}
      </Page>

      <Page id="stretch" page={page} onNext={openPage}>
      <section id="stretch" aria-labelledby="stretch-heading" className="flex scroll-mt-32 flex-col gap-6">
        <SectionHeading
          id="stretch-heading"
          eyebrow="Never a dead end"
          title="Stretch options with aid"
          description="Careers that suit the student well but cost more than the budget and loan plan allow. They are not ruled out."
        />
        <StretchOptions options={result.stretch_options} details={result.details} careerName={careerName} />
      </section>
      </Page>
    </div>
  );
}

type PageProps = { id: string; page: string; onNext: (id: string) => void; children: ReactNode };

/** One results page: shown only when open, fades in, and ends with a button to the next page. */
function Page({ id, page, onNext, children }: PageProps) {
  if (id !== page) return null;
  const index = SECTIONS.findIndex((s) => s.id === id);
  const next = SECTIONS[index + 1];
  const previous = SECTIONS[index - 1];
  return (
    <motion.div
      className="flex flex-col gap-10"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: timing.base, ease: timing.ease }}
    >
      {children}
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink/10 pt-6">
        {previous ? (
          <Button variant="ghost" onClick={() => onNext(previous.id)}>
            <span aria-hidden="true">←</span> {previous.label}
          </Button>
        ) : (
          <span />
        )}
        {next && (
          <Button onClick={() => onNext(next.id)}>
            Next: {next.label} <span aria-hidden="true">→</span>
          </Button>
        )}
      </div>
    </motion.div>
  );
}
