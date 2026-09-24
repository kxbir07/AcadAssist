import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export default function Input({ label, error, className = '', ...props }: InputProps) {
  return (
    <div className="w-full">
      {label && <label className="block text-xs font-semibold text-[var(--color-text-dark)] mb-1.5">{label}</label>}
      <input
        className={`w-full px-3 py-2 border border-[var(--color-card-border)] rounded-lg text-sm bg-[var(--color-card-bg)] text-[var(--color-text-dark)] outline-none focus:border-[var(--color-green-accent)] transition-colors ${
          error ? 'border-red-400 focus:border-red-500' : ''
        } ${className}`}
        {...props}
      />
      {error && <span className="text-[0.65rem] text-red-500 mt-1 block">{error}</span>}
    </div>
  );
}
