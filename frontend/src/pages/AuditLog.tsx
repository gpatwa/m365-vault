import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileText, Search } from 'lucide-react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import type { AuditLogEntry, PaginatedResponse } from '../types';

export default function AuditLog() {
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState('');

  const { data: logs, isLoading } = useQuery({
    queryKey: ['audit-logs', search, severity],
    queryFn: () => api.get<PaginatedResponse<AuditLogEntry>>(
      `/audit/logs?${search ? `search=${search}` : ''}${severity ? `&severity=${severity}` : ''}&page_size=100`
    ),
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
        <p className="text-gray-500">Track all system operations and changes</p>
      </div>

      <div className="flex gap-4 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
          <input type="text" placeholder="Search audit logs..." value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" />
        </div>
        <div className="flex gap-2">
          {['', 'info', 'warning', 'error', 'critical'].map(s => (
            <button key={s} onClick={() => setSeverity(s)}
              className={`px-3 py-2 rounded-lg text-xs font-medium ${severity === s ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Timestamp</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Severity</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Action</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Resource</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Details</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">User</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {logs?.items?.map(log => (
              <tr key={log.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-500 text-xs font-mono">{log.timestamp?.slice(0, 19)}</td>
                <td className="px-4 py-3"><StatusBadge status={log.severity} /></td>
                <td className="px-4 py-3 font-medium">{log.action}</td>
                <td className="px-4 py-3 text-gray-500">{log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}</td>
                <td className="px-4 py-3 text-gray-500 text-xs max-w-[300px] truncate">{log.details || '—'}</td>
                <td className="px-4 py-3 text-gray-500">User #{log.user_id || '—'}</td>
              </tr>
            ))}
            {isLoading && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Loading...</td></tr>}
            {!isLoading && !logs?.items?.length && (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">
                <FileText className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                No audit logs found
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
