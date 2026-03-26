import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { Shield, ArrowLeft, FileText } from 'lucide-react';
import { api } from '../api/client';
import mermaid from 'mermaid';

// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
  fontFamily: 'Inter, system-ui, sans-serif',
  flowchart: { curve: 'basis', padding: 15 },
});

// Render markdown to HTML with Mermaid support
function renderMarkdown(md: string): string {
  let html = md
    // Mermaid code blocks — render as mermaid divs
    .replace(/```mermaid\n([\s\S]*?)```/g, (_match, code) => {
      const id = `mermaid-${Math.random().toString(36).slice(2, 8)}`;
      return `<div class="mermaid-container my-6"><pre class="mermaid" id="${id}">${code.trim()}</pre></div>`;
    })
    // Regular code blocks — preserve ASCII diagrams with proper monospace
    .replace(/```(\w+)?\n([\s\S]*?)```/g, (_match, lang, code) => {
      const hasBoxChars = /[┌┐└┘├┤┬┴─│═╔╗╚╝╠╣╦╩]/.test(code);
      if (hasBoxChars) {
        return `<div class="my-4 bg-gray-900 rounded-xl p-4 overflow-x-auto"><pre class="text-xs text-gray-100 font-mono leading-relaxed whitespace-pre">${code}</pre></div>`;
      }
      const langClass = lang ? `language-${lang}` : '';
      return `<div class="my-4 bg-gray-900 rounded-xl p-4 overflow-x-auto"><pre class="text-sm text-gray-100 font-mono ${langClass}">${code}</pre></div>`;
    })
    // Headers
    .replace(/^#### (.+)$/gm, '<h4 class="text-base font-semibold text-gray-800 mt-6 mb-2">$1</h4>')
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-gray-800 mt-8 mb-3">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold text-gray-900 mt-10 mb-4 pb-2 border-b border-gray-200">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-gray-900 mt-8 mb-4">$1</h1>')
    // Bold + italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-900">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-gray-800 px-1.5 py-0.5 rounded text-xs font-mono">$1</code>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank" rel="noopener">$1</a>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr class="my-8 border-gray-200" />')
    // Tables
    .replace(/^(\|.+\|)$/gm, (line) => {
      if (/^\|[\s:-]+\|$/.test(line)) return ''; // Skip separator
      const cells = line.split('|').filter(c => c.trim() !== '');
      // Detect if this is a header row (first table row)
      const cellHtml = cells.map(c =>
        `<td class="px-4 py-2.5 text-sm text-gray-700 border-b border-gray-100">${c.trim()}</td>`
      ).join('');
      return `<tr class="hover:bg-gray-50">${cellHtml}</tr>`;
    })
    // Wrap consecutive table rows
    .replace(/(<tr[^>]*>.*<\/tr>\n?)+/g, (block) => {
      // First row becomes header
      const rows = block.trim().split('\n');
      if (rows.length > 0) {
        const headerRow = rows[0].replace(/<td/g, '<th').replace(/<\/td>/g, '</th>').replace(/text-gray-700/g, 'text-gray-600 font-medium');
        const bodyRows = rows.slice(1).join('\n');
        return `<div class="overflow-x-auto my-6 rounded-xl border border-gray-200"><table class="w-full text-sm"><thead class="bg-gray-50">${headerRow}</thead><tbody>${bodyRows}</tbody></table></div>`;
      }
      return block;
    })
    // Unordered lists
    .replace(/^- (.+)$/gm, '<li class="text-sm text-gray-700 leading-relaxed">$1</li>')
    .replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul class="list-disc ml-5 space-y-1.5 my-3">$&</ul>')
    // Numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li class="text-sm text-gray-700 leading-relaxed">$1</li>')
    // Paragraphs
    .replace(/^(?!<[a-z/]|$|\s*$)(.+)$/gm, '<p class="text-sm text-gray-700 leading-relaxed my-2">$1</p>');

  return html;
}

export default function DocViewer() {
  const { filename } = useParams<{ filename: string }>();
  const contentRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['doc', filename],
    queryFn: () => api.get<{ file: string; content: string }>(`/docs/${filename}`),
    enabled: !!filename,
  });

  // Render mermaid diagrams after content loads
  useEffect(() => {
    if (data && contentRef.current) {
      const elements = contentRef.current.querySelectorAll('.mermaid');
      if (elements.length > 0) {
        mermaid.run({ nodes: elements as any });
      }
    }
  }, [data]);

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
              ref={contentRef}
              className="max-w-none"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(data.content) }}
            />
          </>
        )}
      </div>
    </div>
  );
}
