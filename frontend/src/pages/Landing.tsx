import { useState } from "react";
import { Link } from "react-router-dom";
import type { DemoProfile } from "../api/client";
import { useAssess, useDemoProfiles } from "../api/queries";
import { Button } from "../components/ui/Button";
import { Card } from "../components/ui/Card";
import { COMPONENTS } from "../lib/labels";
import { componentColors } from "../theme/tokens";

const trackLinkClass =
  "flex flex-1 flex-col rounded-xl border border-line bg-surface p-4 shadow transition-colors hover:border-ink/40 sm:p-6";

export function Landing() {
  const demos = useDemoProfiles();
  const assess = useAssess();
  const [chosenId, setChosenId] = useState<string | null>(null);

  const runDemo = (profile: DemoProfile) => {
    setChosenId(profile.id);
    assess.mutate({ student: profile.student, parent: profile.parent });
  };

  return (
    <div className="flex flex-col gap-10">
      <section className="max-w-3xl">
        <h1 className="text-xl sm:text-2xl">Find a career path that fits the student, the family budget and the job market.</h1>
        <p className="mt-3 text-ink/80">
          PRISM looks at five things for every career and shows how each one adds up to the final score.
        </p>
        <ul className="mt-4 flex flex-wrap gap-2" aria-label="The five parts of every score">
          {COMPONENTS.map((c) => (
            <li key={c.key} className="flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-sm">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: componentColors[c.key] }} aria-hidden="true" />
              {c.label}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="start-heading">
        <h2 id="start-heading" className="text-lg">
          Start your own assessment
        </h2>
        <p className="mt-1 text-sm text-ink/70">About 15 minutes for the student, then 3 minutes for a parent.</p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <Link to="/assess/school" className={trackLinkClass}>
            <span className="font-heading text-lg font-semibold">I'm in school</span>
            <span className="mt-1 text-ink/70">Class 9 to 12</span>
          </Link>
          <Link to="/assess/college" className={trackLinkClass}>
            <span className="font-heading text-lg font-semibold">I'm in college</span>
            <span className="mt-1 text-ink/70">Any degree, any year</span>
          </Link>
        </div>
      </section>

      <section aria-labelledby="demo-heading">
        <h2 id="demo-heading" className="text-lg">
          Try a demo family
        </h2>
        <p className="mt-1 text-sm text-ink/70">Each one runs the full engine on a ready-made student and parent.</p>
        {demos.isPending && <p className="mt-4">Loading demo families…</p>}
        {demos.isError && (
          <p className="mt-4 text-danger" role="alert">
            Could not load the demo families. Is the backend running on port 8000?
          </p>
        )}
        {assess.isError && (
          <p className="mt-4 text-danger" role="alert">
            The assessment did not finish. Please try again.
          </p>
        )}
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {demos.data?.map((profile) => (
            <Card as="article" key={profile.id} className="flex flex-col">
              <h3 className="text-lg">{profile.name}</h3>
              <p className="mt-1 flex-1 text-ink/80">{profile.summary}</p>
              <Button className="mt-4" onClick={() => runDemo(profile)} disabled={assess.isPending}>
                {assess.isPending && chosenId === profile.id ? "Running the engine…" : `Try ${profile.name}'s family`}
              </Button>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}

