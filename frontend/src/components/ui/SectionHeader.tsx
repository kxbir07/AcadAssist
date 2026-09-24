import type { ReactNode } from 'react';

interface SectionHeaderProps {
  icon?: string;
  title: string;
  action?: string;
  onAction?: () => void;
  children?: ReactNode;
}

export default function SectionHeader({ icon, title, action, onAction, children }: SectionHeaderProps) {
  return (
    <div className="section-header">
      <div className="section-title">
        {icon && <span>{icon}</span>}
        {title}
      </div>
      {children}
      {action && (
        <button className="section-link" onClick={onAction}>
          {action} →
        </button>
      )}
    </div>
  );
}
