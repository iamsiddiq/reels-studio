import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

interface PageHeaderProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}

export function PageHeader({ icon: Icon, title, description, action }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex items-start gap-3.5">
        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-5.5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-balance">{title}</h1>
          <p className="mt-1 text-sm text-muted-foreground text-balance">{description}</p>
        </div>
      </div>
      {action}
    </div>
  );
}
