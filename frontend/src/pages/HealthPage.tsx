import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../api/client";

export function HealthPage() {
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth });

  return (
    <main className="mx-auto max-w-xl px-4 py-12">
      <h1 className="text-2xl">PRISM Engine</h1>
      <p className="mt-2 text-sm">System status</p>

      <section className="mt-6 rounded-lg border border-line bg-surface p-6">
        {health.isPending && <p>Checking the server…</p>}
        {health.isError && (
          <p className="text-parentAlignment">
            Could not reach the server. Is the backend running on port 8000?
          </p>
        )}
        {health.data && (
          <dl className="grid grid-cols-2 gap-y-3">
            <dt className="font-medium">Status</dt>
            <dd>{health.data.status}</dd>
            <dt className="font-medium">System 1 backend</dt>
            <dd>{health.data.system1}</dd>
            <dt className="font-medium">LLM provider</dt>
            <dd>{health.data.llm}</dd>
            <dt className="font-medium">Demo mode</dt>
            <dd>{health.data.demo_mode ? "On" : "Off"}</dd>
          </dl>
        )}
      </section>
    </main>
  );
}
