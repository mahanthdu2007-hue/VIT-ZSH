import { type KeyboardEvent, type ReactNode, useId, useRef, useState } from "react";

export type Tab = { id: string; label: string; content: ReactNode };

/** Accessible tabs: arrow keys move between tabs, only the open panel is shown. */
export function Tabs({ tabs, label }: { tabs: Tab[]; label: string }) {
  const [active, setActive] = useState(tabs[0]?.id ?? "");
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const base = useId();
  const index = Math.max(0, tabs.findIndex((t) => t.id === active));
  const current = tabs[index];

  const onKeyDown = (event: KeyboardEvent) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = (index + step + tabs.length) % tabs.length;
    const nextTab = tabs[next];
    if (!nextTab) return;
    setActive(nextTab.id);
    buttons.current[next]?.focus();
  };

  if (!current) return null;
  return (
    <div>
      <div role="tablist" aria-label={label} onKeyDown={onKeyDown} className="flex gap-1 rounded-lg bg-paper p-1">
        {tabs.map((tab, i) => (
          <button
            key={tab.id}
            ref={(el) => {
              buttons.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`${base}-tab-${tab.id}`}
            aria-selected={tab.id === current.id}
            aria-controls={`${base}-panel-${tab.id}`}
            tabIndex={tab.id === current.id ? 0 : -1}
            onClick={() => setActive(tab.id)}
            className={`flex-1 rounded-md px-3 py-2 text-sm font-medium ${
              tab.id === current.id ? "border border-line bg-surface text-ink" : "border border-transparent text-ink/60 hover:text-ink"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id={`${base}-panel-${current.id}`}
        aria-labelledby={`${base}-tab-${current.id}`}
        className="pt-6"
      >
        {current.content}
      </div>
    </div>
  );
}
