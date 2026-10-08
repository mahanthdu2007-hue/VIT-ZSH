import type { ConflictDimension, ConflictResult } from "../../api/client";
import { formatPoints } from "../../lib/format";
import { CONFLICT_DIMENSIONS } from "../../lib/labels";
import { Card } from "../ui/Card";

const dimensionLabel = (name: string) => CONFLICT_DIMENSIONS[name]?.label ?? name;

/** §7.6 Parent-Student Conflict Index: the overall meter, each dimension's share, and the top hotspots. */
export function ConflictPanel({ conflict }: { conflict: ConflictResult }) {
  const hotspots = conflict.hotspots
    .map((name) => conflict.dimensions.find((d) => d.name === name))
    .filter((d): d is ConflictDimension => d !== undefined && d.mismatch > 0);

  return (
    <Card
      title="Where student and parents differ"
      description="The Parent-Student Conflict Index compares the two sets of answers. 0 means full agreement."
    >
      <div>
        <p className="flex items-baseline justify-between">
          <span className="font-medium">Conflict index</span>
          <span>
            <span className="font-heading text-xl font-semibold">{Math.round(conflict.index)}</span> of 100
          </span>
        </p>
        <div
          className="mt-2 h-3 overflow-hidden rounded-full bg-line"
          role="meter"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(conflict.index)}
          aria-label="Parent-Student Conflict Index"
        >
          <div className="h-full rounded-full bg-ink" style={{ width: `${conflict.index}%` }} />
        </div>
      </div>

      <div className="mt-6">
        <h3 className="text-base">Biggest differences</h3>
        {hotspots.length > 0 ? (
          <ul className="mt-2 flex flex-col gap-2">
            {hotspots.map((d) => (
              <li key={d.name} className="rounded-lg border border-ink/20 bg-paper px-3 py-2">
                <span className="font-medium">{dimensionLabel(d.name)}</span>
                <span className="block text-sm">
                  {CONFLICT_DIMENSIONS[d.name]?.hotspot(d)}
                  {d.name === "domain" && conflict.student_top_domains.length > 0 &&
                    ` The student leans towards ${conflict.student_top_domains.join(", ")}.`}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2">Student and parents agree on everything we compare.</p>
        )}
      </div>

      <div className="mt-6">
        <h3 className="text-base">Every area we compare</h3>
        <ul className="mt-2 flex flex-col gap-3">
          {conflict.dimensions.map((d) => {
            const max = d.weight * 100;
            return (
              <li key={d.name}>
                <div className="flex justify-between text-sm">
                  <span>{dimensionLabel(d.name)}</span>
                  <span>
                    {formatPoints(d.points)} of {formatPoints(max)}
                  </span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-line" aria-hidden="true">
                  <div className="h-full rounded-full bg-ink" style={{ width: `${d.mismatch * 100}%` }} />
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </Card>
  );
}
