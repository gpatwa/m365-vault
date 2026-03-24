/**
 * SearchTrigger — unified search bar that opens the ⌘K command palette.
 *
 * Replaces individual search bars on workload pages with a consistent
 * design that triggers the global search. Can pre-filter by workload.
 *
 * Usage:
 *   <SearchTrigger />                          — global search
 *   <SearchTrigger workloadFilter="exchange" />  — pre-filtered to Exchange
 *   <SearchTrigger placeholder="Search emails..." workloadFilter="exchange" />
 */
import { Search, Command } from 'lucide-react';

interface SearchTriggerProps {
  placeholder?: string;
  workloadFilter?: string;
  className?: string;
}

export default function SearchTrigger({
  placeholder = 'Search across all backups...',
  workloadFilter,
  className = '',
}: SearchTriggerProps) {
  const handleClick = () => {
    // Dispatch custom event to open command palette with optional filter
    window.dispatchEvent(new CustomEvent('open-command-palette', {
      detail: { workloadFilter },
    }));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <button
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={`w-full max-w-xl flex items-center gap-3 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-left hover:border-gray-300 hover:shadow-sm transition-all group ${className}`}
    >
      <Search className="w-4 h-4 text-gray-400 group-hover:text-gray-500 transition-colors" />
      <span className="flex-1 text-sm text-gray-400 group-hover:text-gray-500 transition-colors">
        {placeholder}
      </span>
      <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gray-50 border border-gray-200 rounded text-[10px] text-gray-400 font-mono">
        <Command className="w-3 h-3" />K
      </kbd>
    </button>
  );
}
