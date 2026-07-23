import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = {
    hasError: false,
    error: null,
  };

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error, info) {
    console.error("BlinkBot render error", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex items-center justify-center bg-slate-50 p-6 dark:bg-zinc-950">
          <div className="max-w-md rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:bg-zinc-900 dark:border-zinc-800">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-zinc-50">
              Something went wrong.
            </h1>

            <p className="mt-3 text-sm text-slate-500 dark:text-zinc-400">
              BlinkBot hit an unexpected rendering error. Refresh the page or reset state to try again.
            </p>

            {this.state.error && (
              <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-500 font-mono text-left overflow-auto max-h-32">
                {this.state.error.toString()}
              </div>
            )}

            <div className="mt-6 flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="rounded-2xl bg-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-primary/90"
              >
                Reload Page
              </button>
              <button
                onClick={() => {
                  localStorage.clear();
                  window.location.href = "/";
                }}
                className="rounded-2xl border border-border px-5 py-2.5 text-sm font-semibold text-foreground hover:bg-muted"
              >
                Clear State & Reset
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
