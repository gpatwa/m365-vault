import { createContext, useContext, useState, useMemo, type ReactNode } from 'react';
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
  const { isAuthenticated, session } = useAuth();

  // Load saved state
  const [manualSteps, setManualSteps] = useState<Partial<Record<OnboardingStep, boolean>>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  // PERFORMANCE: Derive onboarding state from the SHARED session (AuthContext).
  // Zero extra API calls — reads from the session query that AuthContext already fetches.
  //
  // Backend GET /auth/session returns:
  //   has_tenants: boolean, tenant_count: number, onboarding_status: string, redirect: string|null
  // It does NOT return: tenant_ids, has_protected_objects, has_backups
  // So we use has_tenants (boolean) and onboarding_status ("complete"/"pending"/"demo")
  const hasTenants = !!session?.has_tenants || session?.tenant_count > 0 || session?.onboarding_status === 'complete';
  const hasProtectedObjects = !!session?.has_protected_objects || session?.onboarding_status === 'complete' || !!manualSteps.assign_protection;
  const hasBackups = !!session?.has_backups || session?.onboarding_status === 'complete' || !!manualSteps.first_backup;

  // Auto-detect step completion from session + manual overrides
  const steps = useMemo<Record<OnboardingStep, boolean>>(() => {
    return {
      create_account: isAuthenticated,
      connect_platform: hasTenants || !!manualSteps.connect_platform,
      discover_workloads: hasTenants || !!manualSteps.discover_workloads,
      assign_protection: hasProtectedObjects || !!manualSteps.assign_protection,
      first_backup: hasBackups || !!manualSteps.first_backup,
      explore_recovery: !!manualSteps.explore_recovery,
    };
  }, [isAuthenticated, hasTenants, hasProtectedObjects, hasBackups, manualSteps]);

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
    hasTenants,
    hasProtectedObjects,
    hasBackups,
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
