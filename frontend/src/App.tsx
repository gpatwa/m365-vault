import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Layout from './components/Layout';
import Landing from './pages/Landing';
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
import ObjectDetail from './pages/ObjectDetail';
import SecurityPage from './pages/Security';
import Performance from './pages/Performance';

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RootRoute() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) {
    return <ProtectedRoute><Layout /></ProtectedRoute>;
  }
  return <Landing />;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/welcome" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/sso/callback" element={<SSOCallback />} />
      <Route path="/legal" element={<Legal />} />

      {/* Root: Landing for anonymous, Dashboard for authenticated */}
      <Route path="/" element={<RootRoute />}>
        <Route index element={<Dashboard />} />
        <Route path="exchange" element={<Exchange />} />
        <Route path="onedrive" element={<OneDrive />} />
        <Route path="sharepoint" element={<SharePoint />} />
        <Route path="teams" element={<Teams />} />
        <Route path="entra-id" element={<EntraID />} />
        <Route path="sla-policies" element={<SLAPolicies />} />
        <Route path="jobs" element={<Jobs />} />
        <Route path="tenants" element={<Tenants />} />
        <Route path="settings" element={<Tenants />} />
        <Route path="audit" element={<AuditLog />} />
        <Route path="failed-items" element={<FailedItems />} />
        <Route path="alerts" element={<AlertSettings />} />
        <Route path="search" element={<Search />} />
        <Route path="smart-engine" element={<SmartEngine />} />
        <Route path="restore" element={<SelfRestore />} />
        <Route path="recovery" element={<Recovery />} />
        <Route path="reports" element={<Reports />} />
        <Route path="usage" element={<Usage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="performance" element={<Performance />} />
        <Route path=":workload/:objectId" element={<ObjectDetail />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
