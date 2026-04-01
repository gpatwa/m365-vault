import { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Shield, Save, RotateCcw, Check } from 'lucide-react';
import { api } from '../api/client';
import { useBranding } from '../contexts/BrandingContext';

interface BrandingForm {
  company_name: string;
  tagline: string;
  logo_url: string;
  primary_color: string;
  secondary_color: string;
}

export default function MSPBranding() {
  const branding = useBranding();
  const [form, setForm] = useState<BrandingForm>({
    company_name: '',
    tagline: '',
    logo_url: '',
    primary_color: '#3b82f6',
    secondary_color: '#1e293b',
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (branding.loaded) {
      setForm({
        company_name: branding.companyName,
        tagline: branding.tagline,
        logo_url: branding.logoUrl || '',
        primary_color: branding.primaryColor,
        secondary_color: branding.secondaryColor,
      });
    }
  }, [branding.loaded]);

  const saveMutation = useMutation({
    mutationFn: (data: BrandingForm) => api.put('/msp/branding', data),
    onSuccess: () => {
      setSaved(true);
      branding.refresh();
      setTimeout(() => setSaved(false), 3000);
    },
  });

  const handleSave = () => saveMutation.mutate(form);

  const handleReset = () => {
    setForm({
      company_name: 'Shieldio',
      tagline: 'SaaS Data Protection',
      logo_url: '',
      primary_color: '#3b82f6',
      secondary_color: '#1e293b',
    });
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">White-Label Branding</h1>
        <p className="text-sm text-muted-foreground">Customize the platform with your company branding</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="bg-card rounded-xl p-6 border border-border space-y-5">
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Company Name</label>
            <input
              type="text" value={form.company_name}
              onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-ring"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Tagline</label>
            <input
              type="text" value={form.tagline}
              onChange={e => setForm(f => ({ ...f, tagline: e.target.value }))}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-ring"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">Logo URL</label>
            <input
              type="url" value={form.logo_url} placeholder="https://example.com/logo.png"
              onChange={e => setForm(f => ({ ...f, logo_url: e.target.value }))}
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg text-foreground text-sm focus:outline-none focus:border-ring"
            />
            <p className="text-[10px] text-muted-foreground mt-1">Recommended: 28x28px SVG or PNG. Leave empty for default shield icon.</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Primary Color</label>
              <div className="flex items-center gap-2">
                <input
                  type="color" value={form.primary_color}
                  onChange={e => setForm(f => ({ ...f, primary_color: e.target.value }))}
                  className="w-10 h-10 rounded border border-border cursor-pointer bg-transparent"
                />
                <input
                  type="text" value={form.primary_color}
                  onChange={e => setForm(f => ({ ...f, primary_color: e.target.value }))}
                  className="flex-1 px-3 py-2 bg-muted border border-border rounded-lg text-foreground text-sm font-mono focus:outline-none focus:border-ring"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1">Secondary Color</label>
              <div className="flex items-center gap-2">
                <input
                  type="color" value={form.secondary_color}
                  onChange={e => setForm(f => ({ ...f, secondary_color: e.target.value }))}
                  className="w-10 h-10 rounded border border-border cursor-pointer bg-transparent"
                />
                <input
                  type="text" value={form.secondary_color}
                  onChange={e => setForm(f => ({ ...f, secondary_color: e.target.value }))}
                  className="flex-1 px-3 py-2 bg-muted border border-border rounded-lg text-foreground text-sm font-mono focus:outline-none focus:border-ring"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSave}
              disabled={saveMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
              {saved ? 'Saved' : saveMutation.isPending ? 'Saving...' : 'Save Branding'}
            </button>
            <button
              onClick={handleReset}
              className="flex items-center gap-2 px-4 py-2 bg-secondary text-muted-foreground rounded-lg text-sm font-medium hover:bg-accent transition-colors"
            >
              <RotateCcw className="w-4 h-4" /> Reset to Defaults
            </button>
          </div>
        </div>

        {/* Live Preview */}
        <div className="bg-card rounded-xl p-6 border border-border">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">Live Preview</h3>

          {/* Sidebar preview */}
          <div className="rounded-xl overflow-hidden border border-border" style={{ backgroundColor: form.secondary_color }}>
            <div className="p-4">
              <div className="flex items-center gap-2.5 mb-6">
                {form.logo_url ? (
                  <img src={form.logo_url} alt="Logo" className="w-7 h-7 rounded" />
                ) : (
                  <Shield className="w-7 h-7" style={{ color: form.primary_color }} />
                )}
                <div>
                  <h2 className="text-sm font-bold text-foreground leading-tight">{form.company_name || 'Shieldio'}</h2>
                  <p className="text-[10px] text-muted-foreground">{form.tagline || 'SaaS Data Protection'}</p>
                </div>
              </div>

              {/* Mock nav items */}
              <div className="space-y-1">
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-foreground" style={{ backgroundColor: form.primary_color }}>
                  <div className="w-4 h-4 rounded bg-card/20" />
                  Dashboard
                </div>
                {['Exchange', 'OneDrive', 'SharePoint'].map(item => (
                  <div key={item} className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground">
                    <div className="w-4 h-4 rounded bg-gray-600" />
                    {item}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Button preview */}
          <div className="mt-4 flex items-center gap-3">
            <button className="px-4 py-2 rounded-lg text-foreground text-sm font-medium" style={{ backgroundColor: form.primary_color }}>
              Primary Button
            </button>
            <button className="px-4 py-2 rounded-lg text-sm font-medium border" style={{ borderColor: form.primary_color, color: form.primary_color }}>
              Secondary Button
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
