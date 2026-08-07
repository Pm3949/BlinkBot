import { useMemo, useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { PanelLeftClose, PanelLeftOpen, Database, Settings2, Activity, ShieldAlert, Check, X, ArrowLeft } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import ChatSidebar from "../components/chat/ChatSidebar";
import TracePanel from "../components/chat/TracePanel";
import ChatComposer from "../components/chat/ChatComposer";
import MessageBubble from "../components/chat/MessageBubble";
import { usePrimaryWorkspace } from "../hooks/useSettings";
import { useAuth } from "../context/AuthContext";
import { useAgents, useAgentProjects } from "../hooks/useAgents";
import { useChat } from "../hooks/useChat";
import VerificationBanner from "../components/chat/VerificationBanner";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useUIStore } from "../store/useUIStore";


export default function ChatPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { data: workspace } = usePrimaryWorkspace();
  const hasAgentsPermission = workspace?.memberPermissions?.agents === true;
  const { data: standaloneAgents = [], isLoading: isLoadingAgents } = useAgents(activeWorkspaceId);
  const { data: projects = [], isLoading: isLoadingProjects } = useAgentProjects(activeWorkspaceId);
  const [activeAgentId, setActiveAgentId] = useState("");
  const [activeSubAgentDetails, setActiveSubAgentDetails] = useState(null);
  const [chatLanguage, setChatLanguage] = useState("en");
  const [agentToEdit, setAgentToEdit] = useState(null);
  
  // UI Toggles
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isTraceOpen, setIsTraceOpen] = useState(false);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const {
    activeSessionId,
    activeSession,
    sessions,
    messages,
    loading,
    sendMessage,
    startNewChat,
    selectSession,
    renameSession,
    togglePinSession,
    deleteSession,
    pendingApproval,
    sendApprovalResponse,
  } = useChat();


  const selectedAgentId =
    activeAgentId || activeSession?.agentId || standaloneAgents[0]?.id || "";

  // Since we only have standaloneAgents and activeAgentId could be a sub-agent, 
  // activeAgent needs to fetch from the server if not in standaloneAgents.
  // Actually, we should fetch the specific agent details if it's not standalone,
  // but for chat purposes we just need name/language. Let's pass a placeholder if not found locally.
  const activeAgent = useMemo(
    () => standaloneAgents.find((agent) => agent.id === selectedAgentId) || 
          (activeSubAgentDetails?.id === selectedAgentId ? activeSubAgentDetails : null) || 
          { id: selectedAgentId, name: activeSession?.agentName || "Sub-Agent" },
    [selectedAgentId, standaloneAgents, activeSession, activeSubAgentDetails],
  );

  useEffect(() => {
    if (activeAgent?.language) {
      setChatLanguage(activeAgent.language);
    }
  }, [activeAgent]);

  const selectedAgentSessions = useMemo(
    () =>
      sessions.filter(
        (session) =>
          String(session.agentId || "general") === String(selectedAgentId),
      ),
    [sessions, selectedAgentId],
  );

  const isActiveSessionForSelectedAgent =
    String(activeSession?.agentId || "general") === String(selectedAgentId);
  const visibleMessages = isActiveSessionForSelectedAgent ? messages : [];

  useEffect(() => {
    scrollToBottom();
  }, [visibleMessages, loading, pendingApproval]);

  const handleAgentSelect = (agent) => {
    setActiveAgentId(agent.id);
    setActiveSubAgentDetails(agent);
    
    const latestAgentSession = sessions
      .filter(
        (session) => String(session.agentId || "general") === String(agent.id),
      )
      .sort(
        (first, second) =>
          Number(Boolean(second.pinned)) - Number(Boolean(first.pinned)) ||
          new Date(second.updatedAt).getTime() -
            new Date(first.updatedAt).getTime(),
      )[0];

    selectSession(latestAgentSession?.id || null);
  };

  const handleNewChat = () => {
    startNewChat({
      agentId: selectedAgentId || null,
      agentName: activeAgent?.name || "General",
    });
  };

  const handleSessionSelect = (session) => {
    selectSession(session.id);

    if (session.agentId) {
      setActiveAgentId(session.agentId);
    }
  };

  const handleSend = (content) => {
    sendMessage({
      agentId: selectedAgentId,
      agentName: activeAgent?.name || "General",
      content,
      language: chatLanguage,
    });
  };



  return (
    <div className="flex h-dvh w-screen overflow-hidden bg-background">
      {isSidebarOpen && (
        <ChatSidebar
          standaloneAgents={standaloneAgents}
          projects={projects}
          activeAgentId={selectedAgentId}
          activeSessionId={isActiveSessionForSelectedAgent ? activeSessionId : null}
          sessions={selectedAgentSessions}
          onAgentSelect={handleAgentSelect}
          onNewChat={handleNewChat}
          onSessionSelect={handleSessionSelect}
          onRenameSession={renameSession}
          onTogglePinSession={togglePinSession}
          onDeleteSession={deleteSession}
        />
      )}

      <div className="flex-1 flex flex-col relative min-w-0">
        <div className="absolute top-4 left-4 z-10 flex items-center gap-2">
           <Link 
             to="/dashboard"
             className="p-2 bg-card/80 backdrop-blur border border-border shadow-sm rounded-xl hover:bg-muted text-muted-foreground hover:text-foreground transition-all"
             title="Back to Dashboard"
           >
             <ArrowLeft size={18} />
           </Link>
           <button 
             onClick={() => setIsSidebarOpen(!isSidebarOpen)} 
             className="p-2 bg-card/80 backdrop-blur border border-border shadow-sm rounded-xl hover:bg-muted text-muted-foreground transition-all"
             title="Toggle Chat History"
           >
             {isSidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
           </button>
        </div>



        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex items-center gap-2 px-4 py-2 bg-card/80 backdrop-blur border border-border shadow-sm rounded-2xl">
          <span className="font-medium text-sm text-foreground">{activeAgent?.name || "Select an Agent"}</span>
          {activeAgent && activeAgent.id && (
            <div className="flex items-center gap-1">
              <button 
                onClick={() => navigate(`/agent/${activeAgent.id}/settings`, { state: { agent: activeAgent } })}
                className="p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg transition"
                title="Agent Settings"
              >
                <Settings2 size={16} />
              </button>
            </div>
          )}
        </div>

        <div className="absolute top-4 right-4 z-10">
          {activeAgent && activeAgent.id && (
            <button 
              onClick={() => setIsTraceOpen(!isTraceOpen)}
              className={`flex items-center gap-1.5 px-3 py-2 bg-card/80 backdrop-blur border border-border shadow-sm rounded-xl hover:bg-muted font-semibold text-xs transition-all ${isTraceOpen ? 'text-purple-400 bg-purple-500/10 border-purple-500/30' : 'text-muted-foreground hover:text-foreground'}`}
              title="Toggle Execution Trace"
            >
              <Activity size={20}/> <span>Execution Trace</span>
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto pt-16 flex flex-col">
          <VerificationBanner onRetry={handleSend} />
          <div className="max-w-6xl mx-auto px-8 pb-10 space-y-8 w-full flex-1">
            {isLoadingAgents && <LoadingSkeleton count={2} className="h-24" />}

            {!isLoadingAgents && standaloneAgents.length === 0 && projects.length === 0 && (
              <div className="text-sm text-muted-foreground">
                Create an agent or network before starting a chat.
              </div>
            )}

            {!isLoadingAgents &&
              (standaloneAgents.length > 0 || projects.length > 0) &&
              visibleMessages.length === 0 && (
              <div className="rounded-2xl border border-dashed border-border bg-card p-8 text-center mt-8">
                <h3 className="font-semibold text-foreground">
                  {activeAgent ? activeAgent.name : "Start a chat"}
                </h3>

                <p className="mt-2 text-sm text-muted-foreground">
                  Select a chat from history or start a new chat with this agent.
                </p>
              </div>
            )}

            {visibleMessages.map((message) => (
              <MessageBubble
                key={message.id}
                id={message.id}
                role={message.role}
                agent={activeAgent}
                chatLanguage={chatLanguage}
                latency={message.latency}
                content={message.content}
                sources={message.sources}
                steps={message.steps}
                status={message.status || (message.role === "assistant" && !message.content ? "Thinking..." : null)}
              />
            ))}

                        {/* {loading && (
              <div className="flex items-center gap-3 px-6 py-4 bg-card/50 border border-border w-fit rounded-2xl shadow-sm">
                <div className="flex gap-1.5">
                  <div className="h-2 w-2 rounded-full bg-primary/70 animate-bounce" />
                  <div className="h-2 w-2 rounded-full bg-primary/70 animate-bounce [animation-delay:150ms]" />
                  <div className="h-2 w-2 rounded-full bg-primary/70 animate-bounce [animation-delay:300ms]" />
                </div>
                <span className="text-sm font-medium text-muted-foreground animate-pulse">Thinking...</span>
              </div>
            )} */}

            {pendingApproval && (
              <div className="p-5 border border-amber-500/20 bg-amber-500/5 rounded-2xl shadow-sm space-y-4 max-w-2xl animate-in fade-in slide-in-from-bottom-2 duration-300">
                <div className="flex items-center gap-2 text-amber-500 font-semibold">
                  <ShieldAlert size={20} />
                  <span>Action Approval Required</span>
                </div>
                <div className="text-sm text-muted-foreground space-y-2">
                  <p>
                    The agent wants to run <span className="font-semibold text-foreground font-mono bg-muted px-1.5 py-0.5 rounded border border-border">{pendingApproval.tool_name}</span> with the following parameters:
                  </p>
                  <pre className="p-3 bg-muted border border-border rounded-xl text-xs overflow-x-auto font-mono text-foreground">
                    {JSON.stringify(pendingApproval.arguments, null, 2)}
                  </pre>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => sendApprovalResponse("approve", pendingApproval.tool_call_id)}
                    className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold hover:bg-emerald-700 shadow-md transition-all"
                  >
                    <Check size={14} /> Approve Action
                  </button>
                  <button
                    onClick={() => sendApprovalResponse("reject", pendingApproval.tool_call_id)}
                    className="flex items-center gap-1.5 px-4 py-2 border border-red-500/20 bg-red-500/5 hover:bg-red-500/10 text-red-500 rounded-xl text-xs font-bold transition-all"
                  >
                    <X size={14} /> Reject Action
                  </button>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <ChatComposer
          disabled={!selectedAgentId || !!pendingApproval}
          isLoading={loading || !!pendingApproval}
          onSend={handleSend}
          agent={activeAgent}
          chatLanguage={chatLanguage}
          setChatLanguage={setChatLanguage}
        />
      </div>

      {isTraceOpen && (
        <TracePanel onClose={() => setIsTraceOpen(false)} />
      )}
    </div>
  );
}
