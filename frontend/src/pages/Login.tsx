import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import { api } from '../api/client';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [ssoLoading, setSsoLoading] = useState(false);
  const navigate = useNavigate();

  // Check if SSO is enabled
  useEffect(() => {
    api.get<{ enabled: boolean }>('/auth/sso/config')
      .then(data => setSsoEnabled(data.enabled))
      .catch(() => setSsoEnabled(false));
  }, []);

  const handleSSO = async () => {
    setSsoLoading(true);
    setError('');
    try {
      const data: any = await api.get('/auth/sso/login');
      if (data.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err: any) {
      setError(err.message || 'SSO login failed');
      setSsoLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (isRegister) {
        await api.register({ username, email, password, role: 'admin' });
      }
      await api.login(username, password);
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex">
      {/* Left panel — product info */}
      <div className="hidden lg:flex flex-col justify-center flex-1 px-16 py-12">
        <div className="max-w-md">
          <div className="flex items-center gap-2 mb-8">
            <Shield className="w-8 h-8 text-blue-400" />
            <span className="text-2xl font-bold text-white">M365 Vault</span>
          </div>
          <h2 className="text-3xl font-bold text-white leading-tight mb-4">
            Enterprise Backup for<br />Microsoft 365
          </h2>
          <p className="text-gray-400 mb-8 leading-relaxed">
            Protect Exchange, OneDrive, SharePoint, Teams, and Entra ID with
            self-hosted, open-source data protection.
          </p>
          <div className="space-y-3">
            {['5 workloads with automated scheduling', 'AES-256-GCM encryption per tenant', 'Smart Engine with zero AI token cost', 'WORM storage + legal hold', 'Self-service restore portal'].map(f => (
              <div key={f} className="flex items-center gap-2 text-sm text-gray-300">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full flex-shrink-0" />
                {f}
              </div>
            ))}
          </div>
          <div className="mt-10 pt-6 border-t border-gray-800">
            <a href="/welcome" className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
              Learn more about M365 Vault →
            </a>
          </div>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex items-center justify-center flex-1 lg:flex-none lg:w-[480px] p-6 bg-white lg:rounded-l-3xl">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="lg:hidden inline-flex items-center justify-center w-14 h-14 bg-blue-100 rounded-2xl mb-4">
            <Shield className="w-7 h-7 text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">
            {isRegister ? 'Create Account' : 'Welcome Back'}
          </h1>
          <p className="text-gray-500 mt-1 text-sm">
            {isRegister ? 'Set up your admin account' : 'Sign in to M365 Vault'}
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          {isRegister && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            {isRegister ? 'Create Account & Sign In' : 'Sign In'}
          </button>
        </form>

        {ssoEnabled && (
          <>
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div>
              <div className="relative flex justify-center text-sm"><span className="bg-white px-3 text-gray-400">or</span></div>
            </div>
            <button
              onClick={handleSSO}
              disabled={ssoLoading}
              className="w-full py-2.5 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" viewBox="0 0 21 21"><path d="M0 0h10v10H0z" fill="#f25022"/><path d="M11 0h10v10H11z" fill="#7fba00"/><path d="M0 11h10v10H0z" fill="#00a4ef"/><path d="M11 11h10v10H11z" fill="#ffb900"/></svg>
              {ssoLoading ? 'Redirecting...' : 'Sign in with Microsoft'}
            </button>
          </>
        )}

        <p className="text-center text-sm text-gray-500 mt-4">
          {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => setIsRegister(!isRegister)}
            className="text-blue-600 hover:underline font-medium"
          >
            {isRegister ? 'Sign In' : 'Register'}
          </button>
        </p>
      </div>
      </div>
    </div>
  );
}
