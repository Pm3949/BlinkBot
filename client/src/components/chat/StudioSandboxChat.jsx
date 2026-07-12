import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import ChatComposer from "./ChatComposer";

export default function StudioSandboxChat({
  messages,
  loading,
  onSend,
  agent,
  chatLanguage,
  setChatLanguage,
  onClose
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  return (
    <div className="flex flex-col h-full bg-card/95 backdrop-blur-md border-l border-border/50 shadow-2xl relative z-10 w-[450px]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border/50 bg-background/50">
        <div>
          <h2 className="text-lg font-semibold bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">
            Test Network
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">Live routing visualization</p>
        </div>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground transition-colors p-2 rounded-full hover:bg-muted/50"
          title="Close Sandbox"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6 6 18" />
            <path d="m6 6 12 12" />
          </svg>
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground opacity-70">
            <div className="w-16 h-16 rounded-full bg-purple-500/10 flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-purple-400">
                <path d="M12 8V4H8" />
                <rect width="16" height="12" x="4" y="8" rx="2" />
                <path d="M2 14h2" />
                <path d="M20 14h2" />
                <path d="M15 13v2" />
                <path d="M9 13v2" />
              </svg>
            </div>
            <p className="text-sm">Send a message to watch the<br/>Network Manager route it live.</p>
          </div>
        )}

        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            id={message.id}
            role={message.role}
            agent={agent}
            chatLanguage={chatLanguage}
            latency={message.latency}
            content={message.content}
            status={message.status || (message.role === "assistant" && !message.content ? "Thinking..." : null)}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border/50 bg-background/50 p-2">
        <ChatComposer
          disabled={!agent?.id}
          isLoading={loading}
          onSend={onSend}
          agent={agent}
          chatLanguage={chatLanguage}
          setChatLanguage={setChatLanguage}
          hideAttachment={true}
        />
      </div>
    </div>
  );
}
