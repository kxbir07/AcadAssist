interface ProgressBarProps {
  value: number;
  color?: string;
  height?: number;
  showLabel?: boolean;
  label?: string;
}

export default function ProgressBar({ value, color = 'var(--color-green-accent)', height = 6, showLabel, label }: ProgressBarProps) {
  return (
    <div className="flex items-center gap-3 w-full">
      {label && <span className="text-xs text-[var(--color-text-muted)] min-w-[60px]">{label}</span>}
      <div className="progress-bar-track flex-1" style={{ height }}>
        <div
          className="progress-bar-fill"
          style={{ width: `${Math.min(value, 100)}%`, background: color }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-semibold text-[var(--color-text-dark)] min-w-[32px] text-right">
          {value}%
        </span>
      )}
    </div>
  );
}
