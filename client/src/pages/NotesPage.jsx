import {
  Search,
  Download,
  Trash2,
  Pin,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import EmptyState from "../components/shared/EmptyState";
import { useNotes } from "../hooks/useNotes";
import { useWorkspacePermissions } from "../hooks/useSettings";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

const markdownComponents = {
  h1: ({ ...props }) => (
    <h1 className="mb-3 mt-5 text-2xl font-bold text-foreground" {...props} />
  ),
  h2: ({ ...props }) => (
    <h2 className="mb-3 mt-5 text-xl font-semibold text-foreground" {...props} />
  ),
  h3: ({ ...props }) => (
    <h3 className="mb-2 mt-4 text-lg font-semibold text-foreground" {...props} />
  ),
  p: ({ ...props }) => (
    <p
      className="mb-3 whitespace-pre-wrap break-words text-sm leading-7 text-muted-foreground"
      {...props}
    />
  ),
  ul: ({ ...props }) => (
    <ul className="mb-4 ml-5 list-disc space-y-1 text-sm text-muted-foreground" {...props} />
  ),
  ol: ({ ...props }) => (
    <ol className="mb-4 ml-5 list-decimal space-y-1 text-sm text-muted-foreground" {...props} />
  ),
  li: ({ ...props }) => <li className="leading-7" {...props} />,
  blockquote: ({ ...props }) => (
    <blockquote
      className="mb-4 border-l-4 border-primary bg-primary/5 px-4 py-2 text-sm text-muted-foreground"
      {...props}
    />
  ),
  code: ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || "");

    if (!inline && match) {
      return (
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={match[1]}
          PreTag="div"
          className="rounded-md text-xs"
          {...props}
        >
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      );
    }

    return (
      <code
        className="rounded-md bg-muted px-1.5 py-0.5 text-xs font-medium text-foreground"
        {...props}
      >
        {children}
      </code>
    );
  },
  pre: ({ ...props }) => <pre className="mb-4 overflow-x-auto" {...props} />,
  table: ({ ...props }) => (
    <div className="mb-4 overflow-x-auto">
      <table className="w-full border-collapse text-sm" {...props} />
    </div>
  ),
  th: ({ ...props }) => (
    <th
      className="border border-border bg-muted px-3 py-2 text-left font-semibold text-foreground"
      {...props}
    />
  ),
  td: ({ ...props }) => (
    <td className="border border-border px-3 py-2 text-muted-foreground" {...props} />
  ),
  a: ({ ...props }) => (
    <a className="break-words font-medium text-primary underline" {...props} />
  ),
};

