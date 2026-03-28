/** Criticality tier badge — shows business importance level */
const TIER_STYLES: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-blue-100 text-blue-800 border-blue-200',
  low: 'bg-gray-100 text-gray-600 border-gray-200',
};

export default function CriticalityBadge({ tier, score }: { tier: string; score?: number }) {
  const style = TIER_STYLES[tier] || TIER_STYLES.medium;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${style}`}
      title={score !== undefined ? `Criticality: ${score}/100` : undefined}>
      {tier}
      {score !== undefined && <span className="text-[10px] opacity-60">{score}</span>}
    </span>
  );
}
