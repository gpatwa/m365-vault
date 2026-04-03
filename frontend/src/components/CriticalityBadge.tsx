/** Criticality tier badge — shows business importance level */
const TIER_STYLES: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  medium: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  low: 'bg-muted text-muted-foreground border-border',
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
