import { createContext, useContext, useCallback, useMemo, type ReactNode } from 'react';
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

const OnboardingContext = createContext<OnboardingState | null>(null);

export function OnboardingProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, session } = useAuth();

  // Server-side onboarding state machine.
  // Steps are immutable: once completed on the server, they never un-complete.
  // The session response includes: { onboarding: { steps: { step_name: "iso_date", ... }, completed: N, total: 6 } }
  const serverSteps = session?.onboarding?.steps || {};

  const hasTenants = !!session?.has_tenants || session?.tenant_count > 0 || session?.onboarding_status === 'complete';
  const hasProtectedObjects = !!session?.has_protected_objects || session?.onboarding_status === 'complete';
  const hasBackups = !!session?.has_backups || session?.onboarding_status === 'complete';

  // Derive step completion from server state.
  // Fallback to session-derived values for backward compatibility during migration.
  const steps = useMemo<Record<OnboardingStep, boolean>>(() => {
    return {
      create_account: !!serverSteps.create_account || isAuthenticated,
      connect_platform: !!serverSteps.connect_platform || hasTenants,
      discover_workloads: !!serverSteps.discover_workloads || hasTenants,
      assign_protection: !!serverSteps.assign_protection || hasProtectedObjects,
      first_backup: !!serverSteps.first_backup || hasBackups,
      explore_recovery: !!serverSteps.explore_recovery,
    };
  }, [isAuthenticated, hasTenants, hasProtectedObjects, hasBackups, serverSteps]);

  const completedCount = STEPS_ORDER.filter(s => steps[s]).length;
  const currentStep = STEPS_ORDER.find(s => !steps[s]) || null;

  const completeStep = useCallback(async (step: OnboardingStep) => {
    try {
      await fetch(`/api/onboard/steps/${step}/complete`, { method: 'POST', credentials: 'include' });
      // Refetch session to update onboarding state immediately
      window.dispatchEvent(new Event('kavachiq:session-refresh'));
    } catch {
      // Silently fail — step will be marked on next action
    }
  }, []);

  const resetOnboarding = useCallback(() => {
    // No-op: server-side steps are immutable
  }, []);

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
