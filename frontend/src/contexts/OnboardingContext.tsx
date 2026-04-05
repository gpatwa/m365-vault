import { createContext, useContext, useState, useMemo, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import { useAuth } from './AuthContext';

export type OnboardingStep =
  | 'create_account'
  | 'connect_platform'
  | 'discover_workloads'
  | 'assign_protection'
  | 'first_backup'
  | 'explore_recovery';

interface OnboardingState {
  steps: Record<OnboardingStep, boolean>;
  currentStep: OnboardingStep | null;
  completedCount: number;
  totalSteps: number;
  percentComplete: number;
  isComplete: boolean;
  hasTenants: boolean;
  hasProtectedObjects: boolean;
  hasBackups: boolean;
  completeStep: (step: OnboardingStep) => void;
  resetOnboarding: () => void;
}

const STEPS_ORDER: OnboardingStep[] = [
  'create_account',
  'connect_platform',
  'discover_workloads',
  'assign_protection',
  'first_backup',
  'explore_recovery',
];

const STORAGE_KEY = 'kavachiq_onboarding';

const OnboardingContext = createContext<OnboardingState | null>(null);

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();

  // Load saved state
  const [manualSteps, setManualSteps] = useState<Partial<Record<OnboardingStep, boolean>>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // Fetch real data to auto-detect completed steps
  const { data: summary } = useQuery({
    queryKey: ['onboard-summary'],
    queryFn: () => api.get<any>('/dashboard/summary'),
    enabled: isAuthenticated,
    refetchInterval: 30000,
  });

  // Auto-detect step completion from real data
  const steps = useMemo<Record<OnboardingStep, boolean>>(() => {
    const hasTenants = summary?.tenants > 0;
    const hasProtected = summary?.total_protected > 0;
    const hasJobs = summary?.jobs_24h?.backup_total > 0 || (summary?.total_protected > 0 && hasTenants);

    return {
      create_account: isAuthenticated,
      connect_platform: hasTenants || !!manualSteps.connect_platform,
      discover_workloads: (summary?.total_objects > 0) || !!manualSteps.discover_workloads,
      assign_protection: hasProtected || !!manualSteps.assign_protection,
      first_backup: hasJobs || !!manualSteps.first_backup,
      explore_recovery: !!manualSteps.explore_recovery,
    };
  }, [isAuthenticated, summary, manualSteps]);

  const completedCount = STEPS_ORDER.filter(s => steps[s]).length;
  const currentStep = STEPS_ORDER.find(s => !steps[s]) || null;

  const completeStep = (step: OnboardingStep) => {
    setManualSteps(prev => {
      const next = { ...prev, [step]: true };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      return next;
    });
  };

  const resetOnboarding = () => {
    setManualSteps({});
    localStorage.removeItem(STORAGE_KEY);
  };

  const state: OnboardingState = {
    steps,
    currentStep,
    completedCount,
    totalSteps: STEPS_ORDER.length,
    percentComplete: Math.round((completedCount / STEPS_ORDER.length) * 100),
    isComplete: completedCount === STEPS_ORDER.length,
    hasTenants: summary?.tenants > 0,
    hasProtectedObjects: summary?.total_protected > 0,
    hasBackups: summary?.jobs_24h?.backup_total > 0,
    completeStep,
    resetOnboarding,
  };

  return (
    <OnboardingContext.Provider value={state}>
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error('useOnboarding must be used within OnboardingProvider');
  return ctx;
}

export { STEPS_ORDER };
