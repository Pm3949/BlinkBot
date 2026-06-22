import { useRouteError } from "react-router-dom";
import { AlertCircle } from "lucide-react";

export default function RouteErrorFallback() {
  const error = useRouteError();

  return (
    <div className="h-screen flex items-center justify-center bg-slate-50 p-6 dark:bg-zinc-950">
      <div className="max-w-md w-full rounded-3xl border border-red-200 bg-red-50 p-8 text-center shadow-sm dark:bg-red-950/20 dark:border-red-900/50">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/50 mb-4">
          <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
        </div>
        
        <h1 className="text-xl font-bold text-red-900 dark:text-red-50 mb-2">
          Oops! Something went wrong.
        </h1>
        
        <div className="text-sm text-red-800 dark:text-red-200 mb-6 bg-red-100/50 dark:bg-red-900/20 p-4 rounded-xl text-left overflow-auto max-h-32">
          {error?.message || "An unexpected application error occurred."}
        </div>

        <button
          onClick={() => window.location.reload()}
          className="rounded-xl bg-red-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 transition-colors"
        >
          Reload page
        </button>
      </div>
    </div>
  );
}
