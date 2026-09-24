interface TabsProps {
  tabs: string[];
  activeTab: string;
  onTabChange: (tab: string) => void;
  className?: string;
}

export default function Tabs({ tabs, activeTab, onTabChange, className = '' }: TabsProps) {
  return (
    <div className={`tab-bar flex gap-1 border-b border-[var(--color-border-light)] ${className}`}>
      {tabs.map((tab) => {
        const isActive = tab === activeTab;
        return (
          <button
            key={tab}
            type="button"
            onClick={() => onTabChange(tab)}
            className={`tab-item px-4 py-2 text-xs font-semibold border-b-2 transition-colors cursor-pointer ${
              isActive
                ? 'border-[var(--color-green-accent)] text-[var(--color-green-accent)] font-bold'
                : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-dark)]'
            }`}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
}
