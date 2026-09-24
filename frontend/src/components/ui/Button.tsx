import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
  className?: string;
}

export default function Button({
  variant = 'primary',
  size = 'md',
  children,
  className = '',
  ...props
}: ButtonProps) {
  const baseClasses = 'btn inline-flex items-center justify-center font-semibold transition-all rounded-lg disabled:opacity-50 cursor-pointer';
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-base',
  }[size];
  const variantClasses = {
    primary: 'btn-primary bg-[var(--color-green-accent)] text-white hover:brightness-95 shadow-sm',
    secondary: 'btn-secondary bg-[var(--color-border-light)] text-[var(--color-text-dark)] hover:opacity-90 border border-[var(--color-card-border)]',
    outline: 'border border-[var(--color-card-border)] bg-[var(--color-card-bg)] text-[var(--color-text-dark)] hover:border-[var(--color-green-accent)] hover:text-[var(--color-green-accent)]',
    ghost: 'bg-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-dark)] hover:bg-black/5 dark:hover:bg-white/5',
  }[variant];

  return (
    <button className={`${baseClasses} ${sizeClasses} ${variantClasses} ${className}`} {...props}>
      {children}
    </button>
  );
}
