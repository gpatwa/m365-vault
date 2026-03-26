import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Shield, ArrowLeft, FileText } from 'lucide-react';
import { api } from '../api/client';

// Simple markdown to HTML renderer (no external library)
function renderMarkdown(md: string): string {
  let html = md
    // Headers
    .replace(/^#### (.+)$/gm, '<h4 class="text-base font-semibold text-gray-800 mt-5 mb-2">$1</h4>')
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-gray-800 mt-6 mb-2">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold text-gray-900 mt-8 mb-3 pb-2 border-b border-gray-200">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-gray-900 mt-6 mb-4">$1</h1>')
    // Bold + italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-sm font-mono">$1</code>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank" rel="noopener">$1</a>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr class="my-6 border-gray-200" />')
    // Unordered lists
    .replace(/^- (.+)$/gm, '<li class="ml-4 text-gray-700 text-sm leading-relaxed">$1</li>')
    // Bullet continuation
    .replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul class="list-disc space-y-1 my-2">$&</ul>')
    // Tables
    .replace(/^\|(.+)\|$/gm, (match) => {
      const cells = match.split('|').filter(c => c.trim());
      const isHeader = cells.some(c => /^[\s-]+$/.test(c));
      if (isHeader) return ''; // Skip separator row
      const tag = 'td';
      const cellHtml = cells.map(c => `<${tag} class="px-3 py-2 text-sm text-gray-700 border-b border-gray-100">${c.trim()}</${tag}>`).join('');
      return `<tr class="hover:bg-gray-50">${cellHtml}</tr>`;
    })
    // Wrap table rows
    .replace(/(<tr[^>]*>.*<\/tr>\n?)+/g, '<div class="overflow-x-auto my-4"><table class="w-full border border-gray-200 rounded-lg overflow-hidden text-sm"><tbody>$&</tbody></table></div>')
    // Code blocks
    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto my-4 text-sm"><code>$2</code></pre>')
    // Paragraphs (lines that aren't already HTML)
    .replace(/^(?!<[a-z/]|$)(.+)$/gm, '<p class="text-sm text-gray-700 leading-relaxed my-2">$1</p>');

  return html;
}

export default function DocViewer() {
  const { filename } = useParams<{ filename: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ['doc', filename],
    queryFn: () => api.get<{ file: string; content: string }>(`/docs/${filename}`),
    enabled: !!filename,
  });

  const title = filename?.replace('.md', '').replace(/_/g, ' ') || 'Document';

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-sm border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            <span className="font-bold text-gray-900">Shieldio</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/docs" className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" /> All Docs
            </Link>
            <Link to="/login" className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">Start Free</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 pt-20 pb-16">
        {isLoading && (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="mt-8 bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <p className="text-red-600 font-medium">Document not found</p>
            <Link to="/docs" className="text-sm text-blue-600 hover:underline mt-2 block">Back to documentation</Link>
          </div>
        )}

        {data && (
          <>
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-sm text-gray-400 mt-4 mb-6">
              <Link to="/docs" className="hover:text-gray-600">Docs</Link>
              <span>/</span>
              <span className="text-gray-700 flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> {title}</span>
            </div>

            {/* Rendered content */}
            <article
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(data.content) }}
            />
          </>
        )}
      </div>
    </div>
  );
}
