import type { ReactNode } from "react";
import type { CareerDetail, CityId } from "../../api/client";
import { SectionHeading } from "../ui/SectionHeading";
import { CityDemand } from "./CityDemand";
import { PathwayGraph } from "./PathwayGraph";
import { RiskRadar } from "./RiskRadar";
import { RoiCard } from "./RoiCard";
import { SkillGap } from "./SkillGap";
import { Timeline } from "./Timeline";

type CareerDeepDiveProps = {
  detail: CareerDetail;
  homeCity: CityId | undefined;
  /** The SWOT grid sits beside city demand (§15 order) but is about the top career, so the page passes it in. */
  swot: ReactNode;
};

/** §15 detail panels for the selected career, in dashboard order, as an equal-height bento grid. */
export function CareerDeepDive({ detail, homeCity, swot }: CareerDeepDiveProps) {
  const plan = detail.skill_plan;
  return (
    <section id="closer" aria-labelledby="deep-dive-heading" className="flex scroll-mt-32 flex-col gap-6">
      <SectionHeading
        id="deep-dive-heading"
        eyebrow="A closer look"
        title={detail.career.name}
        description="Risks, skills, the route year by year, where the jobs are and whether the cost pays back."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <RiskRadar risk={detail.risk} />
        <SkillGap plan={plan} />
      </div>
      <PathwayGraph plan={plan} pathwayLabel={detail.pathway.label} />
      <Timeline plan={plan} />
      <div className="grid gap-4 lg:grid-cols-2">
        <CityDemand detail={detail} homeCity={homeCity} />
        {swot}
      </div>
      <RoiCard detail={detail} />
    </section>
  );
}
