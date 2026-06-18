import { useState, useEffect } from "react";
import { Bot, User, Copy, Share2, Volume2, Square, Clock, ThumbsUp, ThumbsDown, Globe } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { toast } from "sonner";

import { useFeedback } from "../../hooks/useFeedback";
import FeedbackModal from "./FeedbackModal";



import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function MessageBubble({ id, role, content, agent, chatLanguage, latency }) {
  const isUser = role === "user";

  const isWebSource = content?.startsWith("[WEB_SOURCE]");
  const displayContent = isWebSource ? content.replace("[WEB_SOURCE]", "").trim() : content;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const audioRef = useState(new Audio())[0];
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [vote, setVote] = useState(null);
  const { submitMutation } = useFeedback();

  const handleUpvote = async () => {
    if (vote) return;
    setVote("upvote");
    toast.success("Thank you for your feedback!");
    // We don't hit the API for upvotes anymore to save DB space
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

    // Strip markdown characters to make speech natural
    const cleanText = displayContent
      .replace(/!\[.*?\]\(.*?\)/g, '') // Remove images
      .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Convert links to plain text
      .replace(/[*_~`#>-]/g, ' ') // Replace formatting characters with spaces
      .trim();

    if (!cleanText) return;

    try {
      setIsSpeaking(true);
      const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;
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
          {isWebSource && (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-blue-500 bg-blue-500/10 border border-blue-500/20 w-fit px-2.5 py-1 rounded-full mb-3">
              <Globe size={12} />
              Answered from Web
            </div>
          )}
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
      
      <FeedbackModal
        isOpen={isFeedbackModalOpen}
        onClose={() => setIsFeedbackModalOpen(false)}
        onSubmit={handleFeedbackSubmit}
        isSubmitting={submitMutation.isPending}
      />
    </div>
  );
}
