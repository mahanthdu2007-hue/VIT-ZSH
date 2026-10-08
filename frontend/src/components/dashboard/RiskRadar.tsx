import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import type { RiskRadar as RiskRadarData } from "../../api/client";
import { RISK_AXES } from "../../lib/labels";
import { colors, fontSizes } from "../../theme/tokens";
import { Card } from "../ui/Card";

type Point = { label: string; meaning: string; value: number };

function RiskTooltip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  const point = active ? payload?.[0]?.payload : undefined;
  if (!point) return null;
  return (
    <div className="max-w-56 rounded-lg bg-ink px-3 py-2 text-sm text-surface shadow-lg">
      <p className="font-medium">
        {point.label}: {Math.round(point.value * 100)} of 100
      </p>
      <p className="mt-1">{point.meaning}</p>
    </div>
  );
}

type TickProps = {
  x?: number | string;
  y?: number | string;
  textAnchor?: "start" | "middle" | "end";
  payload?: { value: string };
};

/** Axis names on two lines, so they fit beside the chart on a phone. */
function AxisLabel({ x = 0, y = 0, textAnchor = "middle", payload }: TickProps) {
  const words = (payload?.value ?? "").split(" ");
  const half = Math.ceil(words.length / 2);
  const lines = words.length > 1 ? [words.slice(0, half).join(" "), words.slice(half).join(" ")] : words;
  return (
    <text x={x} y={y} textAnchor={textAnchor} fill={colors.ink} fontSize={fontSizes.sm}>
      {lines.map((line, i) => (
        <tspan key={line} x={x} dy={i === 0 ? `${(1 - lines.length) * 0.6 + 0.35}em` : "1.2em"}>
          {line}
        </tspan>
      ))}
    </text>
  );
}

/** §7.8 Risk Radar: six risks from 0 (none) to 100 (high), for the selected career. */
export function RiskRadar({ risk }: { risk: RiskRadarData }) {
  const data: Point[] = RISK_AXES.map((axis) => ({ label: axis.label, meaning: axis.meaning, value: risk[axis.key] }));
  return (
    <Card title="Risks to watch" description="Further from the centre means a bigger risk. 0 is none, 100 is high.">
      <div className="h-64" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="62%">
            <PolarGrid stroke={colors.line} />
            <PolarAngleAxis dataKey="label" tick={<AxisLabel />} />
            <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
            <Radar
              dataKey="value"
              stroke={colors.ink}
              strokeWidth={2}
              fill={colors.ink}
              fillOpacity={0.15}
              dot={{ r: 4, fill: colors.ink }}
              isAnimationActive={false}
            />
            <Tooltip content={<RiskTooltip />} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 grid gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
        {data.map((point) => (
          <li key={point.label} className="flex justify-between gap-2">
            <span>{point.label}</span>
            <span className="font-medium">{Math.round(point.value * 100)}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
