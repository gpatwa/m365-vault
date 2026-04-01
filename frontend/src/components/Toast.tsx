import { createContext, useCallback, useContext, useState, useRef, useEffect, type ReactNode } from 'react';
import { AlertCircle, CheckCircle, Info, X, XCircle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  correlationId?: string;
  duration?: number;
}

interface ToastContextValue {
  toast: (t: Omit<Toast, 'id'>) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string, correlationId?: string) => void;
  warning: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

const ICONS: Record<ToastType, ReactNode> = {
  success: <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />,
  error: <XCircle className="w-5 h-5 text-red-400 shrink-0" />,
  warning: <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />,
  info: <Info className="w-5 h-5 text-blue-400 shrink-0" />,
};

const BG: Record<ToastType, string> = {
  success: 'border-emerald-500/30 bg-emerald-950/80',
  error: 'border-red-500/30 bg-red-950/80',
  warning: 'border-amber-500/30 bg-amber-950/80',
  info: 'border-blue-500/30 bg-blue-950/80',
};

function ToastItem({ t, onDismiss }: { t: Toast; onDismiss: (id: string) => void }) {
  const [exiting, setExiting] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    const dur = t.duration ?? (t.type === 'error' ? 8000 : 4000);
    timerRef.current = setTimeout(() => {
      setExiting(true);
      setTimeout(() => onDismiss(t.id), 300);
    }, dur);
    return () => clearTimeout(timerRef.current);
  }, [t, onDismiss]);

  return (
    <div
      className={`flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-sm
        ${BG[t.type]} text-foreground max-w-sm w-full
        transition-all duration-300 ${exiting ? 'opacity-0 translate-x-4' : 'opacity-100 translate-x-0'}`}
    >
      {ICONS[t.type]}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-sm">{t.title}</p>
        {t.message && <p className="text-xs text-foreground/70 mt-0.5">{t.message}</p>}
        {t.correlationId && (
          <p className="text-[10px] text-muted-foreground mt-1 font-mono">ID: {t.correlationId}</p>
        )}
      </div>
      <button
        onClick={() => { setExiting(true); setTimeout(() => onDismiss(t.id), 300); }}
        className="text-muted-foreground hover:text-foreground shrink-0"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  let counter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((t: Omit<Toast, 'id'>) => {
    const id = `toast-${++counter.current}-${Date.now()}`;
    setToasts(prev => [...prev.slice(-4), { ...t, id }]); // max 5 visible
  }, []);

  const value: ToastContextValue = {
    toast: addToast,
    success: (title, message) => addToast({ type: 'success', title, message }),
    error: (title, message, correlationId) => addToast({ type: 'error', title, message, correlationId }),
    warning: (title, message) => addToast({ type: 'warning', title, message }),
    info: (title, message) => addToast({ type: 'info', title, message }),
    dismiss,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Toast container — fixed top-right */}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem t={t} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
