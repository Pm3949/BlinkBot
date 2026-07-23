import { useState, useEffect } from "react";
import { Bot, User, Copy, Volume2, Square, Clock, ThumbsUp, ThumbsDown, Globe, FileText, BookOpen } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

import { useFeedback } from "../../hooks/useFeedback";
import FeedbackModal from "./FeedbackModal";
import { getAuthHeaders } from "../../lib/api";

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function MessageBubble({ id, role, content, agent, chatLanguage, latency, status, sources }) {
  const isUser = role === "user";

  const isWebSource = content?.startsWith("[WEB_SOURCE]");
  const displayContent = isWebSource ? content.replace("[WEB_SOURCE]", "").trim() : content;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useState(new Audio())[0];
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [isSourcesModalOpen, setIsSourcesModalOpen] = useState(false);
  const [vote, setVote] = useState(null);
  const { submitMutation } = useFeedback();

  const isMasterAgent = agent?.name?.toLowerCase().includes("master") && !content?.includes("[Routed to:");

  const hasSources = Array.isArray(sources) && sources.length > 0;
  const maxRelevance = hasSources
    ? Math.max(...sources.map((s) => s.relevance_percent ?? Math.round((s.similarity || 0) * 100)))
    : null;

  const handleUpvote = async () => {
    if (vote) return;
    setVote("upvote");
    toast.success("Thank you for your feedback!");
  };

  const handleDownvote = () => {
    if (vote) return;
    setIsFeedbackModalOpen(true);
  };

  const handleFeedbackSubmit = async (data) => {
    try {
      await submitMutation.mutateAsync({
        message_id: id,
        agent_id: agent?.id,
        vote_type: "downvote",
        category: data.category,
        comment_text: data.comment_text,
      });
      setVote("downvote");
      setIsFeedbackModalOpen(false);
      toast.success("Feedback submitted! AI memory temporarily patched.");
    } catch (e) {
      toast.error("Failed to submit feedback.");
    }
  };

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

    const cleanText = displayContent
      .replace(/!\[.*?\]\(.*?\)/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/[*_~`#>-]/g, ' ')
      .trim();

    if (!cleanText) return;

    try {
      setIsSpeaking(true);
      const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${API_URL}/api/tts`, {
        method: "POST",
        headers: getAuthHeaders(),
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
    if (!displayContent?.trim()) {
      toast.error("Nothing to copy yet.");
      return;
    }

    try {
      await navigator.clipboard.writeText(displayContent);
      toast.success("Copied");
    } catch {
      toast.error("Copy failed. Please try again.");
    }
  };

  return (
    <div className={`animate-message flex gap-4 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div
          className={`
          h-10
          w-10
          rounded-2xl
          flex
          items-center
          justify-center
          ${isMasterAgent ? "bg-purple-600 text-white shadow-md shadow-purple-500/20" : "bg-primary text-primary-foreground"}
        `}
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
            : isMasterAgent
              ? "bg-purple-50/50 border border-purple-200 text-foreground dark:bg-purple-950/20 dark:border-purple-800"
              : "bg-card border border-border text-foreground"
        }
      `}
      >
        <div className="prose max-w-none text-inherit dark:prose-invert whitespace-pre-wrap break-words">
          {isWebSource && (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-500 bg-blue-500/10 border border-blue-500/20 w-fit px-2.5 py-1 rounded-full mb-3">
              <Globe size={12} />
              Answered from Web
            </div>
          )}
          {status && !displayContent && (
             <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                <span className="flex gap-1 mr-1">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce" />
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:150ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:300ms]" />
                </span>
                {status}
             </div>
          )}
          {displayContent && (
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
              img({ node, ...props }) {
                return (
                  <img
                    {...props}
                    className="my-4 max-h-80 w-auto rounded-xl border border-border shadow-sm object-contain"
                    loading="lazy"
                  />
                );
              },
            }}
          >
            {displayContent}
          </ReactMarkdown>
          )}
        </div>
        {!isUser && (
          <div className="flex items-center justify-between mt-4 gap-4">
            <div className="flex items-center gap-2">
              <div
                className="
                flex
                gap-1
                text-muted-foreground/80
                hover:text-foreground
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

                <button
                  onClick={handleUpvote}
                  disabled={!!vote}
                  type="button"
                  className={`p-2 rounded-xl hover:bg-muted ${vote === "upvote" ? "text-green-500" : ""}`}
                  title="Helpful response"
                >
                  <ThumbsUp size={16} />
                </button>

                <button
                  onClick={handleDownvote}
                  disabled={!!vote}
                  type="button"
                  className={`p-2 rounded-xl hover:bg-muted ${vote === "downvote" ? "text-destructive" : ""}`}
                  title="Report issue"
                >
                  <ThumbsDown size={16} />
                </button>

                <button
                  onClick={handleTTS}
                  type="button"
                  className={`p-2 rounded-xl hover:bg-muted ${isSpeaking ? "text-primary" : ""}`}
                  title={isSpeaking ? "Stop speaking" : "Read aloud"}
                >
                  {isSpeaking ? <Square size={16} fill="currentColor" /> : <Volume2 size={16} />}
                </button>
              </div>

              {/* Dynamic RAG Source Citation Inspector Button */}
              {hasSources && (
                <button
                  type="button"
                  onClick={() => setIsSourcesModalOpen(true)}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 text-xs font-semibold transition"
                  title="View retrieved RAG document sources"
                >
                  <BookOpen size={13} />
                  <span>{maxRelevance}% Relevance ({sources.length} {sources.length === 1 ? 'Source' : 'Sources'})</span>
                </button>
              )}
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
      
      <FeedbackModal
        isOpen={isFeedbackModalOpen}
        onClose={() => setIsFeedbackModalOpen(false)}
        onSubmit={handleFeedbackSubmit}
        isSubmitting={submitMutation.isPending}
      />

      {/* Dynamic RAG Sources Citation Inspector Modal */}
      {isSourcesModalOpen && hasSources && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
          <div className="bg-card border border-border p-6 rounded-3xl max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border/50 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="text-primary" size={20} />
                <h3 className="font-bold text-base text-foreground">Retrieved RAG Sources (pgvector)</h3>
              </div>
              <button
                type="button"
                onClick={() => setIsSourcesModalOpen(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {sources.map((src, idx) => {
                const score = src.relevance_percent ?? Math.round((src.similarity || 0) * 100);
                const title = src.name || src.filename || src.title || "Document Chunk";
                return (
                  <div key={idx} className="p-4 rounded-2xl border border-primary/20 bg-primary/5 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs text-primary flex items-center gap-1.5">
                        <FileText size={14} /> {title}
                      </span>
                      <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                        {score}% Match
                      </span>
                    </div>
                    {src.content && (
                      <p className="text-xs text-muted-foreground leading-relaxed font-mono bg-background/50 p-2.5 rounded-xl border border-border/40">
                        "{src.content}"
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="pt-2 text-right">
              <button
                type="button"
                onClick={() => setIsSourcesModalOpen(false)}
                className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground text-xs font-semibold rounded-xl"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
