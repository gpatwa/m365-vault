import { useQuery, useMutation } from '@tanstack/react-query';
import { Bell, Mail, Globe, Send, CheckCircle, XCircle } from 'lucide-react';
import { useState } from 'react';
import { api } from '../api/client';

export default function AlertSettings() {
  const [testResult, setTestResult] = useState<{ sent: boolean; message: string } | null>(null);

  const { data: config } = useQuery({
    queryKey: ['alert-config'],
    queryFn: () => api.get<any>('/alerts/config'),
  });

  const testMutation = useMutation({
    mutationFn: () => api.post('/alerts/test'),
    onSuccess: (data: any) => {
      setTestResult({
        sent: true,
        message: `Test alert sent! Email: ${data.channels?.email ? 'Yes' : 'No'}, Webhook: ${data.channels?.webhook ? 'Yes' : 'No'}`,
      });
    },
    onError: (err: any) => {
      setTestResult({ sent: false, message: err.message || 'Failed to send test alert' });
    },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Alert Settings</h1>
        <p className="text-muted-foreground">Configure email and webhook notifications for backup events</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Email Configuration */}
        <div className="bg-card rounded-xl border shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <Mail className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-foreground">Email Alerts</h3>
            {config?.smtp_configured
              ? <span className="ml-auto px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">Configured</span>
              : <span className="ml-auto px-2 py-0.5 bg-muted text-muted-foreground text-xs rounded-full font-medium">Not Configured</span>
            }
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">SMTP Host</span>
              <span className="font-mono text-muted-foreground">{config?.smtp_host || 'Not set'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">From Address</span>
              <span className="font-mono text-muted-foreground">{config?.smtp_from || 'Not set'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Recipients</span>
              <span className="font-mono text-muted-foreground">{config?.email_recipients || 'Not set'}</span>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-50 rounded-lg">
            <p className="text-xs text-blue-700">
              Configure via environment variables: <code className="bg-blue-100 px-1 rounded">SMTP_HOST</code>, <code className="bg-blue-100 px-1 rounded">SMTP_PORT</code>, <code className="bg-blue-100 px-1 rounded">SMTP_USER</code>, <code className="bg-blue-100 px-1 rounded">SMTP_PASSWORD</code>, <code className="bg-blue-100 px-1 rounded">SMTP_FROM</code>, <code className="bg-blue-100 px-1 rounded">ALERT_EMAIL_RECIPIENTS</code>
            </p>
          </div>
        </div>

        {/* Webhook Configuration */}
        <div className="bg-card rounded-xl border shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-purple-600" />
            <h3 className="font-semibold text-foreground">Webhook Alerts</h3>
            {config?.webhook_configured
              ? <span className="ml-auto px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full font-medium">Configured</span>
              : <span className="ml-auto px-2 py-0.5 bg-muted text-muted-foreground text-xs rounded-full font-medium">Not Configured</span>
            }
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Webhook URL</span>
              <span className="font-mono text-muted-foreground truncate ml-4">{config?.webhook_url || 'Not set'}</span>
            </div>
          </div>

          <div className="mt-4 p-3 bg-purple-50 rounded-lg">
            <p className="text-xs text-purple-700">
              Supports Slack, Teams, or custom webhooks. Set <code className="bg-purple-100 px-1 rounded">ALERT_WEBHOOK_URL</code> environment variable.
            </p>
          </div>
        </div>
      </div>

      {/* Alert Events */}
      <div className="bg-card rounded-xl border shadow-sm p-6 mt-6">
        <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
          <Bell className="w-5 h-5 text-orange-500" /> Alert Events
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
          {[
            { event: 'Backup Failed', desc: 'When a backup job fails after all retries', severity: 'error' },
            { event: 'Anomaly Detected', desc: 'When Smart Engine detects unusual backup patterns', severity: 'critical' },
            { event: 'SLA Violation', desc: 'When backup frequency misses SLA target', severity: 'warning' },
            { event: 'Auth Expired', desc: 'When tenant credentials expire', severity: 'error' },
            { event: 'Storage Warning', desc: 'When storage usage exceeds threshold', severity: 'warning' },
            { event: 'WORM Lock Applied', desc: 'When immutable retention lock is set', severity: 'info' },
          ].map(({ event, desc, severity }) => (
            <div key={event} className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${
                severity === 'critical' ? 'bg-red-100 text-red-700' :
                severity === 'error' ? 'bg-orange-100 text-orange-700' :
                severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                'bg-blue-100 text-blue-700'
              }`}>{severity}</span>
              <div>
                <p className="font-medium text-foreground">{event}</p>
                <p className="text-muted-foreground text-xs">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Test Alert */}
      <div className="bg-card rounded-xl border shadow-sm p-6 mt-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-foreground">Test Configuration</h3>
            <p className="text-muted-foreground text-sm">Send a test alert to verify your notification channels</p>
          </div>
          <button
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50"
          >
            <Send className="w-4 h-4" /> {testMutation.isPending ? 'Sending...' : 'Send Test Alert'}
          </button>
        </div>
        {testResult && (
          <div className={`mt-3 p-3 rounded-lg flex items-center gap-2 text-sm ${testResult.sent ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
            {testResult.sent ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
            {testResult.message}
          </div>
        )}
      </div>
    </div>
  );
}
