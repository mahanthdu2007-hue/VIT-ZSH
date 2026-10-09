import { motion, useReducedMotion } from "framer-motion";
import { type KeyboardEvent, type ReactNode, useId, useRef, useState } from "react";
import { timing } from "../../theme/tokens";

export type Tab = { id: string; label: string; content: ReactNode };

/** Accessible segmented control: arrow keys move between tabs, a pill slides to the open one, the panel fades in. */
export function Tabs({ tabs, label }: { tabs: Tab[]; label: string }) {
  const [active, setActive] = useState(tabs[0]?.id ?? "");
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  const base = useId();
  const reduce = useReducedMotion();
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
      <div
        role="tablist"
        aria-label={label}
        onKeyDown={onKeyDown}
        className="no-scrollbar flex gap-1 overflow-x-auto rounded-full bg-paper p-1"
      >
        {tabs.map((tab, i) => {
          const selected = tab.id === current.id;
          return (
            <button
              key={tab.id}
              ref={(el) => {
                buttons.current[i] = el;
              }}
              type="button"
              role="tab"
              id={`${base}-tab-${tab.id}`}
              aria-selected={selected}
              aria-controls={`${base}-panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(tab.id)}
              className={`relative flex-1 whitespace-nowrap rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                selected ? "text-ink" : "text-ink/60 hover:text-ink"
              }`}
            >
              {selected && (
                <motion.span
                  layoutId={reduce ? undefined : `${base}-pill`}
                  className="absolute inset-0 rounded-full bg-surface shadow"
                  transition={timing.pill}
                  aria-hidden="true"
                />
              )}
              <span className="relative">{tab.label}</span>
            </button>
          );
        })}
      </div>
      <motion.div
        key={current.id}
        role="tabpanel"
        id={`${base}-panel-${current.id}`}
        aria-labelledby={`${base}-tab-${current.id}`}
        className="pt-6"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: timing.base, ease: timing.ease }}
      >
        {current.content}
      </motion.div>
    </div>
  );
}
