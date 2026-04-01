import { Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  path?: string;  // If no path, it's the current page (not a link)
  icon?: React.ReactNode;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  rightSlot?: React.ReactNode;
}

export default function Breadcrumb({ items, rightSlot }: BreadcrumbProps) {
  return (
    <nav className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-1 text-sm">
        <Link to="/" className="text-muted-foreground hover:text-muted-foreground transition-colors">
          <Home className="w-4 h-4" />
        </Link>
        {items.map((item, i) => (
          <span key={i} className="flex items-center gap-1">
            <ChevronRight className="w-3.5 h-3.5 text-foreground/70" />
            {item.path ? (
              <Link
                to={item.path}
                className="text-muted-foreground hover:text-blue-600 transition-colors flex items-center gap-1"
              >
                {item.icon}
                {item.label}
              </Link>
            ) : (
              <span className="text-foreground font-medium flex items-center gap-1">
                {item.icon}
                {item.label}
              </span>
            )}
          </span>
        ))}
      </div>
      {rightSlot && <div className="ml-4">{rightSlot}</div>}
    </nav>
  );
}
