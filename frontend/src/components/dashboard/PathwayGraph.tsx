import { type Edge, MarkerType, type Node, Position, ReactFlow, type ReactFlowInstance } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useRef } from "react";
import type { SkillPlan } from "../../api/client";
import { colors } from "../../theme/tokens";
import { Card } from "../ui/Card";

const NODE_WIDTH = 144;
const NODE_GAP = 32;
const NODE_HEIGHT = 56;
const MIN_READABLE_ZOOM = 0.85;
const SIDE_PADDING = 16;

const NODE_CLASS = {
  pathway: "!w-[144px] !rounded-lg !border-ink !bg-surface !text-sm !text-ink",
  learning: "!w-[144px] !rounded-lg !border-studentFit !bg-studentFit/10 !text-sm !text-ink",
};

function buildGraph(plan: SkillPlan): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = plan.roadmap.map((step, i) => ({
    id: String(i),
    position: { x: i * (NODE_WIDTH + NODE_GAP), y: 0 },
    data: { label: step.text },
    className: NODE_CLASS[step.kind],
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  }));
  const edges: Edge[] = nodes.slice(1).map((node, i) => ({
    id: `${i}-${node.id}`,
    source: String(i),
    target: node.id,
    style: { stroke: colors.ink },
    markerEnd: { type: MarkerType.ArrowClosed, color: colors.ink },
  }));
  return { nodes, edges };
}

/** §8 roadmap as a left-to-right graph: course steps and learning steps, read-only. */
export function PathwayGraph({ plan, pathwayLabel }: { plan: SkillPlan; pathwayLabel: string }) {
  const { nodes, edges } = buildGraph(plan);
  const container = useRef<HTMLDivElement>(null);
  const hasLearning = plan.roadmap.some((step) => step.kind === "learning");

  // Fit everything when there is room; on a narrow screen keep the text readable and start from the first step.
  const place = (flow: ReactFlowInstance) => {
    const box = container.current?.getBoundingClientRect();
    if (!box) return;
    const fullWidth = nodes.length * (NODE_WIDTH + NODE_GAP) - NODE_GAP;
    const zoom = Math.min(1, Math.max(MIN_READABLE_ZOOM, (box.width - 2 * SIDE_PADDING) / fullWidth));
    const x = zoom * fullWidth + 2 * SIDE_PADDING <= box.width ? (box.width - zoom * fullWidth) / 2 : SIDE_PADDING;
    void flow.setViewport({ x, y: box.height / 2 - (NODE_HEIGHT / 2) * zoom, zoom });
  };

  return (
    <Card title="Your route" description={`${pathwayLabel}, with the skills to learn along the way.`}>
      <div
        ref={container}
        className="h-32 rounded-lg border border-line bg-paper"
        role="img"
        aria-label={`Route: ${plan.roadmap.map((step) => step.text).join(", then ")}.`}
      >
        <ReactFlow
          key={plan.career_id}
          nodes={nodes}
          edges={edges}
          onInit={place}
          nodesDraggable={false}
          nodesConnectable={false}
          nodesFocusable={false}
          edgesFocusable={false}
          elementsSelectable={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          zoomOnDoubleClick={false}
          preventScrolling={false}
          panOnDrag
          minZoom={MIN_READABLE_ZOOM}
          maxZoom={1}
        />
      </div>
      <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink/70">
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-sm border border-ink bg-surface" aria-hidden="true" />
          Course step
        </span>
        {hasLearning && (
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-sm border border-studentFit bg-studentFit/10" aria-hidden="true" />
            Skill to learn
          </span>
        )}
        <span>Drag sideways to see every step.</span>
      </p>
    </Card>
  );
}
