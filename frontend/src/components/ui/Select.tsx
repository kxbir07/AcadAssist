import type { SelectHTMLAttributes } from 'react';

interface SelectOption {
  label: string;
  value: string | number;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options?: (string | SelectOption)[];
}

export default function Select({ label, options, children, className = '', ...props }: SelectProps) {
  return (
    <div className="w-full">
      {label && <label className="block text-xs font-semibold text-[var(--color-text-dark)] mb-1.5">{label}</label>}
      <select
        className={`w-full px-3 py-2 border border-[var(--color-card-border)] rounded-lg text-sm bg-[var(--color-card-bg)] text-[var(--color-text-dark)] outline-none focus:border-[var(--color-green-accent)] transition-colors cursor-pointer ${className}`}
        {...props}
      >
        {options
          ? options.map((opt) => {
              if (typeof opt === 'string') {
                return <option key={opt} value={opt}>{opt}</option>;
              }
              return <option key={opt.value} value={opt.value}>{opt.label}</option>;
            })
          : children}
      </select>
    </div>
  );
}
