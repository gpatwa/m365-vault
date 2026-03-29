import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Copy, Check } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  correlationId: string;
  copied: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null, correlationId: '', copied: false };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      correlationId: Math.random().toString(36).substring(2, 10),
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[Shieldio:ErrorBoundary]', error, info.componentStack);
  }

  handleCopy = () => {
    const text = `Error: ${this.state.error?.message}\nCorrelation ID: ${this.state.correlationId}`;
    navigator.clipboard.writeText(text).then(() => {
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="min-h-[50vh] flex items-center justify-center p-8">
          <div className="max-w-md w-full text-center space-y-6">
            <div className="w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white mb-2">Something went wrong</h2>
              <p className="text-gray-400 text-sm">
                An unexpected error occurred. Our team has been notified.
              </p>
            </div>
            {this.state.error && (
              <div className="bg-gray-900/50 border border-gray-700 rounded-lg p-3 text-left">
                <p className="text-xs text-gray-400 font-mono break-all">
                  {this.state.error.message}
                </p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-700">
                  <p className="text-[10px] text-gray-500 font-mono">
                    ID: {this.state.correlationId}
                  </p>
                  <button
                    onClick={this.handleCopy}
                    className="text-gray-500 hover:text-gray-300 transition-colors"
                    title="Copy error details"
                  >
                    {this.state.copied
                      ? <Check className="w-3.5 h-3.5 text-emerald-400" />
                      : <Copy className="w-3.5 h-3.5" />
                    }
                  </button>
                </div>
              </div>
            )}
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => window.location.reload()}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" /> Try Again
              </button>
              <a
                href="/"
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
              >
                <Home className="w-4 h-4" /> Dashboard
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
