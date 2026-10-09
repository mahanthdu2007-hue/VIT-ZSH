import { Link, Outlet } from "react-router-dom";
import { useHealth } from "../../api/queries";
import { componentColors } from "../../theme/tokens";

function PrismMark() {
  return (
    <span className="flex h-3 w-6 overflow-hidden rounded-sm" aria-hidden="true">
      {Object.values(componentColors).map((color) => (
        <span key={color} className="flex-1" style={{ backgroundColor: color }} />
      ))}
    </span>
  );
}

export function AppShell() {
  const health = useHealth();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-ink/10 bg-paper/75 backdrop-blur-xl backdrop-saturate-150">
        <div className="mx-auto flex h-12 max-w-6xl items-center justify-between gap-4 px-4">
          <Link to="/" className="flex items-center gap-2 rounded text-base font-semibold tracking-tight">
            <PrismMark />
            PRISM Engine
          </Link>
          <p className="hidden text-sm text-ink/60 sm:block">Career choices the whole family can understand</p>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:py-12">
        <Outlet />
      </main>
      <footer className="border-t border-ink/10">
        <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-5 text-sm text-ink/60">
          <p>All money values and salaries are indicative estimates for guidance only.</p>
          <p className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${health.data ? "bg-financialFit" : health.isError ? "bg-danger" : "bg-line"}`}
              aria-hidden="true"
            />
            {health.data
              ? `Engine online · System 1: ${health.data.system1}`
              : health.isError
                ? "Engine offline: start the backend on port 8000"
                : "Checking the engine…"}
          </p>
        </div>
      </footer>
    </div>
  );
}
