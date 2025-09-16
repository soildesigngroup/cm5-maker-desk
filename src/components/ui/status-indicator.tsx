import React from 'react';
import { cn } from '@/lib/utils';

type StatusType = 'connected' | 'disconnected' | 'warning' | 'error' | 'testing';

interface StatusIndicatorProps {
  status: StatusType;
  label?: string;
  className?: string;
  showPulse?: boolean;
}

const statusStyles = {
  connected: 'bg-success border-success/30 shadow-[0_0_10px_hsl(var(--success)/0.4)]',
  disconnected: 'bg-muted-foreground border-muted-foreground/30',
  warning: 'bg-warning border-warning/30 shadow-[0_0_10px_hsl(var(--warning)/0.4)]',
  error: 'bg-destructive border-destructive/30 shadow-[0_0_10px_hsl(var(--destructive)/0.4)]',
  testing: 'bg-primary border-primary/30 shadow-[0_0_10px_hsl(var(--primary)/0.4)] animate-pulse',
};

export function StatusIndicator({ 
  status, 
  label, 
  className,
  showPulse = true 
}: StatusIndicatorProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div 
        className={cn(
          'w-3 h-3 rounded-full border-2 hmi-transition',
          statusStyles[status],
          showPulse && status === 'connected' && 'animate-pulse-glow'
        )}
      />
      {label && (
        <span className="text-sm font-medium text-foreground">
          {label}
        </span>
      )}
    </div>
  );
}