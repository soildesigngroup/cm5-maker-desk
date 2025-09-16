import React from 'react';
import { cn } from '@/lib/utils';

interface HMIToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  className?: string;
}

export function HMIToggle({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  className,
}: HMIToggleProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent',
          'hmi-transition focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2',
          'focus:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
          checked 
            ? 'bg-primary shadow-[0_0_10px_hsl(var(--primary)/0.4)]' 
            : 'bg-secondary'
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block h-5 w-5 rounded-full bg-background shadow-lg',
            'transform ring-0 hmi-transition',
            checked ? 'translate-x-5' : 'translate-x-0'
          )}
        />
      </button>
      {(label || description) && (
        <div className="flex flex-col">
          {label && (
            <span className="text-sm font-medium text-foreground">
              {label}
            </span>
          )}
          {description && (
            <span className="text-xs text-muted-foreground">
              {description}
            </span>
          )}
        </div>
      )}
    </div>
  );
}