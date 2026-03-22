import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { api } from './api/client';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Exchange from './pages/Exchange';
import OneDrive from './pages/OneDrive';
import SharePoint from './pages/SharePoint';
import EntraID from './pages/EntraID';
import SLAPolicies from './pages/SLAPolicies';
import Jobs from './pages/Jobs';
import Tenants from './pages/Settings';
import AuditLog from './pages/AuditLog';
import FailedItems from './pages/FailedItems';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!api.getToken()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="exchange" element={<Exchange />} />
          <Route path="onedrive" element={<OneDrive />} />
          <Route path="sharepoint" element={<SharePoint />} />
          <Route path="entra-id" element={<EntraID />} />
          <Route path="sla-policies" element={<SLAPolicies />} />
          <Route path="jobs" element={<Jobs />} />
          <Route path="tenants" element={<Tenants />} />
          <Route path="settings" element={<Tenants />} />
          <Route path="audit" element={<AuditLog />} />
          <Route path="failed-items" element={<FailedItems />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
