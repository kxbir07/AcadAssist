interface SubjectBadgeProps {
  tag: string;
  className?: string;
}

const BADGE_MAP: Record<string, string> = {
  QC: 'badge-qc',
  ROB: 'badge-rob',
  ASTRO: 'badge-astro',
  BIO: 'badge-bio',
  DCP: 'badge-dcp',
  LING: 'badge-ling',
  DSA: 'badge-qc',
  DBMS: 'badge-dcp',
  CN: 'badge-astro',
  Mixed: 'badge-mixed',
  Break: 'badge-break',
};

export default function SubjectBadge({ tag, className = '' }: SubjectBadgeProps) {
  const badgeClass = BADGE_MAP[tag] || 'badge-mixed';
  return (
    <span className={`subject-badge ${badgeClass} ${className}`}>
      {tag}
    </span>
  );
}
