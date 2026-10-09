import type { CareerDetail, CityId } from "../../api/client";
import { CITY_NAMES } from "../../lib/labels";
import { colors } from "../../theme/tokens";
import { Badge } from "../ui/Badge";
import { Card } from "../ui/Card";
import { Meter } from "../ui/Meter";

/** §7.7 Industry Hiring Index inputs: demand for the selected career in each city, best reachable city highlighted. */
export function CityDemand({ detail, homeCity }: { detail: CareerDetail; homeCity: CityId | undefined }) {
  const best = detail.market.best_city;
  const cities = (Object.entries(detail.career.city_demand) as [CityId, number][]).sort((a, b) => b[1] - a[1]);
  return (
    <Card
      title="Where the jobs are"
      description={`Hiring demand for ${detail.career.name} in each city, out of 100. ${CITY_NAMES[best as CityId] ?? best} is the best city you can reach.`}
    >
      <ul className="flex flex-1 flex-col justify-between gap-4">
        {cities.map(([city, demand]) => {
          const isBest = city === best;
          return (
            <li key={city} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between gap-2 text-sm">
                <span className="flex flex-wrap items-center gap-2">
                  <span className={isBest ? "font-medium" : undefined}>{CITY_NAMES[city]}</span>
                  {isBest && <Badge tone="good">Best for you</Badge>}
                  {city === homeCity && <Badge>Home</Badge>}
                </span>
                <span className="font-medium tabular-nums">{Math.round(demand * 100)}</span>
              </div>
              <Meter value={demand} color={isBest ? colors.marketDemand : `${colors.marketDemand}66`} />
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
