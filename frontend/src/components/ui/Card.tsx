import type { HTMLAttributes, ReactNode } from "react";

type CardProps = HTMLAttributes<HTMLElement> & {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  as?: "section" | "div" | "article";
};

export function Card({ title, description, actions, as: Tag = "section", className = "", children, ...props }: CardProps) {
  return (
    <Tag className={`flex h-full flex-col rounded-xl border border-line bg-surface p-5 sm:p-6 ${className}`} {...props}>
      {(title || actions) && (
        <header className="mb-5 flex flex-wrap items-start justify-between gap-2">
          <div>
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
