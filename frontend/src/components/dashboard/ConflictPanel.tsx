import type { ConflictDimension, ConflictResult } from "../../api/client";
import { CONFLICT_DIMENSIONS } from "../../lib/labels";
import { colors } from "../../theme/tokens";
import { Card } from "../ui/Card";
import { CountUp } from "../ui/CountUp";
import { Meter } from "../ui/Meter";

const dimensionLabel = (name: string) => CONFLICT_DIMENSIONS[name]?.label ?? name;

/** §7.6 Parent-Student Conflict Index: the overall meter, each dimension's share, and the top hotspots. */
export function ConflictPanel({ conflict }: { conflict: ConflictResult }) {
  const hotspots = conflict.hotspots
    .map((name) => conflict.dimensions.find((d) => d.name === name))
    .filter((d): d is ConflictDimension => d !== undefined && d.mismatch > 0);

  return (
    <Card
      title="Where student and parents differ"
    >
      <div
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(conflict.index)}
        aria-label="Parent-Student Conflict Index"
      >
        <p className="flex items-baseline justify-between">
          <span className="font-medium">Conflict index</span>
          <span className="text-ink/60">
            <CountUp
              value={conflict.index}
              format={(v) => String(Math.round(v))}
              className="text-2xl font-semibold tracking-tight text-ink"
            />{" "}
            of 100
          </span>
        </p>
        <div className="mt-2">
          <Meter value={conflict.index / 100} color={colors.ink} height="h-3" />
        </div>
      </div>

      <div className="mt-8">
        <h3 className="text-base">Biggest differences</h3>
        {hotspots.length > 0 ? (
          <ul className="mt-3 grid gap-3 sm:grid-cols-2">
            {hotspots.map((d) => (
              <li key={d.name} className="rounded-xl bg-paper p-4">
                <span className="font-medium">{dimensionLabel(d.name)}</span>
                <span className="mt-1 block text-sm leading-snug text-ink/70">
                  {CONFLICT_DIMENSIONS[d.name]?.hotspot(d)}
                  {d.name === "domain" && conflict.student_top_domains.length > 0 &&
                    ` The student leans towards ${conflict.student_top_domains.join(", ")}.`}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3">Student and parents agree on everything we compare.</p>
        )}
      </div>
    </Card>
  );
}
