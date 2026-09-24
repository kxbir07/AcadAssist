import type { ReactNode } from 'react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  className?: string;
}

export default function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  const variantClasses = {
    default: 'bg-[var(--color-green-light)] text-[var(--color-green-accent)] dark:bg-[var(--color-green-accent)]/20 dark:text-emerald-300',
    success: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30',
    warning: 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border border-amber-500/30',
    danger: 'bg-red-500/15 text-red-700 dark:text-red-300 border border-red-500/30',
    info: 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/30',
    neutral: 'bg-gray-500/15 text-[var(--color-text-body)] border border-[var(--color-card-border)]',
  }[variant];

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${variantClasses} ${className}`}>
      {children}
    </span>
  );
}
