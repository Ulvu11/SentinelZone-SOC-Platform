interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4 mb-6">
      <div className="min-w-0">
        {eyebrow && (
          <p className="text-soc-accent text-[11px] font-medium tracking-[0.16em] uppercase mb-1">
            {eyebrow}
          </p>
        )}
        <h1 className="text-2xl font-bold text-soc-text">{title}</h1>
        {description && (
          <p className="text-sm text-soc-muted mt-1">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-3">{actions}</div>
      )}
    </div>
  );
}
