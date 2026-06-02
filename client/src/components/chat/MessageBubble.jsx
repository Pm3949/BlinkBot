import { Bot, User, Copy, Share2, Bookmark } from "lucide-react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { toast } from "sonner";
import { useNotes } from "../../hooks/useNotes";

export default function MessageBubble({ role, content, agent }) {
  const isUser = role === "user";
  const { addNote, isSaved } = useNotes();
  const saved = isSaved(content, agent?.id || null);

  const handleCopy = async () => {
    if (!content?.trim()) {
      toast.error("Nothing to copy yet.");
      return;
    }

    try {
      await navigator.clipboard.writeText(content);
      toast.success("Copied");
    } catch {
      toast.error("Copy failed. Please try again.");
    }
  };

  const handleSave = () => {
    const note = addNote(content, agent);

    if (note) {
      toast.success(saved ? "Already saved" : "Saved to notes");
    }
  };

  return (
    <div className={`flex gap-4 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div
          className="
          h-10
          w-10
          rounded-2xl
          bg-indigo-600
          text-white
          flex
          items-center
          justify-center
        "
        >
          <Bot size={18} />
        </div>
      )}

      <div
        className={`
        max-w-3xl
        rounded-[28px]
        px-6
        py-5
        shadow-sm
        group
        ${
          isUser
            ? "bg-slate-900 text-white dark:bg-indigo-600"
            : "bg-white border border-slate-200 text-slate-900 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-50"
        }
      `}
      >
        <div className="prose max-w-none prose-slate dark:prose-invert">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
        {!isUser && (
          <div
            className="
            flex
            gap-2
            mt-4
            opacity-0
            group-hover:opacity-100
            transition-all
          "
          >
            <button
              onClick={handleCopy}
              type="button"
              className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800"
              title="Copy response"
            >
              <Copy size={16} />
            </button>

            <button
              onClick={handleSave}
              type="button"
              className={`p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800 ${
                saved ? "text-indigo-600" : ""
              }`}
              title={saved ? "Saved to notes" : "Save response to notes"}
              aria-pressed={saved}
            >
              <Bookmark
                size={16}
                fill={saved ? "currentColor" : "none"}
              />
            </button>

            <button
              type="button"
              className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800"
              title="Share response"
            >
              <Share2 size={16} />
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <div
          className="
          h-10
          w-10
          rounded-2xl
          bg-slate-200
          flex
          items-center
          justify-center
        "
        >
          <User size={18} />
        </div>
      )}
    </div>
  );
}
