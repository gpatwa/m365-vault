import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ArrowRight, ArrowLeft, Shield, LayoutDashboard, Mail, Activity, Brain, ShieldCheck, BarChart3, Search } from 'lucide-react';

const TOUR_STEPS = [
  {
    title: 'Welcome to Shieldio',
    description: 'Your SaaS data protection platform. Let us show you around — it only takes 60 seconds.',
    icon: Shield,
    color: 'bg-blue-600',
    route: '/',
  },
  {
    title: 'Dashboard — Your Command Center',
    description: 'See protection coverage, health score, and backup status across all workloads at a glance. Every metric is clickable for drill-down.',
    icon: LayoutDashboard,
    color: 'bg-indigo-600',
    route: '/',
  },
  {
    title: 'Workload Protection',
    description: 'Exchange, OneDrive, SharePoint, Teams, and Entra ID — each workload has dedicated backup, restore, and monitoring. Click any workload to explore.',
    icon: Mail,
    color: 'bg-purple-600',
    route: '/exchange',
  },
  {
    title: 'Jobs & Monitoring',
    description: 'Track every backup and restore job in real-time. Failed jobs auto-retry with exponential backoff. Swimlane view groups by workload.',
    icon: Activity,
    color: 'bg-green-600',
    route: '/jobs',
  },
  {
    title: 'Smart Engine',
    description: 'AI-powered anomaly detection learns your backup patterns and alerts on deviations. Health scoring, baselines, and trend analysis — all at zero cost.',
    icon: Brain,
    color: 'bg-amber-600',
    route: '/smart-engine',
  },
  {
    title: 'Recovery Dashboard',
    description: 'Recovery confidence scoring, RPO/RTO tracking, and automated recovery runbooks. Know your recovery readiness before you need it.',
    icon: ShieldCheck,
    color: 'bg-red-600',
    route: '/recovery',
  },
  {
    title: 'Reports & Security',
    description: 'Compliance-ready reports, storage analytics, and a security posture page with SOC 2, GDPR, and HIPAA control mapping.',
    icon: BarChart3,
    color: 'bg-teal-600',
    route: '/reports',
  },
  {
    title: 'Search Everything',
    description: 'Press ⌘K anywhere to search across all backups. Intent-aware search understands "find deleted emails" or "check OneDrive status".',
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
    localStorage.setItem('shieldio_tour_completed', 'true');
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
        <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
          {/* Progress bar */}
          <div className="h-1 bg-gray-100">
            <div
              className={`h-full ${current.color} transition-all duration-500`}
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="p-6">
            {/* Close button */}
            <button onClick={complete} className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors">
              <X className="w-5 h-5" />
            </button>

            {/* Icon + Step counter */}
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-2.5 ${current.color} rounded-xl`}>
                <Icon className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="text-[10px] text-gray-400 uppercase tracking-wider font-semibold">
                  Step {step + 1} of {TOUR_STEPS.length}
                </span>
              </div>
            </div>

            {/* Content */}
            <h3 className="text-lg font-bold text-gray-900 mb-2">{current.title}</h3>
            <p className="text-sm text-gray-600 leading-relaxed">{current.description}</p>

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
                  <button onClick={prev} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1 transition-colors">
                    <ArrowLeft className="w-3.5 h-3.5" /> Back
                  </button>
                )}
                <button
                  onClick={next}
                  className={`px-4 py-1.5 ${current.color} text-white text-sm font-medium rounded-lg hover:opacity-90 flex items-center gap-1.5 transition-all`}
                >
                  {step === TOUR_STEPS.length - 1 ? 'Get Started' : 'Next'}
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Skip link */}
            {step < TOUR_STEPS.length - 1 && (
              <button onClick={complete} className="w-full text-center text-xs text-gray-400 hover:text-gray-600 mt-3 transition-colors">
                Skip tour
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
