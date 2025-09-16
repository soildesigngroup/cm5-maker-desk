import React from 'react';
import { cn } from '@/lib/utils';

interface HMIDisplayProps {
  value: string | number;
  label?: string;
  unit?: string;
  className?: string;
  variant?: 'default' | 'large' | 'critical';
  status?: 'normal' | 'warning' | 'error';
}

const variants = {
  default: 'text-2xl',
  large: 'text-4xl',
  critical: 'text-3xl font-bold',
};

const statusStyles = {
  normal: 'text-foreground',
  warning: 'text-warning',
  error: 'text-destructive',
};

export function HMIDisplay({
  value,
  label,
  unit,
  className,
  variant = 'default',
  status = 'normal',
}: HMIDisplayProps) {
  return (
    <div className={cn('text-center space-y-1', className)}>
      {label && (
        <div className="text-sm text-muted-foreground font-medium uppercase tracking-wide">
          {label}
        </div>
      )}
      <div className={cn(
        'font-mono tabular-nums hmi-transition',
        variants[variant],
        statusStyles[status]
      )}>
        {value}{unit && <span className="text-muted-foreground ml-1">{unit}</span>}
      </div>
    </div>
  );
}