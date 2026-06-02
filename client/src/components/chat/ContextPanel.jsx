import {
  FileText,
  Globe,
} from "lucide-react";

function getSourceIcon(filename = "") {
  return filename.startsWith("http")
    ? Globe
    : FileText;
}

export default function ContextPanel({
  documents = [],
  isLoading = false,
}) {
  return (
    <div className="hidden w-80 border-l border-slate-200 bg-white dark:border-zinc-800 dark:bg-zinc-950 xl:block">
      <div className="p-6">
        <h3 className="font-semibold text-lg text-slate-950 dark:text-zinc-50">
          Context
        </h3>

        <p className="text-sm text-slate-500 mt-1 dark:text-zinc-400">
          Sources used by the agent
        </p>
      </div>

      <div className="px-4 space-y-3">
        {isLoading && (
          <>
            <div className="h-20 rounded-2xl bg-slate-100 animate-pulse dark:bg-zinc-800" />
            <div className="h-20 rounded-2xl bg-slate-100 animate-pulse dark:bg-zinc-800" />
          </>
        )}

        {!isLoading && documents.length === 0 && (
          <div className="border border-dashed rounded-2xl p-4 text-sm text-slate-500 dark:border-zinc-800 dark:text-zinc-400">
            No sources available for this agent.
          </div>
        )}

        {!isLoading &&
          documents.slice(0, 5).map((document) => {
            const Icon = getSourceIcon(
              document.filename,
            );

            return (
              <div
                key={document.id}
                className="border border-slate-200 rounded-2xl p-4 transition hover:bg-slate-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
              >
                <div className="flex gap-3">
                  <Icon size={18} className="text-slate-500 dark:text-zinc-400" />
                  <div className="min-w-0">
                    <div className="font-medium truncate text-slate-900 dark:text-zinc-100">
                      {document.filename}
                    </div>

                    <div className="text-xs text-slate-500 capitalize dark:text-zinc-400">
                      {document.status || "available"}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
      </div>
    </div>
  );
}
