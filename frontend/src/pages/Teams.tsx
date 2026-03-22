import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, RefreshCw, Loader2, CheckCircle, Users } from 'lucide-react';
import { api } from '../api/client';
import { useTenantId } from '../hooks/useTenant';
import { formatSize, timeAgo } from '../utils/format';

interface Team {
  id: number;
  display_name: string;
  ms_object_id: string;
  status: string;
  last_backup_at: string | null;
  total_items_backed_up: number;
  total_size_bytes: number;
}

export default function Teams() {
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const tenantId = useTenantId();
  const qc = useQueryClient();

  const { data: teamsData, isLoading } = useQuery({
    queryKey: ['teams-list', tenantId],
    queryFn: () => api.get<{ total: number; items: Team[] }>(`/teams/teams?tenant_id=${tenantId}`),
  });

  const backupMutation = useMutation({
    mutationFn: (teamId?: number) =>
      teamId
        ? api.post(`/teams/teams/${teamId}/backup`)
        : api.post(`/teams/backup-all?tenant_id=${tenantId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['teams-list'] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-600" />
      </div>
    );
  }

  const teams = teamsData?.items || [];

  if (teams.length === 0) {
    return (
      <div className="text-center py-16">
        <MessageSquare className="w-16 h-16 mx-auto mb-4 text-gray-300" />
        <h2 className="text-xl font-semibold text-gray-700 mb-2">No Teams Discovered</h2>
        <p className="text-gray-500">Run discovery on your tenant from the Tenants page to find Microsoft Teams.</p>
        <p className="text-gray-400 text-sm mt-2">Requires Chat.Read.All, ChannelMessage.Read.All, Team.ReadBasic.All permissions</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-pink-50 rounded-lg">
            <MessageSquare className="w-6 h-6 text-pink-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Microsoft Teams</h1>
            <p className="text-sm text-gray-500">{teams.length} team{teams.length !== 1 ? 's' : ''} discovered</p>
          </div>
        </div>
        <button
          onClick={() => backupMutation.mutate(undefined)}
          disabled={backupMutation.isPending}
          className="px-4 py-2 bg-pink-600 text-white rounded-lg text-sm font-medium hover:bg-pink-700 disabled:opacity-50 flex items-center gap-2"
        >
          {backupMutation.isPending
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Backing up...</>
            : <><RefreshCw className="w-4 h-4" /> Backup All Teams</>
          }
        </button>
      </div>

      {backupMutation.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700 flex items-center gap-2">
          <CheckCircle className="w-4 h-4" /> Backup completed successfully
        </div>
      )}

      {/* Teams Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {teams.map(team => (
          <div
            key={team.id}
            className={`bg-white rounded-xl border p-5 cursor-pointer transition-all hover:shadow-md ${
              selectedTeam?.id === team.id ? 'border-pink-400 ring-2 ring-pink-200' : 'border-gray-200'
            }`}
            onClick={() => setSelectedTeam(selectedTeam?.id === team.id ? null : team)}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-pink-600" />
                <h3 className="font-semibold text-gray-900">{team.display_name.replace(' (Team)', '')}</h3>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                team.status === 'protected' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
              }`}>{team.status}</span>
            </div>
            <div className="text-sm text-gray-500 space-y-1">
              <p>{team.total_items_backed_up} items • {formatSize(team.total_size_bytes)}</p>
              <p>{team.last_backup_at ? `Last backup ${timeAgo(team.last_backup_at)}` : 'No backups yet'}</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); backupMutation.mutate(team.id); }}
              disabled={backupMutation.isPending}
              className="mt-3 w-full px-3 py-1.5 border border-pink-200 text-pink-700 rounded-lg text-xs font-medium hover:bg-pink-50 flex items-center justify-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> Backup Now
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
