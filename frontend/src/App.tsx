import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { OnboardingProvider } from './contexts/OnboardingContext';
import { TenantProvider } from './contexts/TenantContext';
import { BrandingProvider } from './contexts/BrandingContext';
import { FeatureFlagProvider } from './contexts/FeatureFlagContext';
import { ToastProvider } from './components/Toast';
import { ErrorBoundary } from './components/ErrorBoundary';
import { api } from './api/client';
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
import AuditLog from './pages/AuditLog';
import FailedItems from './pages/FailedItems';
import SSOCallback from './pages/SSOCallback';
import AlertSettings from './pages/AlertSettings';
import SmartEngine from './pages/SmartEngine';
import Search from './pages/Search';
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
import MSPDashboard from './pages/MSPDashboard';
import MSPBrandingPage from './pages/MSPBranding';
import BillingPortal from './pages/BillingPortal';
import BulkOnboard from './pages/BulkOnboard';
import MSPDemo from './pages/MSPDemo';
import FeatureFlagsPage from './pages/FeatureFlags';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RootRoute() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Landing />;
  return <ProtectedRoute><Layout /></ProtectedRoute>;
}

/** Smart redirect: checks user state and routes to the right experience */
function SmartHome() {
  const [checked, setChecked] = useState(false);
  const [redirect, setRedirect] = useState<string | null>(null);

  useEffect(() => {
    console.log('[Shieldio:SmartHome] mounted, token:', !!api.getToken());

    // Route users based on their role and purpose
    api.get<any>('/auth/me')
      .then(user => {
        if ((user?.username === 'demo' || user?.username === 'prospect') && !sessionStorage.getItem('demo_onboard_complete')) {
          console.log('[Shieldio:SmartHome] → demo/prospect user, redirect /onboard/demo');
          setRedirect('/onboard/demo');
          return;
        }
        if (user?.username === 'msp' || user?.role === 'msp_admin') {
          console.log('[Shieldio:SmartHome] → MSP user, redirect /msp');
          setRedirect('/msp');
          return;
        }
        // Normal user (admin/operator/viewer) — check tenants
        return api.get<any[]>('/tenants/');
      })
      .then(tenants => {
        if (!tenants) return; // demo user already redirected
        console.log('[Shieldio:SmartHome] tenants:', tenants?.length);
        if (!tenants || tenants.length === 0) {
          setRedirect('/onboard');
        } else {
          setChecked(true);
        }
      })
      .catch((err) => {
        console.error('[Shieldio:SmartHome] catch:', err?.message);
        setRedirect('/onboard');
      });
  }, []);

  if (redirect) return <Navigate to={redirect} replace />;
  if (!checked) return null;
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
        <Route path="tenants" element={<Tenants />} />
        <Route path="settings" element={<Tenants />} />
        <Route path="msp" element={<MSPDashboard />} />
        <Route path="msp/branding" element={<MSPBrandingPage />} />
        <Route path="msp/billing" element={<BillingPortal />} />
        <Route path="msp/onboard" element={<BulkOnboard />} />
        <Route path="msp/demo" element={<MSPDemo />} />
        <Route path="features" element={<FeatureFlagsPage />} />
        <Route path="audit" element={<AuditLog />} />
        <Route path="failed-items" element={<FailedItems />} />
        <Route path="alerts" element={<AlertSettings />} />
        <Route path="search" element={<Search />} />
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
  );
}
