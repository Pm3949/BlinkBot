import { useEffect, useRef } from "react";
import { ShieldAlert, Check, X } from "lucide-react";
import MessageBubble from "./MessageBubble";
import ChatComposer from "./ChatComposer";

export default function StudioSandboxChat({
  messages,
  loading,
  onSend,
  agent,
  chatLanguage,
  setChatLanguage,
  onClose,
  pendingApproval,
  sendApprovalResponse
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
        {pendingApproval && (
          <div className="p-4 border border-amber-500/20 bg-amber-500/5 rounded-2xl shadow-sm space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-center gap-2 text-amber-500 font-semibold text-xs">
              <ShieldAlert size={16} />
              <span>Action Approval Required</span>
            </div>
            <div className="text-xs text-muted-foreground space-y-2">
              <p>
                Agent wants to run <span className="font-semibold text-foreground font-mono bg-muted px-1 py-0.5 rounded border border-border">{pendingApproval.tool_name}</span>:
              </p>
              <pre className="p-2.5 bg-muted border border-border rounded-xl text-[10px] overflow-x-auto font-mono text-foreground max-h-40">
                {JSON.stringify(pendingApproval.arguments, null, 2)}
              </pre>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => sendApprovalResponse("approve", pendingApproval.tool_call_id)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-600 text-white rounded-xl text-[10px] font-bold hover:bg-emerald-700 shadow-sm transition-all"
              >
                <Check size={12} /> Approve
              </button>
              <button
                onClick={() => sendApprovalResponse("reject", pendingApproval.tool_call_id)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 border border-red-500/20 bg-red-500/5 hover:bg-red-500/10 text-red-500 rounded-xl text-[10px] font-bold transition-all"
              >
                <X size={12} /> Reject
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border/50 bg-background/50 p-2">
        <ChatComposer
          disabled={!agent?.id || !!pendingApproval}
          isLoading={loading || !!pendingApproval}
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
