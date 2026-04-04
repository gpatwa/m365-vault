import { useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Shield, Lock, ArrowRight, Check } from 'lucide-react';
import { api } from '../api/client';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [status, setStatus] = useState<'form' | 'loading' | 'success' | 'error'>('form');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setError('Passwords do not match'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return; }
    setStatus('loading');
    try {
      await api.post('/auth/reset-password', { token, new_password: password });
      setStatus('success');
    } catch (err: any) {
      setError(err.message || 'Reset failed. Token may be expired.');
      setStatus('error');
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Shield className="w-10 h-10 text-teal-500 mx-auto mb-3" />
          <h1 className="text-2xl font-bold text-foreground">Reset Your Password</h1>
        </div>

        {status === 'success' ? (
          <div className="bg-card border border-border rounded-xl p-6 text-center">
            <Check className="w-12 h-12 text-teal-500 mx-auto mb-3" />
            <h2 className="text-lg font-semibold text-foreground mb-2">Password Reset!</h2>
            <p className="text-sm text-muted-foreground mb-4">Your password has been updated. You can now sign in.</p>
            <Link to="/login" className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium inline-flex items-center gap-2">
              Sign In <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="bg-card border border-border rounded-xl p-6 space-y-4">
            {!token && <p className="text-sm text-red-400">Missing reset token. Please use the link from your email.</p>}
            {error && <p className="text-sm text-red-400">{error}</p>}
            <div>
              <label className="text-xs font-medium text-muted-foreground">New Password</label>
              <div className="relative mt-1">
                <Lock className="absolute left-3 top-2.5 w-4 h-4 text-muted-foreground" />
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8}
                  className="w-full pl-10 pr-4 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring"
                  placeholder="Minimum 8 characters" />
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Confirm Password</label>
              <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required
                className="w-full mt-1 px-4 py-2 border border-border rounded-lg bg-background text-foreground text-sm focus:ring-2 focus:ring-ring"
                placeholder="Re-enter password" />
            </div>
            <button type="submit" disabled={status === 'loading' || !token}
              className="w-full py-2.5 bg-teal-600 text-white rounded-lg font-medium disabled:opacity-50">
              {status === 'loading' ? 'Resetting...' : 'Reset Password'}
            </button>
            <Link to="/login" className="block text-center text-sm text-muted-foreground hover:text-foreground">
              Back to Sign In
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
