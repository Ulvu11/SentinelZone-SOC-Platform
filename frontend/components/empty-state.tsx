import { Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="text-soc-muted mb-4">{icon ?? <Inbox size={48} />}</div>
      <h3 className="text-sm font-semibold text-soc-text mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-soc-muted max-w-xs">{description}</p>
      )}
    </div>
  );
}
