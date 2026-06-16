import { useState, useEffect } from "react";
import { Bot, User, Copy, Share2, Bookmark, Volume2, Square, Clock } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { toast } from "sonner";
import { useNotes } from "../../hooks/useNotes";
import { useWorkspacePermissions } from "../../hooks/useSettings";

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function MessageBubble({ role, content, agent, chatLanguage, latency }) {
  const isUser = role === "user";
  const { addNote, isSaved } = useNotes();
  const { canManageNotes } = useWorkspacePermissions();
  const saved = isSaved(content, agent?.id || null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useState(new Audio())[0];

  useEffect(() => {
    return () => {
      audioRef.pause();
      audioRef.src = "";
    };
  }, [audioRef]);

  const handleTTS = async () => {
    if (isSpeaking) {
      audioRef.pause();
      setIsSpeaking(false);
      return;
    }

    if (!content) return;

    // Strip markdown characters to make speech natural
    const cleanText = content
      .replace(/!\[.*?\]\(.*?\)/g, '') // Remove images
      .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Convert links to plain text
      .replace(/[*_~`#>-]/g, ' ') // Replace formatting characters with spaces
      .trim();

    if (!cleanText) return;

    try {
      setIsSpeaking(true);
      const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${API_URL}/api/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: cleanText,
          language: chatLanguage || "en"
        })
      });

      if (!response.ok) throw new Error("TTS failed");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      
      audioRef.src = url;
      audioRef.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(url);
      };
      
      audioRef.play();
    } catch (error) {
      console.error("TTS Error:", error);
      setIsSpeaking(false);
      toast.error("Failed to play audio");
    }
  };

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
    <div className={`animate-message flex gap-4 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div
          className="
          h-10
          w-10
          rounded-2xl
          bg-primary
          text-primary-foreground
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
            ? "bg-primary text-primary-foreground"
            : "bg-card border border-border text-foreground"
        }
      `}
      >
        <div className="prose max-w-none text-inherit dark:prose-invert whitespace-pre-wrap break-words">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || "");
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={vscDarkPlus}
                    language={match[1]}
                    PreTag="div"
                    className="rounded-md"
                    {...props}
                  >
                    {String(children).replace(/\n$/, "")}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>
        {!isUser && (
          <div className="flex items-center justify-between mt-4 gap-8">
            <div
              className="
              flex
              gap-2
              opacity-0
              group-hover:opacity-100
              transition-all
            "
            >
              <button
                onClick={handleCopy}
                type="button"
                className="p-2 rounded-xl hover:bg-muted"
                title="Copy response"
              >
                <Copy size={16} />
              </button>

              {canManageNotes && (
                <button
                  onClick={handleSave}
                  type="button"
                  className={`p-2 rounded-xl hover:bg-muted ${
                    saved ? "text-primary" : ""
                  }`}
                  title={saved ? "Saved to notes" : "Save response to notes"}
                  aria-pressed={saved}
                >
                  <Bookmark
                    size={16}
                    fill={saved ? "currentColor" : "none"}
                  />
                </button>
              )}

              <button
                onClick={handleTTS}
                type="button"
                className={`p-2 rounded-xl hover:bg-muted ${isSpeaking ? "text-primary" : ""}`}
                title={isSpeaking ? "Stop speaking" : "Read aloud"}
              >
                {isSpeaking ? <Square size={16} fill="currentColor" /> : <Volume2 size={16} />}
              </button>

              <button
                type="button"
                className="p-2 rounded-xl hover:bg-muted"
                title="Share response"
              >
                <Share2 size={16} />
              </button>
            </div>

            {latency && (
              <span className="text-[11px] font-mono text-muted-foreground/75 flex items-center gap-1 select-none">
                <Clock size={12} className="text-muted-foreground/60" />
                {latency < 1000 ? `${latency.toFixed(0)}ms` : `${(latency / 1000).toFixed(2)}s`}
              </span>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div
          className="
          h-10
          w-10
          rounded-2xl
          bg-muted
          text-muted-foreground
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