function getCleanTitle(value) {
  const title = String(value || "Saved response")
    .replace(/^#{1,6}\s+/, "")
    .replace(/^[-*+]\s+/, "")
    .replace(/^\d+\.\s+/, "")
    .replace(/\*\*/g, "")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();

  return title || "Saved response";
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function markdownToPrintableHtml(markdown) {
  return escapeHtml(markdown)
    .replace(/^###### (.*)$/gm, "<h6>$1</h6>")
    .replace(/^##### (.*)$/gm, "<h5>$1</h5>")
    .replace(/^#### (.*)$/gm, "<h4>$1</h4>")
    .replace(/^### (.*)$/gm, "<h3>$1</h3>")
    .replace(/^## (.*)$/gm, "<h2>$1</h2>")
    .replace(/^# (.*)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n{2,}/g, "</p><p>")
    .replace(/\n/g, "<br />");
}

export default function NotesPage() {
  const { notes, deleteNote, togglePin } = useNotes();
  const { canManageNotes } = useWorkspacePermissions();
  const [query, setQuery] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState("all");
  const hasNotes = notes.length > 0;

  const agentOptions = useMemo(() => {
    const agentsById = new Map();

    notes.forEach((note) => {
      const id = note.agentId || "general";

      if (!agentsById.has(id)) {
        agentsById.set(id, {
          id,
          name: note.agentName || "General",
        });
      }
    });

    return Array.from(agentsById.values()).sort((first, second) =>
      first.name.localeCompare(second.name),
    );
  }, [notes]);

  const filteredNotes = useMemo(() => {
    const search = query.trim().toLowerCase();
    const agentFilteredNotes =
      selectedAgentId === "all"
        ? notes
        : notes.filter((note) => (note.agentId || "general") === selectedAgentId);

    const visibleNotes = search
      ? agentFilteredNotes.filter((note) =>
        `${note.title} ${note.content} ${note.agentName || ""}`
          .toLowerCase()
          .includes(search),
      )
      : agentFilteredNotes;

    return [...visibleNotes].sort(
      (first, second) =>
        Number(Boolean(second.pinned)) - Number(Boolean(first.pinned)) ||
        new Date(second.createdAt).getTime() -
        new Date(first.createdAt).getTime(),
    );
  }, [notes, query, selectedAgentId]);

  const getNoteMarkdown = (note) =>
    `# ${getCleanTitle(note.title)}\nAgent: ${note.agentName || "General"
    }\nSaved: ${new Date(note.createdAt).toLocaleString()}\n\n${note.content}`;

  const printPdf = (title, content) => {
    const printWindow = window.open("", "_blank", "width=900,height=700");

    if (!printWindow) {
      toast.error("Please allow popups to download PDF.");
      return;
    }

    printWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <title>${escapeHtml(title)}</title>
          <style>
            @page { margin: 18mm; }
            body {
              color: #0f172a;
              font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
              line-height: 1.65;
            }
            h1 { font-size: 26px; margin: 0 0 14px; }
            h2 { font-size: 20px; margin: 22px 0 10px; }
            h3 { font-size: 17px; margin: 18px 0 8px; }
            p { margin: 0 0 12px; }
            code {
              background: #f1f5f9;
              border-radius: 4px;
              color: #0f172a;
              font-family: "SFMono-Regular", Consolas, monospace;
              padding: 2px 5px;
            }
            .content {
              border-top: 1px solid #e2e8f0;
              margin-top: 18px;
              padding-top: 18px;
            }
          </style>
        </head>
        <body>
          <div class="content"><p>${markdownToPrintableHtml(content)}</p></div>
          <script>
            window.onload = () => {
              window.print();
            };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  const handleExport = () => {
    if (!hasNotes) return;

    const content = notes
      .map((note) => getNoteMarkdown(note))
      .join("\n\n---\n\n");

    printPdf("ragmate-notes.pdf", content);
    toast.success("PDF export opened");
  };

  const handleDownloadNote = (note) => {
    printPdf(`${getCleanTitle(note.title)}.pdf`, getNoteMarkdown(note));
    toast.success("PDF export opened");
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-4xl font-bold text-foreground">
            Saved Notes
          </h1>

          <p className="text-muted-foreground mt-2">
            Insights collected from your AI conversations.
          </p>
        </div>

        <button
          disabled={!hasNotes}
          onClick={handleExport}
          className="
          px-5
          py-3
          rounded-2xl
          bg-primary
          text-primary-foreground
          hover:bg-primary-hover
          flex
          items-center
          gap-2
          disabled:opacity-60
        "
        >
          <Download size={18} />
          Export All
        </button>
      </div>

      {hasNotes && (
        <div className="mb-6 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setSelectedAgentId("all")}
            className={`rounded-xl px-4 py-2 text-sm font-medium ${selectedAgentId === "all"
                ? "bg-primary text-primary-foreground"
                : "border border-border bg-background text-muted-foreground hover:bg-muted"
              }`}
          >
            All notes
          </button>

          {agentOptions.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => setSelectedAgentId(agent.id)}
              className={`rounded-xl px-4 py-2 text-sm font-medium ${selectedAgentId === agent.id
                  ? "bg-primary text-primary-foreground"
                  : "border border-border bg-background text-muted-foreground hover:bg-muted"
                }`}
            >
              {agent.name}
            </button>
          ))}
        </div>
      )}

      <div className="relative mb-8">
        <Search
          className="
          absolute
          left-4
          top-4
          text-muted-foreground
        "
          size={18}
        />

        <input
          placeholder="Search notes..."
          disabled={!hasNotes}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="
          w-full
          rounded-2xl
          border
          border-border
          bg-background
          text-foreground
          placeholder:text-muted-foreground
          pl-12
          py-4
          disabled:opacity-60
        "
        />
      </div>

      {!hasNotes && (
        <EmptyState
          title="No notes saved yet"
          description="Saved notes from AI conversations will appear here when available."
        />
      )}

      {hasNotes && filteredNotes.length === 0 && (
        <EmptyState
          title="No matching notes"
          description="Try a different search term."
        />
      )}

      {filteredNotes.length > 0 && (
        <div className="grid gap-4">
          {filteredNotes.map((note) => (
            <article
              key={note.id}
              className="
              glass-card
              p-5
            "
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold text-foreground">
                    {getCleanTitle(note.title)}
                  </h2>

                  <p className="mt-1 text-xs text-muted-foreground">
                    Saved {new Date(note.createdAt).toLocaleString()}
                  </p>
                </div>

                <div className="flex shrink-0 items-center gap-1">
                  {canManageNotes && (
                    <button
                      type="button"
                      onClick={() => togglePin(note.id)}
                      className="
                      rounded-xl
                      p-2
                      text-muted-foreground
                      hover:bg-primary/10
                      hover:text-primary
                    "
                      title={note.pinned ? "Unpin note" : "Pin note"}
                      aria-pressed={Boolean(note.pinned)}
                    >
                      <Pin
                        size={16}
                        fill={note.pinned ? "currentColor" : "none"}
                        className={note.pinned ? "text-primary" : ""}
                      />
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => handleDownloadNote(note)}
                    className="
                    rounded-xl
                    p-2
                    text-muted-foreground
                    hover:bg-muted
                    hover:text-foreground
                  "
                    title="Download note"
                  >
                    <Download size={16} />
                  </button>

                  {canManageNotes && (
                    <button
                      type="button"
                      onClick={() => deleteNote(note.id)}
                      className="
                      rounded-xl
                      p-2
                      text-muted-foreground
                      hover:bg-red-500/10
                      hover:text-red-600
                    "
                      title="Delete note"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>

              <p className="mt-1 text-xs text-muted-foreground">
                Agent: {note.agentName || "General"}
              </p>

              <div className="mt-4 min-w-0 overflow-hidden rounded-xl border border-border bg-muted/30 p-4">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                >
                  {note.content}
                </ReactMarkdown>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
