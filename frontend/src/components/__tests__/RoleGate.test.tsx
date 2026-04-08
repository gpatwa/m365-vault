/**
 * RoleGate component tests — verifies route-level role enforcement.
 *
 * Tests that:
 * - Authorized roles see the protected content
 * - Unauthorized roles get redirected
 * - Platform admin (username='admin') bypasses all role checks
 * - Unauthenticated users redirect to login
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import RoleGate from '../RoleGate';

// Mock useAuth — we control what user is returned
const mockUser = vi.fn();
vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUser(),
}));

function renderWithRouter(element: React.ReactNode, initialPath = '/test') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/test" element={element} />
        <Route path="/" element={<div data-testid="dashboard">Dashboard</div>} />
        <Route path="/login" element={<div data-testid="login">Login</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe('RoleGate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children for authorized role', () => {
    mockUser.mockReturnValue({
      user: { username: 'testadmin', role: 'admin', email: 'a@b.com', full_name: 'Admin' },
    });

    renderWithRouter(
      <RoleGate roles={['admin', 'msp_admin']}>
        <div data-testid="protected">Secret Content</div>
      </RoleGate>
    );

    expect(screen.getByTestId('protected')).toBeInTheDocument();
    expect(screen.getByText('Secret Content')).toBeInTheDocument();
  });

  it('redirects unauthorized role to dashboard', () => {
    mockUser.mockReturnValue({
      user: { username: 'testviewer', role: 'viewer', email: 'v@b.com', full_name: 'Viewer' },
    });

    renderWithRouter(
      <RoleGate roles={['admin', 'msp_admin']}>
        <div data-testid="protected">Secret Content</div>
      </RoleGate>
    );

    // Should redirect to dashboard, not show protected content
    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });

  it('platform admin (username=admin) bypasses all role checks', () => {
    mockUser.mockReturnValue({
      user: { username: 'admin', role: 'admin', email: 'admin@test.com', full_name: 'Platform Admin' },
    });

    // Even though roles only allows 'msp_admin', platform admin should pass
    renderWithRouter(
      <RoleGate roles={['msp_admin']}>
        <div data-testid="protected">MSP Content</div>
      </RoleGate>
    );

    expect(screen.getByTestId('protected')).toBeInTheDocument();
  });

  it('redirects unauthenticated users to login', () => {
    mockUser.mockReturnValue({ user: null });

    renderWithRouter(
      <RoleGate roles={['admin']}>
        <div data-testid="protected">Admin Content</div>
      </RoleGate>
    );

    expect(screen.queryByTestId('protected')).not.toBeInTheDocument();
    expect(screen.getByTestId('login')).toBeInTheDocument();
  });

  it('allows msp_admin to access msp routes', () => {
    mockUser.mockReturnValue({
      user: { username: 'testmsp', role: 'msp_admin', email: 'm@b.com', full_name: 'MSP Admin' },
    });

    renderWithRouter(
      <RoleGate roles={['platform_admin', 'msp_admin', 'admin']}>
        <div data-testid="msp-page">MSP Dashboard</div>
      </RoleGate>
    );

    expect(screen.getByTestId('msp-page')).toBeInTheDocument();
  });

  it('blocks operator from admin-only routes', () => {
    mockUser.mockReturnValue({
      user: { username: 'testop', role: 'operator', email: 'op@b.com', full_name: 'Operator' },
    });

    renderWithRouter(
      <RoleGate roles={['platform_admin', 'admin']}>
        <div data-testid="admin-page">Feature Config</div>
      </RoleGate>
    );

    expect(screen.queryByTestId('admin-page')).not.toBeInTheDocument();
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });

  it('blocks restore_operator from msp routes', () => {
    mockUser.mockReturnValue({
      user: { username: 'testro', role: 'restore_operator', email: 'ro@b.com', full_name: 'Restore Op' },
    });

    renderWithRouter(
      <RoleGate roles={['platform_admin', 'msp_admin', 'admin']}>
        <div data-testid="msp-page">MSP</div>
      </RoleGate>
    );

    expect(screen.queryByTestId('msp-page')).not.toBeInTheDocument();
  });

  it('supports custom redirect path', () => {
    mockUser.mockReturnValue({
      user: { username: 'testviewer', role: 'viewer', email: 'v@b.com', full_name: 'Viewer' },
    });

    render(
      <MemoryRouter initialEntries={['/test']}>
        <Routes>
          <Route
            path="/test"
            element={
              <RoleGate roles={['admin']} redirectTo="/login">
                <div>Admin Only</div>
              </RoleGate>
            }
          />
          <Route path="/login" element={<div data-testid="login">Login Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByTestId('login')).toBeInTheDocument();
  });
});
