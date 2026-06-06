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
    <div className="hidden w-80 border-l border-border bg-card xl:block">
      <div className="p-6">
        <h3 className="font-semibold text-lg text-foreground">
          Context
        </h3>

        <p className="text-sm text-muted-foreground mt-1">
          Sources used by the agent
        </p>
      </div>

      <div className="px-4 space-y-3">
        {isLoading && (
          <>
            <div className="h-20 rounded-2xl bg-muted animate-pulse" />
            <div className="h-20 rounded-2xl bg-muted animate-pulse" />
          </>
        )}

        {!isLoading && documents.length === 0 && (
          <div className="border border-dashed rounded-2xl p-4 text-sm text-muted-foreground border-border">
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
                className="border border-border rounded-2xl p-4 transition hover:bg-muted"
              >
                <div className="flex gap-3">
                  <Icon size={18} className="text-muted-foreground" />
                  <div className="min-w-0">
                    <div className="font-medium truncate text-foreground">
                      {document.filename}
                    </div>

                    <div className="text-xs text-muted-foreground capitalize">
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
