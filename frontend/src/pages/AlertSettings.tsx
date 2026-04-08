import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, Mail, Globe, Send, CheckCircle, XCircle, ChevronDown, ChevronUp, Clock, Loader2 } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { api } from '../api/client';
import { useToast } from '../components/Toast';
import { useTenantSwitcher } from '../hooks/useTenant';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const ALERT_EVENTS = [
  { key: 'backup_failed', label: 'Backup Failed', desc: 'When a backup job fails after retries' },
  { key: 'backup_completed', label: 'Backup Completed', desc: 'When a backup job succeeds' },
  { key: 'anomaly_detected', label: 'Anomaly Detected', desc: 'Unusual backup patterns detected' },
  { key: 'protection_gap', label: 'Protection Gap', desc: 'Object not backed up per SLA' },
  { key: 'secret_expiring', label: 'Secret Expiring', desc: 'Credentials near expiration' },
  { key: 'worm_violation', label: 'WORM Violation', desc: 'Immutable retention violated' },
  { key: 'restore_completed', label: 'Restore Completed', desc: 'Restore job succeeded' },
  { key: 'restore_failed', label: 'Restore Failed', desc: 'Restore job failed' },
];

const FREQUENCY_OPTIONS = [
  { value: 'immediate', label: 'Immediate', desc: 'Real-time alerts as events occur' },
  { value: 'hourly', label: 'Hourly Digest', desc: 'Batched summary every hour' },
  { value: 'daily', label: 'Daily Digest', desc: 'Batched summary once per day' },
];

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TenantAlertConfig {
  tenant_id: number;
  email_recipients: string;
  webhook_url: string;
  enabled_events: string[];
  frequency: string;
  quiet_start_hour: number | null;
  quiet_end_hour: number | null;
  configured: boolean;
}

interface SaveResponse {
  tenant_id: number;
  status: string;
  enabled_events: string[];
  frequency: string;
}

