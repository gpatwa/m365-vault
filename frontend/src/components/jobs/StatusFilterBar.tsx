interface StatusFilterBarProps {
  value: string;
  onChange: (status: string) => void;
  counts?: Record<string, number>;
}

const STATUSES = ['', 'queued', 'in_progress', 'completed', 'failed', 'partial'];

export default function StatusFilterBar({ value, onChange, counts }: StatusFilterBarProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      {STATUSES.map(s => {
        const count = counts?.[s || 'all'];
        return (
          <button
            key={s}
            onClick={() => onChange(s)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors flex items-center gap-1.5 ${
              value === s
                ? 'bg-blue-100 text-blue-400 ring-1 ring-blue-300'
                : 'bg-muted text-muted-foreground hover:bg-accent'
            }`}
          >
            {s ? s.replace('_', ' ') : 'All'}
            {count !== undefined && count > 0 && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                value === s ? 'bg-blue-200 text-blue-400' : 'bg-gray-200 text-muted-foreground'
              }`}>
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
