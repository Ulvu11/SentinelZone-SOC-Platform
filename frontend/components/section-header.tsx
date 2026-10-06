interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export function SectionHeader({ title, subtitle, action }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h2 className="text-sm font-semibold text-soc-text">{title}</h2>
        {subtitle && (
          <p className="text-xs text-soc-muted mt-0.5">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}