interface TestResponse {
  sent: number;
  total_recipients: number;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AlertSettings() {
  const toast = useToast();
  const qc = useQueryClient();
  const { selectedTenantId } = useTenantSwitcher();

  /* --- System config state (existing) --- */
  const [testResult, setTestResult] = useState<{ sent: boolean; message: string } | null>(null);

  /* --- Per-tenant preferences state --- */
  const [emailRecipients, setEmailRecipients] = useState('');
  const [webhookUrl, setWebhookUrl] = useState('');
  const [enabledEvents, setEnabledEvents] = useState<string[]>(['backup_failed', 'anomaly_detected', 'protection_gap']);
  const [frequency, setFrequency] = useState<string>('immediate');
  const [quietExpanded, setQuietExpanded] = useState(false);
  const [quietStart, setQuietStart] = useState(22);
  const [quietEnd, setQuietEnd] = useState(7);

  /* --- Queries --- */
  const { data: config } = useQuery({
    queryKey: ['alert-config'],
    queryFn: () => api.get<any>('/alerts/config'),
  });

  const { data: tenantConfig, isLoading: tenantConfigLoading } = useQuery({
    queryKey: ['alert-tenant-config', selectedTenantId],
    queryFn: () => api.get<TenantAlertConfig>(`/alerts/tenant?tenant_id=${selectedTenantId}`),
    enabled: !!selectedTenantId,
  });

  /* --- Populate form from API (once) --- */
  const formInitialized = useRef(false);
  useEffect(() => {
    if (tenantConfig && !formInitialized.current) {
      formInitialized.current = true;
      setEmailRecipients(tenantConfig.email_recipients || '');
      setWebhookUrl(tenantConfig.webhook_url || '');
      setEnabledEvents(tenantConfig.enabled_events?.length ? tenantConfig.enabled_events : ['backup_failed', 'anomaly_detected', 'protection_gap']);
      setFrequency(tenantConfig.frequency || 'immediate');
      if (tenantConfig.quiet_start_hour !== null && tenantConfig.quiet_end_hour !== null) {
        setQuietStart(tenantConfig.quiet_start_hour);
        setQuietEnd(tenantConfig.quiet_end_hour);
        setQuietExpanded(true);
      }
    }
  }, [tenantConfig]);

  /* --- Mutations --- */
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

  const saveMutation = useMutation({
    mutationFn: () =>
      api.put<SaveResponse>(`/alerts/tenant?tenant_id=${selectedTenantId}`, {
        email_recipients: emailRecipients,
        webhook_url: webhookUrl,
        enabled_events: enabledEvents,
        frequency,
        quiet_start_hour: quietExpanded ? quietStart : null,
        quiet_end_hour: quietExpanded ? quietEnd : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alert-tenant-config', selectedTenantId] });
      toast.success('Preferences saved', 'Your alert preferences have been updated.');
    },
    onError: (err: any) => {
      toast.error('Save failed', err.message || 'Could not save alert preferences.');
    },
  });

  const tenantTestMutation = useMutation({
    mutationFn: () => api.post<TestResponse>(`/alerts/tenant/test?tenant_id=${selectedTenantId}`),
    onSuccess: (data) => {
      toast.success('Test alert sent', `Sent to ${data.sent} of ${data.total_recipients} recipients.`);
    },
    onError: (err: any) => {
      toast.error('Test failed', err.message || 'Could not send test alert.');
    },
  });

  /* --- Event toggle helper --- */
  const toggleEvent = (key: string) => {
    setEnabledEvents((prev) =>
      prev.includes(key) ? prev.filter((e) => e !== key) : [...prev, key],
    );
  };

  /* ------------------------------------------------------------------ */
  /*  Render                                                             */
  /* ------------------------------------------------------------------ */

  return (
    <div>
      {/* Page header (outside tabs) */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Alert Settings</h1>
        <p className="text-muted-foreground">Configure email and webhook notifications for backup events</p>
      </div>

      <Tabs.Root defaultValue="preferences" className="w-full">
        <Tabs.List className="flex gap-2 mb-6">
          <Tabs.Trigger
            value="preferences"
            className="px-4 py-2 text-sm font-medium rounded-lg data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=inactive]:text-muted-foreground transition-colors"
          >
            Alert Preferences
          </Tabs.Trigger>
          <Tabs.Trigger
            value="system"
            className="px-4 py-2 text-sm font-medium rounded-lg data-[state=active]:bg-blue-600 data-[state=active]:text-white data-[state=inactive]:text-muted-foreground transition-colors"
          >
            System Config
          </Tabs.Trigger>
        </Tabs.List>

        {/* ============================================================ */}
        {/*  Tab: Alert Preferences (per-tenant self-service)            */}
        {/* ============================================================ */}
        <Tabs.Content value="preferences">
          {tenantConfigLoading ? (
            <div className="flex items-center justify-center py-16 text-muted-foreground gap-2">
              <Loader2 className="w-5 h-5 animate-spin" />
              Loading tenant preferences...
            </div>
          ) : !selectedTenantId ? (
            <div className="bg-card rounded-xl border shadow-sm p-6 text-center text-muted-foreground">
              No tenant selected. Please select a tenant to configure alert preferences.
            </div>
          ) : (
            <div className="space-y-6">
              {/* Email Recipients */}
              <div className="bg-card rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Mail className="w-5 h-5 text-blue-600" />
                  <div>
                    <h3 className="font-semibold text-foreground">Email Recipients</h3>
                    <p className="text-muted-foreground text-xs">Comma-separated</p>
                  </div>
                </div>
                <input
                  type="text"
                  value={emailRecipients}
                  onChange={(e) => setEmailRecipients(e.target.value)}
                  placeholder="admin@example.com, ops@example.com"
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                />
              </div>

              {/* Webhook URL */}
              <div className="bg-card rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Globe className="w-5 h-5 text-purple-600" />
                  <div>
                    <h3 className="font-semibold text-foreground">Webhook URL</h3>
                    <p className="text-muted-foreground text-xs">Slack, Teams, or PagerDuty</p>
                  </div>
                </div>
                <input
                  type="url"
                  value={webhookUrl}
                  onChange={(e) => setWebhookUrl(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                />
              </div>

              {/* Alert Events */}
              <div className="bg-card rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Bell className="w-5 h-5 text-orange-500" />
                  <h3 className="font-semibold text-foreground">Alert Events</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {ALERT_EVENTS.map(({ key, label, desc }) => (
                    <label
                      key={key}
                      className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={enabledEvents.includes(key)}
                        onChange={() => toggleEvent(key)}
                        className="rounded"
                      />
                      <div>
                        <p className="font-medium text-foreground text-sm">{label}</p>
                        <p className="text-muted-foreground text-xs">{desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Delivery Frequency */}
              <div className="bg-card rounded-xl border shadow-sm p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Clock className="w-5 h-5 text-green-500" />
                  <h3 className="font-semibold text-foreground">Delivery Frequency</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {FREQUENCY_OPTIONS.map(({ value, label, desc }) => (
                    <label
                      key={value}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        frequency === value
                          ? 'border-blue-500 bg-blue-500/5'
                          : 'border-border'
                      }`}
                    >
                      <input
                        type="radio"
                        name="frequency"
                        value={value}
                        checked={frequency === value}
                        onChange={() => setFrequency(value)}
                        className="accent-blue-600"
                      />
                      <div>
                        <p className="font-medium text-foreground text-sm">{label}</p>
                        <p className="text-muted-foreground text-xs">{desc}</p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Quiet Hours (collapsible) */}
              <div className="bg-card rounded-xl border shadow-sm p-6">
                <button
                  type="button"
                  onClick={() => setQuietExpanded(!quietExpanded)}
                  className="flex items-center justify-between w-full text-left"
                >
                  <div className="flex items-center gap-2">
                    <Clock className="w-5 h-5 text-indigo-500" />
                    <div>
                      <h3 className="font-semibold text-foreground">Quiet Hours</h3>
                      <p className="text-muted-foreground text-xs">Suppress alerts during off-hours</p>
                    </div>
                  </div>
                  {quietExpanded ? (
                    <ChevronUp className="w-5 h-5 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-muted-foreground" />
                  )}
                </button>

                {quietExpanded && (
                  <div className="mt-4 flex items-center gap-4">
                    <div className="flex-1">
                      <label className="block text-sm text-muted-foreground mb-1">Start Hour (UTC)</label>
                      <input
                        type="number"
                        min={0}
                        max={23}
                        value={quietStart}
                        onChange={(e) => setQuietStart(Math.min(23, Math.max(0, parseInt(e.target.value) || 0)))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="block text-sm text-muted-foreground mb-1">End Hour (UTC)</label>
                      <input
                        type="number"
                        min={0}
                        max={23}
                        value={quietEnd}
                        onChange={(e) => setQuietEnd(Math.min(23, Math.max(0, parseInt(e.target.value) || 0)))}
                        className="w-full px-3 py-2 bg-background border border-border rounded-lg text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/40"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => saveMutation.mutate()}
                  disabled={saveMutation.isPending}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50 transition-colors"
                >
                  {saveMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {saveMutation.isPending ? 'Saving...' : 'Save Preferences'}
                </button>
                <button
                  onClick={() => tenantTestMutation.mutate()}
                  disabled={tenantTestMutation.isPending}
                  className="px-4 py-2 border border-border text-foreground rounded-lg text-sm font-medium hover:bg-muted flex items-center gap-2 disabled:opacity-50 transition-colors"
                >
                  {tenantTestMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                  {tenantTestMutation.isPending ? 'Sending...' : 'Send Test Alert'}
                </button>
              </div>
            </div>
          )}
        </Tabs.Content>

        {/* ============================================================ */}
        {/*  Tab: System Config (existing content, unchanged)            */}
        {/* ============================================================ */}
        <Tabs.Content value="system">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Email Configuration */}
            <div className="bg-card rounded-xl border shadow-sm p-6">
              <div className="flex items-center gap-2 mb-4">
                <Mail className="w-5 h-5 text-blue-600" />
                <h3 className="font-semibold text-foreground">Email Alerts</h3>
                {config?.smtp_configured
                  ? <span className="ml-auto px-2 py-0.5 bg-green-100 text-green-400 text-xs rounded-full font-medium">Configured</span>
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

              <div className="mt-4 p-3 bg-blue-500/10 rounded-lg">
                <p className="text-xs text-blue-400">
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
                  ? <span className="ml-auto px-2 py-0.5 bg-green-100 text-green-400 text-xs rounded-full font-medium">Configured</span>
                  : <span className="ml-auto px-2 py-0.5 bg-muted text-muted-foreground text-xs rounded-full font-medium">Not Configured</span>
                }
              </div>

              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Webhook URL</span>
                  <span className="font-mono text-muted-foreground truncate ml-4">{config?.webhook_url || 'Not set'}</span>
                </div>
              </div>

              <div className="mt-4 p-3 bg-purple-500/10 rounded-lg">
                <p className="text-xs text-purple-400">
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
                    severity === 'critical' ? 'bg-red-100 text-red-400' :
                    severity === 'error' ? 'bg-orange-100 text-orange-700' :
                    severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-blue-100 text-blue-400'
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
              <div className={`mt-3 p-3 rounded-lg flex items-center gap-2 text-sm ${testResult.sent ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
                {testResult.sent ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {testResult.message}
              </div>
            )}
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
