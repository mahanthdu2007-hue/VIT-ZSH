import type { CareerDetail, CityId } from "../../api/client";
import { CITY_NAMES } from "../../lib/labels";
import { Card } from "../ui/Card";

/** §7.7 Industry Hiring Index inputs: demand for the selected career in each city, best reachable city highlighted. */
export function CityDemand({ detail, homeCity }: { detail: CareerDetail; homeCity: CityId | undefined }) {
  const best = detail.market.best_city;
  const cities = (Object.entries(detail.career.city_demand) as [CityId, number][]).sort((a, b) => b[1] - a[1]);
  return (
    <Card
      title="Where the jobs are"
      description={`Hiring demand for ${detail.career.name} in each city, out of 100. ${CITY_NAMES[best as CityId] ?? best} is the best city you can reach.`}
    >
      <ul className="flex flex-col gap-3">
        {cities.map(([city, demand]) => {
          const isBest = city === best;
          return (
            <li key={city}>
              <div className="flex justify-between gap-2 text-sm">
                <span className={isBest ? "font-medium" : undefined}>
                  {CITY_NAMES[city]}
                  {isBest && " · best for you"}
                  {city === homeCity && " · home"}
                </span>
                <span className="font-medium">{Math.round(demand * 100)}</span>
              </div>
              <div className="mt-1 h-2 rounded-full bg-line">
                <div
                  className={`h-full rounded-full ${isBest ? "bg-marketDemand" : "bg-marketDemand/40"}`}
                  style={{ width: `${demand * 100}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
