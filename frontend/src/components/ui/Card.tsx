import type { HTMLAttributes, ReactNode } from "react";
import { useReveal } from "../../lib/useReveal";

type CardProps = HTMLAttributes<HTMLElement> & {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  as?: "section" | "div" | "article";
};

/** A rounded white tile that rises gently into place the first time it scrolls into view. */
export function Card({ title, description, actions, as: Tag = "section", className = "", children, ...props }: CardProps) {
  const { ref, shown } = useReveal<HTMLDivElement>();
  return (
    <Tag
      ref={ref}
      data-shown={shown || undefined}
      className={`reveal flex h-full min-w-0 flex-col rounded-2xl bg-surface p-6 shadow sm:p-8 ${className}`}
      {...props}
    >
      {(title || actions) && (
        <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            {title && <h2 className="text-lg">{title}</h2>}
            {description && <p className="mt-1 text-sm leading-relaxed text-ink/60">{description}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </Tag>
  );
}
