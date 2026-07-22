import { useMemo, useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { PanelLeftClose, PanelLeftOpen, Database, Settings2, Activity } from "lucide-react";
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
  }, [visibleMessages, loading]);

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
    <div className="flex h-[calc(100vh-8rem)] overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
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
        <div className="absolute top-4 left-4 z-10">
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
          <div className="max-w-4xl mx-auto px-8 pb-10 space-y-8 w-full flex-1">
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

            <div ref={messagesEndRef} />
          </div>
        </div>

        <ChatComposer
          disabled={!selectedAgentId}
          isLoading={loading}
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
