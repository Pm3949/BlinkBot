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
    console.error("RagMate render error", error, info);
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
              RagMate hit an unexpected rendering error. Refresh the page to try again.
            </p>

            <button
              onClick={() => window.location.reload()}
              className="mt-6 rounded-2xl bg-[var(--primary)] px-5 py-3 text-white hover:bg-[var(--primary-hover)]"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
