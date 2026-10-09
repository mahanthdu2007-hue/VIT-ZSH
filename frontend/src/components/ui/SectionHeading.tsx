type SectionHeadingProps = {
  id: string;
  title: string;
};

/** A large, plain section title. */
export function SectionHeading({ id, title }: SectionHeadingProps) {
  return (
    <h2 id={id} className="text-xl leading-tight sm:text-2xl">
      {title}
    </h2>
  );
}
