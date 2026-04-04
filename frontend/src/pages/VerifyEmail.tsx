import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Shield, Check, X, Loader2 } from 'lucide-react';
import { api } from '../api/client';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) { setStatus('error'); setError('Missing verification token.'); return; }
    api.post('/auth/verify-email', { token })
      .then(() => setStatus('success'))
      .catch((err: any) => { setStatus('error'); setError(err.message || 'Verification failed.'); });
  }, [token]);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <Shield className="w-10 h-10 text-teal-500 mx-auto mb-6" />

        {status === 'loading' && (
          <div>
            <Loader2 className="w-8 h-8 text-teal-500 animate-spin mx-auto mb-4" />
            <p className="text-muted-foreground">Verifying your email...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="bg-card border border-border rounded-xl p-6">
            <Check className="w-12 h-12 text-teal-500 mx-auto mb-3" />
            <h2 className="text-lg font-semibold text-foreground mb-2">Email Verified!</h2>
            <p className="text-sm text-muted-foreground mb-4">Your email has been confirmed. You're all set.</p>
            <Link to="/" className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium inline-block">
              Go to Dashboard
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="bg-card border border-border rounded-xl p-6">
            <X className="w-12 h-12 text-red-400 mx-auto mb-3" />
            <h2 className="text-lg font-semibold text-foreground mb-2">Verification Failed</h2>
            <p className="text-sm text-muted-foreground mb-4">{error}</p>
            <Link to="/login" className="px-6 py-2.5 bg-muted text-foreground rounded-lg font-medium inline-block">
              Back to Sign In
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
