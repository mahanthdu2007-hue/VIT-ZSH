import type { ReactNode } from "react";
import type { CareerDetail, CityId } from "../../api/client";
import { CityDemand } from "./CityDemand";
import { ExamsAndScholarships } from "./ExamsAndScholarships";
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

/** §15 detail panels for the selected career, in dashboard order. */
export function CareerDeepDive({ detail, homeCity, swot }: CareerDeepDiveProps) {
  const plan = detail.skill_plan;
  return (
    <section aria-labelledby="deep-dive-heading" className="flex flex-col gap-6">
      <h2 id="deep-dive-heading" className="text-lg">
        A closer look at {detail.career.name}
      </h2>
      <div className="grid items-stretch gap-6 lg:grid-cols-2">
        <RiskRadar risk={detail.risk} />
        <SkillGap plan={plan} />
      </div>
      <div className="grid items-stretch gap-6 lg:grid-cols-5">
        <div className="min-w-0 lg:col-span-3">
          <PathwayGraph plan={plan} pathwayLabel={detail.pathway.label} />
        </div>
        <div className="lg:col-span-2">
          <Timeline plan={plan} />
        </div>
      </div>
      <div className="grid items-stretch gap-6 lg:grid-cols-2">
        <CityDemand detail={detail} homeCity={homeCity} />
        {swot}
      </div>
      <div className="grid items-stretch gap-6 lg:grid-cols-2">
        <RoiCard detail={detail} />
        <ExamsAndScholarships detail={detail} />
      </div>
    </section>
  );
}
