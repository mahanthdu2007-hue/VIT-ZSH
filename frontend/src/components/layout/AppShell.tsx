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
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 rounded font-heading text-lg font-semibold">
            <PrismMark />
            PRISM Engine
          </Link>
          <p className="hidden text-sm text-ink/70 sm:block">Career choices the whole family can understand</p>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:py-10">
        <Outlet />
      </main>
      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-6xl flex-wrap justify-between gap-2 px-4 py-3 text-sm text-ink/70">
          <p>All money values and salaries are indicative estimates for guidance only.</p>
          <p>
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
