import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { OnboardingProvider } from './contexts/OnboardingContext';
import { TenantProvider } from './contexts/TenantContext';
import { BrandingProvider } from './contexts/BrandingContext';
import { FeatureFlagProvider } from './contexts/FeatureFlagContext';
import { ToastProvider } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import Layout from './components/Layout';
import Landing from './pages/Landing';
import Tour from './pages/Tour';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Exchange from './pages/Exchange';
import OneDrive from './pages/OneDrive';
import SharePoint from './pages/SharePoint';
import EntraID from './pages/EntraID';
import Teams from './pages/Teams';
import SLAPolicies from './pages/SLAPolicies';
import Jobs from './pages/Jobs';
import Tenants from './pages/Settings';
import Organization from './pages/Organization';
import AuditLog from './pages/AuditLog';
import FailedItems from './pages/FailedItems';
import SSOCallback from './pages/SSOCallback';
import AlertSettings from './pages/AlertSettings';
import SmartEngine from './pages/SmartEngine';
import Search from './pages/Search';
import EDiscovery from './pages/eDiscovery';
import SelfRestore from './pages/SelfRestore';
import Recovery from './pages/Recovery';
import Reports from './pages/Reports';
import Usage from './pages/Usage';
import Legal from './pages/Legal';
import Contact from './pages/Contact';
import About from './pages/About';
import AgentShield from './pages/AgentShield';
import ResetPassword from './pages/ResetPassword';
import VerifyEmail from './pages/VerifyEmail';
import Billing from './pages/Billing';
import SecurityPosture from './pages/SecurityPosture';
import ObjectDetail from './pages/ObjectDetail';
import SecurityPage from './pages/Security';
import Docs from './pages/Docs';
import DocViewer from './pages/DocViewer';
import Performance from './pages/Performance';
import OrgContext from './pages/OrgContext';
import Onboard, { OnboardCallback, DemoOnboard } from './pages/Onboard';
import RestoreCallback from './pages/RestoreCallback';
import MSPDashboard from './pages/MSPDashboard';
import MSPBrandingPage from './pages/MSPBranding';
import BillingPortal from './pages/BillingPortal';
import BulkOnboard from './pages/BulkOnboard';
import MSPDemo from './pages/MSPDemo';
import FeatureFlagsPage from './pages/FeatureFlags';
import RoleGate from './components/RoleGate';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RootRoute() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }
  if (!isAuthenticated) return <Landing />;
  return <ProtectedRoute><TenantGate /></ProtectedRoute>;
}

/**
 * TenantGate — Enterprise pattern: before first connection, the entire app IS the onboarding wizard.
 *
 * PERFORMANCE: Reads from the SHARED session in AuthContext (queryKey: ['session']).
 * No duplicate API call — AuthContext already fetched it. Zero additional latency.
 */
function TenantGate() {
  const { session, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  // Server says user has no tenants → show onboard wizard (no Layout, no sidebar)
  if (session?.redirect) {
    if (session.onboarding_status === 'demo') {
      sessionStorage.setItem('kavachiq_onboard_mode', 'demo');
      return <Navigate to="/onboard/demo" replace />;
    }
    sessionStorage.setItem('kavachiq_onboard_mode', 'fast');
    return <Navigate to="/onboard" replace />;
  }

  // User has tenants → full app
  return <Layout />;
}

/** SmartHome — simplified. TenantGate handles routing.
 * By the time SmartHome renders, user is authenticated AND has tenants. */
function SmartHome() {
  return <Dashboard />;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/welcome" element={<Landing />} />
      <Route path="/tour" element={<Tour />} />
      <Route path="/login" element={<Login />} />
      <Route path="/sso/callback" element={<SSOCallback />} />
      <Route path="/legal" element={<Legal />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/about" element={<About />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/docs" element={<Docs />} />
      <Route path="/docs/view/:filename" element={<DocViewer />} />
      <Route path="/onboard" element={<ProtectedRoute><Onboard /></ProtectedRoute>} />
      <Route path="/onboard/callback" element={<ProtectedRoute><OnboardCallback /></ProtectedRoute>} />
      <Route path="/restore/callback" element={<ProtectedRoute><RestoreCallback /></ProtectedRoute>} />
      <Route path="/onboard/demo" element={<ProtectedRoute><DemoOnboard /></ProtectedRoute>} />

      {/* Root: Landing for anonymous, Dashboard for authenticated */}
      <Route path="/" element={<RootRoute />}>
        <Route index element={<SmartHome />} />
        <Route path="exchange" element={<Exchange />} />
        <Route path="onedrive" element={<OneDrive />} />
        <Route path="sharepoint" element={<SharePoint />} />
        <Route path="teams" element={<Teams />} />
        <Route path="entra-id" element={<EntraID />} />
        <Route path="sla-policies" element={<SLAPolicies />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="tenants" element={<RoleGate roles={['platform_admin', 'admin']}><Tenants /></RoleGate>} />
        <Route path="settings" element={<Organization />} />
        <Route path="msp" element={<RoleGate roles={['platform_admin', 'msp_admin', 'admin']}><MSPDashboard /></RoleGate>} />
        <Route path="msp/branding" element={<RoleGate roles={['platform_admin', 'msp_admin', 'admin']}><MSPBrandingPage /></RoleGate>} />
        <Route path="msp/billing" element={<RoleGate roles={['platform_admin', 'msp_admin', 'admin']}><BillingPortal /></RoleGate>} />
        <Route path="msp/onboard" element={<RoleGate roles={['platform_admin', 'msp_admin', 'admin']}><BulkOnboard /></RoleGate>} />
        <Route path="msp/demo" element={<RoleGate roles={['platform_admin', 'msp_admin', 'admin']}><MSPDemo /></RoleGate>} />
        <Route path="features" element={<RoleGate roles={['platform_admin', 'admin']}><FeatureFlagsPage /></RoleGate>} />
        <Route path="audit" element={<AuditLog />} />
        <Route path="failed-items" element={<FailedItems />} />
        <Route path="alerts" element={<AlertSettings />} />
        <Route path="search" element={<Search />} />
        <Route path="ediscovery" element={<EDiscovery />} />
        <Route path="smart-engine" element={<SmartEngine />} />
        <Route path="agent-shield" element={<AgentShield />} />
        <Route path="restore" element={<SelfRestore />} />
        <Route path="recovery" element={<Recovery />} />
        <Route path="reports" element={<Reports />} />
        <Route path="usage" element={<Usage />} />
        <Route path="billing" element={<Billing />} />
        <Route path="security-posture" element={<SecurityPosture />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="performance" element={<Performance />} />
        <Route path="org-context" element={<OrgContext />} />
        <Route path=":workload/:objectId" element={<ObjectDetail />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <HelmetProvider>
    <FeatureFlagProvider>
    <BrandingProvider>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <OnboardingProvider>
          <TenantProvider>
            <ToastProvider>
              <ErrorBoundary>
                <BrowserRouter>
                  <AppRoutes />
                </BrowserRouter>
              </ErrorBoundary>
            </ToastProvider>
          </TenantProvider>
        </OnboardingProvider>
      </AuthProvider>
    </QueryClientProvider>
    </BrandingProvider>
    </FeatureFlagProvider>
    </HelmetProvider>
  );
}
