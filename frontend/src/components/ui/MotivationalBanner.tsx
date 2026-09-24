import type { ReactNode } from 'react';

interface MotivationalBannerProps {
  tag: string;
  title: string | ReactNode;
  subtitle: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function MotivationalBanner({ tag, title, subtitle, actionLabel = 'Keep Going', onAction }: MotivationalBannerProps) {
  return (
    <div className="motivational-banner">
      <div style={{ position: 'relative', zIndex: 1 }}>
        <div className="motivational-banner-tag">{tag}</div>
        <h3>{title}</h3>
        <p>{subtitle}</p>
      </div>
      <button
        onClick={onAction}
        className="relative z-1 flex items-center gap-2 px-6 py-2.5 bg-white/10 hover:bg-white/20 border border-white/20 rounded-[10px] text-white text-sm font-semibold transition-colors whitespace-nowrap"
      >
        {actionLabel} <span>→</span>
      </button>
    </div>
  );
}
