/**
 * Restore OAuth Callback — handles the redirect after admin consents to write permissions.
 *
 * Flow:
 * 1. Admin clicks "Restore" → popup opens OAuth consent URL
 * 2. Admin signs in + consents → Microsoft redirects to /restore/callback?code=...&state=...
 * 3. This component sends the code to the backend to exchange for tokens
 * 4. Backend stores tokens in-memory (never persisted)
 * 5. This component closes the popup or redirects back to the restore page
 */
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

export default function RestoreCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('Completing restore authorization...');

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');
    const errorDesc = searchParams.get('error_description');

    if (error) {
      setStatus('error');
      setMessage(`Consent denied: ${errorDesc || error}`);
      return;
    }

    if (!code || !state) {
      setStatus('error');
      setMessage('Missing authorization code. Please try again.');
      return;
    }

    // Exchange code for tokens via backend
    const exchangeCode = async () => {
      try {
        const data: any = await api.get(
          `/restore-consent/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
        );

        if (data.status === 'ready') {
          setStatus('success');
          setMessage('Write permissions granted. You can now restore data.');

          // Store the state token for the restore flow
          sessionStorage.setItem('kavachiq_restore_state', state);
          sessionStorage.setItem('kavachiq_restore_tenant', String(data.tenant_id));

          // Redirect back to recovery page after 2 seconds
          setTimeout(() => navigate('/recovery'), 2000);
        } else {
          setStatus('error');
          setMessage('Authorization failed. Please try again.');
        }
      } catch (err: any) {
        setStatus('error');
        setMessage(err?.message || 'Failed to complete authorization.');
      }
    };

    exchangeCode();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="bg-card rounded-2xl border border-border shadow-lg p-8 max-w-md w-full text-center">
        {status === 'processing' && (
          <>
            <Loader2 className="w-12 h-12 text-teal-400 mx-auto mb-4 animate-spin" />
            <h2 className="text-xl font-bold text-foreground mb-2">Authorizing Restore</h2>
            <p className="text-sm text-muted-foreground">{message}</p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-foreground mb-2">Restore Authorized</h2>
            <p className="text-sm text-muted-foreground">{message}</p>
            <p className="text-xs text-muted-foreground mt-3">Redirecting to recovery page...</p>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-foreground mb-2">Authorization Failed</h2>
            <p className="text-sm text-muted-foreground mb-4">{message}</p>
            <button
              onClick={() => navigate('/recovery')}
              className="px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-semibold hover:bg-teal-500"
            >
              Back to Recovery
            </button>
          </>
        )}
      </div>
    </div>
  );
}
