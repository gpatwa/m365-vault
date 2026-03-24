import { Link } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

export interface BreadcrumbItem {
  label: string;
  path?: string;  // If no path, it's the current page (not a link)
  icon?: React.ReactNode;
}

export default function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav className="flex items-center gap-1 text-sm mb-4">
      <Link to="/" className="text-gray-400 hover:text-gray-600 transition-colors">
        <Home className="w-4 h-4" />
      </Link>
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          <ChevronRight className="w-3.5 h-3.5 text-gray-300" />
          {item.path ? (
            <Link
              to={item.path}
              className="text-gray-500 hover:text-blue-600 transition-colors flex items-center gap-1"
            >
              {item.icon}
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-900 font-medium flex items-center gap-1">
              {item.icon}
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
