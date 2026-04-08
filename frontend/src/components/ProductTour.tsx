import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ArrowRight, ArrowLeft, Shield, LayoutDashboard, Mail, Activity, Brain, ShieldCheck, BarChart3, Search, Building2, Lock } from 'lucide-react';

const TOUR_STEPS = [
  // ── Getting Started ──
  {
    title: 'Welcome to KavachIQ',
    description: 'Your SaaS data protection platform. This tour walks you through setup, operations, and advanced features — it only takes 90 seconds.',
    icon: Shield,
    color: 'bg-blue-600',
    route: '/',
  },
  {
    title: 'Step 1: Connect Your Tenant',
    description: 'Start here — onboard your M365 tenant with a 3-step wizard. Enter credentials, discover workloads, and assign protection policies in minutes.',
    icon: Building2,
    color: 'bg-indigo-600',
    route: '/tenants',
  },
  {
    title: 'Step 2: Configure SLA Policies',
    description: 'Define backup frequency (hourly to daily), retention period (30-365 days), WORM immutability, and legal hold. Assign policies to workloads.',
    icon: Shield,
    color: 'bg-indigo-500/100',
    route: '/sla-policies',
  },
  // ── Daily Operations ──
  {
    title: 'Dashboard — Your Command Center',
    description: 'Once configured, the dashboard shows protection coverage, health score, and backup status across all workloads. Every metric drills down.',
    icon: LayoutDashboard,
    color: 'bg-blue-600',
    route: '/',
  },
  {
    title: 'Workload Protection',
    description: 'Exchange, OneDrive, SharePoint, Teams, and Entra ID — each workload shows backup status, item counts, and one-click backup/restore.',
    icon: Mail,
    color: 'bg-purple-600',
    route: '/exchange',
  },
  {
    title: 'Jobs & Monitoring',
    description: 'Track every backup and restore job in real-time. Failed jobs auto-retry with exponential backoff. Swimlane view groups jobs by workload.',
    icon: Activity,
    color: 'bg-green-600',
    route: '/jobs',
  },
  // ── Recovery & Intelligence ──
  {
    title: 'Self-Restore & Recovery',
    description: 'Search and restore any item across all workloads. Recovery dashboard shows confidence scoring, RPO/RTO tracking, and automated runbooks.',
    icon: ShieldCheck,
    color: 'bg-emerald-600',
    route: '/recovery',
  },
  {
    title: 'Smart Engine & Alerts',
    description: 'AI-powered anomaly detection learns your backup patterns. Health scoring, trend analysis, and email/webhook alerts — intelligence included free.',
    icon: Brain,
    color: 'bg-amber-600',
    route: '/smart-engine',
  },
  // ── Compliance & Governance ──
  {
    title: 'Reports, Usage & Compliance',
    description: 'Backup performance, storage analytics, license utilization, and compliance-ready reports. Every admin action logged in the immutable audit trail.',
    icon: BarChart3,
    color: 'bg-teal-600',
    route: '/reports',
  },
  {
    title: 'Security Posture',
    description: 'Your security grade, encryption status, and compliance readiness (SOC 2, GDPR, HIPAA, DORA). Download the security pack for procurement.',
    icon: Lock,
    color: 'bg-rose-600',
    route: '/security',
  },
  // ── Power Tips ──
  {
    title: 'Pro Tip: Search Everything with ⌘K',
    description: 'Press ⌘K anywhere to search across all backups. Intent-aware: try "find deleted emails", "check OneDrive status", or "show failed jobs".',
    icon: Search,
    color: 'bg-pink-600',
    route: '/',
  },
];

interface ProductTourProps {
  onComplete: () => void;
}

export default function ProductTour({ onComplete }: ProductTourProps) {
  const [step, setStep] = useState(0);
  const [isVisible, setIsVisible] = useState(true);
  const navigate = useNavigate();
  const current = TOUR_STEPS[step];
  const Icon = current.icon;
  const progress = ((step + 1) / TOUR_STEPS.length) * 100;

  useEffect(() => {
    navigate(current.route);
  }, [step]);

  const next = () => {
    if (step < TOUR_STEPS.length - 1) {
      setStep(step + 1);
    } else {
      complete();
    }
  };

  const prev = () => {
    if (step > 0) setStep(step - 1);
  };

  const complete = () => {
    setIsVisible(false);
    // Save to server (persists across devices, no localStorage)
    import('../api/client').then(({ api }) => {
      api.put('/auth/preferences/tour_completed', { value: 'true' }).catch(() => {});
    });
    navigate('/');
    onComplete();
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center pointer-events-none">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/20 pointer-events-auto" onClick={complete} />

      {/* Tour Card */}
      <div className="relative pointer-events-auto mb-6 mx-4 w-full max-w-lg animate-slide-up">
        <div className="bg-card rounded-2xl shadow-2xl border border-border overflow-hidden">
          {/* Progress bar */}
          <div className="h-1 bg-muted">
            <div
              className={`h-full ${current.color} transition-all duration-500`}
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="p-6">
            {/* Close button */}
            <button onClick={complete} className="absolute top-4 right-4 text-muted-foreground hover:text-muted-foreground transition-colors">
              <X className="w-5 h-5" />
            </button>

            {/* Icon + Step counter */}
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-2.5 ${current.color} rounded-xl`}>
                <Icon className="w-5 h-5 text-foreground" />
              </div>
              <div>
                <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-semibold">
                  Step {step + 1} of {TOUR_STEPS.length}
                </span>
              </div>
            </div>

            {/* Content */}
            <h3 className="text-lg font-bold text-foreground mb-2">{current.title}</h3>
            <p className="text-sm text-muted-foreground leading-relaxed">{current.description}</p>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-6">
              <div className="flex gap-1.5">
                {TOUR_STEPS.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setStep(i)}
                    className={`w-2 h-2 rounded-full transition-all ${i === step ? `${current.color} w-6` : 'bg-gray-200 hover:bg-gray-300'}`}
                  />
                ))}
              </div>

              <div className="flex gap-2">
                {step > 0 && (
                  <button onClick={prev} className="px-3 py-1.5 text-sm text-muted-foreground hover:text-muted-foreground flex items-center gap-1 transition-colors">
                    <ArrowLeft className="w-3.5 h-3.5" /> Back
                  </button>
                )}
                <button
                  onClick={next}
                  className={`px-4 py-1.5 ${current.color} text-foreground text-sm font-medium rounded-lg hover:opacity-90 flex items-center gap-1.5 transition-all`}
                >
                  {step === TOUR_STEPS.length - 1 ? 'Get Started' : 'Next'}
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Skip link */}
            {step < TOUR_STEPS.length - 1 && (
              <button onClick={complete} className="w-full text-center text-xs text-muted-foreground hover:text-muted-foreground mt-3 transition-colors">
                Skip tour
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
