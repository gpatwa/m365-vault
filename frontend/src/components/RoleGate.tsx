/**
 * RoleGate — route-level role enforcement (defense-in-depth).
 *
 * Sidebar hiding in Layout.tsx is NOT sufficient — users can type URLs directly.
 * This component wraps routes to enforce role checks on the frontend.
 * Backend still enforces via require_role() — this prevents the page shell
 * from rendering and showing confusing 403 error states.
 *
 * Usage:
 *   <Route path="msp" element={<RoleGate roles={['platform_admin','msp_admin']}><MSPDashboard /></RoleGate>} />
 */
import { type ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface RoleGateProps {
  /** Roles allowed to access this route */
  roles: string[];
  /** Content to render when authorized */
  children: ReactNode;
  /** Where to redirect unauthorized users (default: dashboard) */
  redirectTo?: string;
}

export default function RoleGate({ roles, children, redirectTo = '/' }: RoleGateProps) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const userRole = user.role || 'viewer';

  // Platform admin bypass: username='admin' has access to everything
  // Matches the isPlatformAdmin check in Layout.tsx
  const isPlatformAdmin = user.username === 'admin';
  if (isPlatformAdmin) {
    return <>{children}</>;
  }

  // Check if user's role is in the allowed list
  if (roles.includes(userRole)) {
    return <>{children}</>;
  }

  // Also check if 'platform_admin' is in roles — map to isPlatformAdmin
  if (roles.includes('platform_admin') && isPlatformAdmin) {
    return <>{children}</>;
  }

  // Unauthorized — redirect silently (no confusing 403 page)
  return <Navigate to={redirectTo} replace />;
}
