import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Shield, Loader2 } from 'lucide-react';
import { api } from '../api/client';

export default function SSOCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');
    const errorDesc = searchParams.get('error_description');

    if (errorParam) {
      setError(errorDesc || errorParam);
      return;
    }

    if (!code || !state) {
      setError('Missing authorization code or state parameter');
      return;
    }

    // Exchange code for token
    api.post('/auth/sso/callback', { code, state })
      .then((data: any) => {
        if (data.access_token) {
          api.setToken(data.access_token);
          navigate('/', { replace: true });
        } else {
          setError('No access token received');
        }
      })
      .catch((err: any) => {
        setError(err.message || 'SSO callback failed');
      });
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500/15 rounded-2xl mb-4">
          <Shield className="w-8 h-8 text-blue-600" />
        </div>
        {error ? (
          <>
            <h2 className="text-xl font-bold text-red-600 mb-2">Sign-in Failed</h2>
            <p className="text-gray-600 text-sm mb-4">{error}</p>
            <button onClick={() => navigate('/login')} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
              Back to Login
            </button>
          </>
        ) : (
          <>
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900">Signing you in...</h2>
            <p className="text-gray-500 text-sm mt-1">Completing Microsoft authentication</p>
          </>
        )}
      </div>
    </div>
  );
}
