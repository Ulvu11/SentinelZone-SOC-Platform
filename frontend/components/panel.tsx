import { SectionHeader } from "@/components/section-header";

export function Panel({
  title,
  subtitle,
  action,
  children,
  id,
  className = "",
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  id?: string;
  className?: string;
}) {
  return (
    <section
      id={id}
      className={`min-w-0 rounded-lg border border-soc-line bg-soc-panel p-4 ${className}`}
    >
      <SectionHeader title={title} subtitle={subtitle} action={action} />
      {children}
    </section>
  );
}

export function DetailList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2 text-sm text-soc-text">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <span aria-hidden="true" className="text-soc-accent">
            •
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}
