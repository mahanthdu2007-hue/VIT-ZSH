import type { ReactNode } from "react";

type SectionHeadingProps = {
  id: string;
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
};

/** A large section title with a small label above it, in the style of a product page. */
export function SectionHeading({ id, eyebrow, title, description }: SectionHeadingProps) {
  return (
    <div className="max-w-3xl">
      <p className="text-sm font-medium text-studentFit">{eyebrow}</p>
      <h2 id={id} className="mt-1 text-xl leading-tight sm:text-2xl">
        {title}
      </h2>
      {description && <p className="mt-2 text-ink/60">{description}</p>}
    </div>
  );
}
