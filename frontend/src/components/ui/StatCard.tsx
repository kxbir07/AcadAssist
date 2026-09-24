interface StatCardProps {
  icon: string;
  iconBg: string;
  value: string;
  label: string;
  delta?: string;
}

export default function StatCard({ icon, iconBg, value, label, delta }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ background: iconBg }}>{icon}</div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {delta && <div className="stat-delta">{delta}</div>}
      </div>
    </div>
  );
}
