import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { Shield, ArrowLeft, FileText } from 'lucide-react';
import { api } from '../api/client';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  securityLevel: 'loose',
  fontFamily: 'Inter, system-ui, sans-serif',
  fontSize: 14,
  flowchart: { padding: 20, nodeSpacing: 30, rankSpacing: 50 },
  er: { fontSize: 14 },
});

/**
 * Markdown to HTML renderer with Mermaid support.
 *
 * Key: Extract ALL code blocks first (mermaid + regular) into placeholders,
 * then run markdown transforms, then restore code blocks untouched.
 */
function renderMarkdown(md: string): string {
  const placeholders: { type: 'mermaid' | 'code'; content: string; lang?: string }[] = [];

  // 1. Extract mermaid blocks
  let text = md.replace(/```mermaid\n([\s\S]*?)```/g, (_, code) => {
    const idx = placeholders.length;
    placeholders.push({ type: 'mermaid', content: code.trim() });
    return `\n%%PLACEHOLDER_${idx}%%\n`;
  });

  // 2. Extract regular code blocks
  text = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = placeholders.length;
    placeholders.push({ type: 'code', content: code, lang: lang || '' });
    return `\n%%PLACEHOLDER_${idx}%%\n`;
  });

  // 3. Extract inline code
  text = text.replace(/`([^`]+)`/g, '<code class="bg-muted text-foreground px-1.5 py-0.5 rounded text-xs font-mono">$1</code>');

  // 4. Markdown transforms (safe — no code blocks to corrupt)
  text = text
    // Headers
    .replace(/^#### (.+)$/gm, '<h4 class="text-base font-semibold text-foreground mt-6 mb-2">$1</h4>')
    .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold text-foreground mt-8 mb-3">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="text-xl font-bold text-foreground mt-10 mb-4 pb-2 border-b border-border">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold text-foreground mt-8 mb-4">$1</h1>')
    // Bold + italic
    .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-foreground">$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank" rel="noopener">$1</a>')
    // Horizontal rules
    .replace(/^---$/gm, '<hr class="my-8 border-border" />')
    // Tables: convert | rows to HTML
    .replace(/^(\|.+\|)$/gm, (line) => {
      if (/^\|[\s:-]+\|$/.test(line)) return '';
      const cells = line.split('|').filter(c => c.trim() !== '');
      return '<tr class="hover:bg-muted/50">' + cells.map(c =>
        `<td class="px-4 py-2.5 text-sm text-muted-foreground border-b border-border">${c.trim()}</td>`
      ).join('') + '</tr>';
    })
    // Wrap table rows
    .replace(/(<tr[^>]*>.*<\/tr>\n?)+/g, (block) => {
      const rows = block.trim().split('\n');
      const header = rows[0]?.replace(/<td/g, '<th').replace(/<\/td>/g, '</th>').replace(/text-foreground\/80/g, 'text-muted-foreground font-medium') || '';
      const body = rows.slice(1).join('\n');
      return `<div class="overflow-x-auto my-6 rounded-xl border border-border"><table class="w-full text-sm"><thead class="bg-muted/50">${header}</thead><tbody>${body}</tbody></table></div>`;
    })
    // Lists
    .replace(/^- (.+)$/gm, '<li class="text-sm text-muted-foreground leading-relaxed">$1</li>')
    .replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul class="list-disc ml-5 space-y-1.5 my-3">$&</ul>')
    // Paragraphs (lines not already HTML)
    .replace(/^(?!<[a-z/]|%%|$|\s*$)(.+)$/gm, '<p class="text-sm text-muted-foreground leading-relaxed my-2">$1</p>');

  // 5. Restore placeholders
  text = text.replace(/%%PLACEHOLDER_(\d+)%%/g, (_, idxStr) => {
    const idx = parseInt(idxStr);
    const block = placeholders[idx];
    if (!block) return '';

    if (block.type === 'mermaid') {
      const id = `mermaid-${Date.now()}-${idx}`;
      return `<div class="my-8 p-6 bg-muted/50 rounded-xl border border-border overflow-x-auto"><pre class="mermaid" id="${id}">${block.content}</pre></div>`;
    }

    // Regular code block
    const hasBoxChars = /[┌┐└┘├┤┬┴─│═╔╗╚╝╠╣╦╩]/.test(block.content);
    const cls = hasBoxChars ? 'text-xs leading-relaxed whitespace-pre' : 'text-sm';
    return `<div class="my-4 bg-muted rounded-xl p-4 overflow-x-auto"><pre class="${cls} text-gray-100 font-mono">${block.content}</pre></div>`;
  });

  return text;
}

export default function DocViewer() {
  const { filename } = useParams<{ filename: string }>();
  const contentRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['doc', filename],
    queryFn: () => api.get<{ file: string; content: string }>(`/docs/${filename}`),
    enabled: !!filename,
  });

  // Render mermaid after content loads
  useEffect(() => {
    if (data && contentRef.current) {
      const elements = contentRef.current.querySelectorAll('.mermaid');
      if (elements.length > 0) {
        // Small delay to ensure DOM is ready
        setTimeout(() => {
          try {
            mermaid.run({ nodes: elements as any });
          } catch (e) {
            console.error('Mermaid render error:', e);
          }
        }, 100);
      }
    }
  }, [data]);

  const title = filename?.replace('.md', '').replace(/_/g, ' ') || 'Document';

  return (
    <div className="min-h-screen bg-card">
      <nav className="fixed top-0 w-full z-50 bg-card/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link to="/welcome" className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-blue-600" />
            <span className="font-bold text-foreground">KavachIQ</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/docs" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
              <ArrowLeft className="w-3.5 h-3.5" /> All Docs
            </Link>
            <Link to="/login" className="px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">Start Free</Link>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-6 pt-20 pb-16">
        {isLoading && (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-blue-500/20 border-t-blue-600 rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="mt-8 bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-center">
            <p className="text-red-600 font-medium">Document not found</p>
            <Link to="/docs" className="text-sm text-blue-600 hover:underline mt-2 block">Back to documentation</Link>
          </div>
        )}

        {data && (
          <>
            <div className="flex items-center gap-2 text-sm text-muted-foreground mt-4 mb-6">
              <Link to="/docs" className="hover:text-muted-foreground">Docs</Link>
              <span>/</span>
              <span className="text-muted-foreground flex items-center gap-1"><FileText className="w-3.5 h-3.5" /> {title}</span>
            </div>

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
