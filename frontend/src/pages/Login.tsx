import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { Shield, Mail, HardDrive, Globe, MessageSquare, KeyRound, Lock, ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

const PROTECTED_APPS = [
  { icon: Mail, label: 'Exchange', color: 'text-blue-500' },
  { icon: HardDrive, label: 'OneDrive', color: 'text-purple-500' },
  { icon: Globe, label: 'SharePoint', color: 'text-green-500' },
  { icon: MessageSquare, label: 'Teams', color: 'text-pink-500' },
  { icon: KeyRound, label: 'Entra ID', color: 'text-amber-500' },
];

const TRUST_POINTS = [
  'AES-256-GCM encryption',
  'Per-tenant isolation',
  'SOC 2 ready',
  'GDPR compliant',
];

export default function Login() {
  const [searchParams] = useSearchParams();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isRegister, setIsRegister] = useState(searchParams.get('register') === 'true');
  const [forgotMode, setForgotMode] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotSent, setForgotSent] = useState(false);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [ssoEnabled, setSsoEnabled] = useState(false);
  const [ssoLoading, setSsoLoading] = useState(false);
  const { login: authLogin } = useAuth();
  const navigate = useNavigate();

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
      if (data.auth_url) window.location.href = data.auth_url;
    } catch (err: any) {
      setError(err.message || 'SSO login failed');
      setSsoLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      if (isRegister) {
        await api.register({ username, email, password, full_name: fullName || undefined, role: 'admin' });
      }
      await authLogin(username, password);
      console.log('[KavachIQ] Login success. Token:', api.getToken()?.substring(0, 20) + '...');
      // Navigate to home — SmartHome will route based on user role
      console.log('[KavachIQ] Login success, navigating to /');
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel — visual storytelling */}
      <div className="hidden lg:flex flex-col flex-1 bg-gradient-to-br from-background via-background to-blue-900 relative overflow-hidden">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 left-20 w-64 h-64 bg-blue-500/100 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-indigo-500/100 rounded-full blur-3xl" />
        </div>

        <div className="relative flex flex-col justify-between flex-1 p-12">
          {/* Top: Logo + nav */}
          <div className="flex items-center justify-between">
            <Link to="/welcome" className="flex items-center gap-2 group">
              <Shield className="w-7 h-7 text-blue-400 group-hover:text-blue-300 transition-colors" />
              <span className="text-lg font-bold text-foreground">KavachIQ</span>
            </Link>
            <Link to="/welcome" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
              Back to home
            </Link>
          </div>

          {/* Center: Value prop */}
          <div className="max-w-lg">
            <h2 className="text-4xl font-extrabold text-foreground leading-tight mb-4">
              Your data deserves<br />
              <span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                better protection.
              </span>
            </h2>
            <p className="text-muted-foreground text-lg leading-relaxed mb-10">
              Join organizations that trust KavachIQ to protect their
              most critical SaaS data — with zero vendor lock-in.
            </p>

            {/* Protected apps */}
            <div className="mb-8">
              <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold mb-3">Protected Platforms</p>
              <div className="flex items-center gap-4">
                {PROTECTED_APPS.map(app => (
                  <div key={app.label} className="group flex flex-col items-center gap-1.5">
                    <div className="w-11 h-11 bg-card border border-border rounded-xl flex items-center justify-center group-hover:border-border group-hover:bg-muted transition-all">
                      <app.icon className={`w-5 h-5 ${app.color}`} />
                    </div>
                    <span className="text-[10px] text-muted-foreground group-hover:text-muted-foreground transition-colors">{app.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Trust badges */}
            <div className="flex flex-wrap items-center gap-3">
              {TRUST_POINTS.map(point => (
                <div key={point} className="flex items-center gap-1.5 px-2.5 py-1 bg-card/50 border border-border rounded-full">
                  <Lock className="w-3 h-3 text-green-400" />
                  <span className="text-[11px] text-muted-foreground">{point}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Bottom: testimonial placeholder */}
          <div className="bg-card/30 border border-border rounded-xl p-5">
            <p className="text-sm text-muted-foreground italic leading-relaxed">
              "We needed a backup solution we could host ourselves for compliance.
              KavachIQ gave us enterprise-grade protection with full data sovereignty."
            </p>
            <div className="flex items-center gap-3 mt-3">
              <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-xs font-bold">IT</div>
              <div>
                <p className="text-xs text-muted-foreground font-medium">IT Director</p>
                <p className="text-[11px] text-muted-foreground">Enterprise Customer</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex items-center justify-center flex-1 lg:flex-none lg:w-[460px] bg-card p-8">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center gap-2 mb-8">
            <Shield className="w-8 h-8 text-primary" />
            <span className="text-xl font-bold text-foreground">KavachIQ</span>
          </div>

          {/* Heading */}
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-foreground">
              {isRegister ? 'Create your account' : 'Sign in'}
            </h1>
            <p className="text-muted-foreground mt-1.5 text-sm">
              {isRegister
                ? 'Set up your admin account to get started.'
                : 'Welcome back. Enter your credentials to continue.'}
            </p>
          </div>

          {/* SSO button first (primary action for enterprise) */}
          {ssoEnabled && (
            <>
              <button
                onClick={handleSSO}
                disabled={ssoLoading}
                className="w-full py-2.5 bg-card border-2 border-border rounded-xl font-medium text-foreground hover:bg-muted/50 hover:border-border transition-all flex items-center justify-center gap-3"
              >
                <svg className="w-5 h-5" viewBox="0 0 21 21"><path d="M0 0h10v10H0z" fill="#f25022"/><path d="M11 0h10v10H11z" fill="#7fba00"/><path d="M0 11h10v10H0z" fill="#00a4ef"/><path d="M11 11h10v10H11z" fill="#ffb900"/></svg>
                {ssoLoading ? 'Redirecting...' : 'Continue with Microsoft'}
              </button>
              <div className="relative my-5">
                <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border" /></div>
                <div className="relative flex justify-center"><span className="bg-card px-3 text-xs text-muted-foreground">or sign in with credentials</span></div>
              </div>
            </>
          )}

          {/* Error */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl p-3 mb-4 text-sm flex items-start gap-2">
              <div className="w-4 h-4 bg-red-500/20 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-[10px] font-bold">!</span>
              </div>
              {error}
            </div>
          )}

          {/* Form */}
          {/* Forgot Password Mode */}
          {forgotMode && !forgotSent && (
            <div className="space-y-4 mb-6">
              <p className="text-sm text-muted-foreground">Enter your email and we'll send you a reset link.</p>
              <input type="email" value={forgotEmail} onChange={e => setForgotEmail(e.target.value)}
                placeholder="Enter your email"
                className="w-full px-3.5 py-2.5 border border-input bg-transparent rounded-xl text-sm text-foreground focus:ring-2 focus:ring-ring" />
              {error && <p className="text-xs text-red-400">{error}</p>}
              <button onClick={async () => {
                try {
                  await api.post('/auth/forgot-password', { email: forgotEmail });
                  setForgotSent(true);
                } catch (e: any) { setError(e.message || 'Failed to send'); }
              }} className="w-full py-2.5 bg-primary text-primary-foreground rounded-xl font-semibold">
                Send Reset Link
              </button>
              <button onClick={() => { setForgotMode(false); setError(''); }} className="w-full text-sm text-muted-foreground hover:text-foreground">
                Back to Sign In
              </button>
            </div>
          )}
          {forgotMode && forgotSent && (
            <div className="text-center py-6">
              <div className="w-12 h-12 bg-teal-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <Mail className="w-6 h-6 text-teal-400" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-1">Check Your Email</h3>
              <p className="text-sm text-muted-foreground mb-4">If that email exists, a reset link has been sent.</p>
              <button onClick={() => { setForgotMode(false); setForgotSent(false); setError(''); }}
                className="text-sm text-primary hover:text-primary/80 font-medium">Back to Sign In</button>
            </div>
          )}

          {!forgotMode && <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-1.5">
                {isRegister ? 'Work Email' : 'Email or Username'}
              </label>
              <input
                type={isRegister ? 'email' : 'text'}
                name="kavachiq-username"
                autoComplete="off"
                value={isRegister ? email : username}
                onChange={e => {
                  if (isRegister) {
                    setEmail(e.target.value);
                    setUsername(e.target.value.split('@')[0]); // Auto-generate username from email
                  } else {
                    setUsername(e.target.value);
                  }
                }}
                placeholder={isRegister ? 'you@company.com' : 'Email or username'}
                className="w-full px-3.5 py-2.5 border border-input bg-transparent rounded-xl text-sm text-foreground focus:ring-2 focus:ring-ring focus:border-ring placeholder:text-muted-foreground/50 transition-colors"
                required
                autoFocus
              />
            </div>

            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1.5">Full Name <span className="text-muted-foreground font-normal">(optional)</span></label>
                <input
                  type="text"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  placeholder="Your name"
                  className="w-full px-3.5 py-2.5 border border-input bg-transparent rounded-xl text-sm text-foreground focus:ring-2 focus:ring-ring focus:border-ring placeholder:text-muted-foreground/50 transition-colors"
                />
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm font-medium text-muted-foreground">Password</label>
                {!isRegister && (
                  <button type="button" onClick={() => { setForgotMode(true); setError(''); }} className="text-xs text-primary hover:text-primary/80 font-medium">
                    Forgot password?
                  </button>
                )}
              </div>
              <input
                type="password"
                name="kavachiq-password"
                autoComplete="off"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder={isRegister ? 'Min 8 chars, 1 uppercase, 1 digit' : 'Enter your password'}
                className="w-full px-3.5 py-2.5 border border-input bg-transparent rounded-xl text-sm text-foreground focus:ring-2 focus:ring-ring focus:border-ring placeholder:text-muted-foreground/50 transition-colors"
                required
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-primary text-primary-foreground rounded-xl font-semibold hover:bg-primary/90 transition-all hover:shadow-lg hover:shadow-primary/20 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
              ) : (
                <>
                  {isRegister ? 'Create Account' : 'Sign In'}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>}

          {/* Toggle register/login */}
          <p className="text-center text-sm text-muted-foreground mt-6">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button
              onClick={() => { setIsRegister(!isRegister); setError(''); }}
              className="text-primary hover:text-primary/80 font-semibold transition-colors"
            >
              {isRegister ? 'Sign In' : 'Create Account'}
            </button>
          </p>

          {/* Footer */}
          <div className="mt-8 pt-6 border-t border-border text-center">
            <p className="text-[11px] text-muted-foreground">
              Free for up to 25 users.{' '}
              <Link to="/legal?tab=tos" className="underline hover:text-foreground">Terms</Link>
              {' '}&bull;{' '}
              <Link to="/legal?tab=privacy" className="underline hover:text-foreground">Privacy</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
