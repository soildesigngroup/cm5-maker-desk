import React from 'react';
import { cn } from '@/lib/utils';

interface HMISliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  unit?: string;
  className?: string;
  disabled?: boolean;
}

export function HMISlider({
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  label,
  unit,
  className,
  disabled = false,
}: HMISliderProps) {
  const percentage = ((value - min) / (max - min)) * 100;

  return (
    <div className={cn('w-full space-y-2', className)}>
      {label && (
        <div className="flex justify-between items-center">
          <label className="text-sm font-medium text-foreground">{label}</label>
          <span className="text-sm text-muted-foreground font-mono">
            {value}{unit && ` ${unit}`}
          </span>
        </div>
      )}
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          disabled={disabled}
          className={cn(
            'w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer',
            'focus:outline-none focus:ring-2 focus:ring-primary/50',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            '[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5',
            '[&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary',
            '[&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary-foreground',
            '[&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:hmi-transition',
            '[&::-webkit-slider-thumb]:hover:scale-110',
            '[&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:rounded-full',
            '[&::-moz-range-thumb]:bg-primary [&::-moz-range-thumb]:border-0',
            '[&::-moz-range-thumb]:shadow-lg [&::-moz-range-thumb]:cursor-pointer'
          )}
        />
        <div 
          className="absolute top-0 left-0 h-2 bg-primary rounded-lg pointer-events-none hmi-transition"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}