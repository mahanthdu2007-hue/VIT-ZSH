import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";
import { timing } from "../../theme/tokens";

export type NavSection = { id: string; label: string };

type SectionNavProps = {
  sections: NavSection[];
  active: string;
  onSelect: (id: string) => void;
  actions?: ReactNode;
};

/** A floating, frosted bar under the header: one button per results page, with a pill that glides to the open page. */
export function SectionNav({ sections, active, onSelect, actions }: SectionNavProps) {
  const reduce = useReducedMotion();
  return (
    <nav aria-label="Results pages" className="sticky top-14 z-30 -mx-1">
      <div className="flex items-center gap-2 rounded-full bg-surface/80 p-1.5 shadow backdrop-blur-xl backdrop-saturate-150">
        <ul className="no-scrollbar flex min-w-0 flex-1 gap-1 overflow-x-auto">
          {sections.map((section) => {
            const current = section.id === active;
            return (
              <li key={section.id} className="shrink-0">
                <button
                  type="button"
                  aria-current={current ? "page" : undefined}
                  onClick={() => onSelect(section.id)}
                  className={`relative block rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                    current ? "text-surface" : "text-ink/60 hover:text-ink"
                  }`}
                >
                  {current && (
                    <motion.span
                      layoutId={reduce ? undefined : "section-nav-pill"}
                      className="absolute inset-0 rounded-full bg-ink"
                      transition={timing.pill}
                      aria-hidden="true"
                    />
                  )}
                  <span className="relative">{section.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
        {actions && <div className="hidden shrink-0 items-center gap-1 md:flex">{actions}</div>}
      </div>
    </nav>
  );
}
