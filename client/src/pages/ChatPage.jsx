import { useMemo, useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { PanelLeftClose, PanelLeftOpen, Database, Settings2, Activity, ShieldAlert, Check, X, ArrowLeft, Sun, Moon } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import ChatSidebar from "../components/chat/ChatSidebar";
import TracePanel from "../components/chat/TracePanel";
import ChatComposer from "../components/chat/ChatComposer";
import MessageBubble from "../components/chat/MessageBubble";
import { usePrimaryWorkspace, useUserWorkspaces } from "../hooks/useSettings";
import { useAuth } from "../context/AuthContext";
import { useAgents, useAgentProjects } from "../hooks/useAgents";
import { useChat } from "../hooks/useChat";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import { useUIStore } from "../store/useUIStore";
import PageLoader from "../components/ui/PageLoader";


export default function ChatPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const setActiveWorkspaceId = useUIStore((state) => state.setActiveWorkspaceId);
  const darkMode = useUIStore((state) => state.darkMode);
  const toggleDarkMode = useUIStore((state) => state.toggleDarkMode);
  const { data: workspaces = [] } = useUserWorkspaces();
  const [hasLoadedInitially, setHasLoadedInitially] = useState(false);

  useEffect(() => {
    if (workspaces.length > 0) {
      const exists = workspaces.some((w) => w.id === activeWorkspaceId);
      if (!activeWorkspaceId || !exists) {
        setActiveWorkspaceId(workspaces[0].id);
      }
    }
  }, [workspaces, activeWorkspaceId, setActiveWorkspaceId]);

  useEffect(() => {
    const style = document.createElement("style");
    style.id = "hide-widget-style";
    style.innerHTML = `
      #blinkbot-bubble, #blinkbot-window, #blinkbot-popup {
        display: none !important;
      }
    `;
    document.head.appendChild(style);

    return () => {
      const styleEl = document.getElementById("hide-widget-style");
      if (styleEl) styleEl.remove();
    };
  }, []);

  const { data: workspace } = usePrimaryWorkspace();
  const hasAgentsPermission = workspace?.memberPermissions?.agents === true;
  const { data: projects = [], isLoading: isLoadingProjects } = useAgentProjects(activeWorkspaceId);
  const [activeAgentId, setActiveAgentId] = useState(() => {
    return localStorage.getItem("ragmate_active_agent_id") || "";
  });
  const [activeSubAgentDetails, setActiveSubAgentDetails] = useState(null);
  const [chatLanguage, setChatLanguage] = useState("en");
  const [agentToEdit, setAgentToEdit] = useState(null);
  
  // UI Toggles
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isTraceOpen, setIsTraceOpen] = useState(false);
  
  const messagesEndRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const lastMessageIdRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const lastScrollTopRef = useRef(0);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    
    const { scrollTop } = scrollContainerRef.current;
    
    // Detect if the user is scrolling up (scrollTop is decreasing)
    const isScrollingUp = scrollTop < lastScrollTopRef.current;
    lastScrollTopRef.current = scrollTop;
    
    // If scrolled to the top, scrolling up, and older messages exist, fetch them
    if (scrollTop < 5 && isScrollingUp && hasNextPage && !isFetchingNextPage) {
      const previousScrollHeight = scrollContainerRef.current.scrollHeight;
      
      fetchNextPage().then(() => {
        if (scrollContainerRef.current) {
          const newScrollHeight = scrollContainerRef.current.scrollHeight;
          scrollContainerRef.current.scrollTop = newScrollHeight - previousScrollHeight;
          lastScrollTopRef.current = scrollContainerRef.current.scrollTop;
        }
      });
    }
  };

  // Auto-select project on load with localStorage persistence
  useEffect(() => {
    if (projects.length > 0) {
      const savedId = localStorage.getItem("ragmate_active_agent_id");
      const isValid = projects.some(p => p.id === savedId);
      if (isValid) {
        setActiveAgentId(savedId);
        const match = projects.find(p => p.id === savedId);
        if (match) setActiveSubAgentDetails(match);
      } else {
        setActiveAgentId(projects[0].id);
        localStorage.setItem("ragmate_active_agent_id", projects[0].id);
        if (projects[0]) setActiveSubAgentDetails(projects[0]);
      }
    }
  }, [projects]);

  const selectedAgentId = activeAgentId;

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
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoadingSessions,
    isLoadingMessages,
  } = useChat(selectedAgentId);

  useEffect(() => {
    if (!isLoadingProjects && !isLoadingSessions) {
      setHasLoadedInitially(true);
    }
  }, [isLoadingProjects, isLoadingSessions]);

  // activeAgent resolves to the currently selected network project
  const activeAgent = useMemo(
    () => projects.find((project) => project.id === selectedAgentId) || 
          { id: selectedAgentId, name: activeSession?.agentName || "Network Manager" },
    [selectedAgentId, projects, activeSession],
  );

  useEffect(() => {
    if (activeAgent?.language) {
      setChatLanguage(activeAgent.language);
    }
  }, [activeAgent]);

  const selectedAgentSessions = sessions;

  const isActiveSessionForSelectedAgent = true;
  const visibleMessages = messages;

  const wasFetchingNextPageRef = useRef(false);

  // Track if we are currently loading older pages
  useEffect(() => {
    if (isFetchingNextPage) {
      wasFetchingNextPageRef.current = true;
    }
  }, [isFetchingNextPage]);

  // Only scroll to bottom if a new message was sent/received at the end of the chat
  useEffect(() => {
    if (visibleMessages.length === 0) return;

    if (wasFetchingNextPageRef.current) {
      wasFetchingNextPageRef.current = false;
      const lastMsg = visibleMessages[visibleMessages.length - 1];
      if (lastMsg) lastMessageIdRef.current = lastMsg.id;
      return;
    }

    const lastMsg = visibleMessages[visibleMessages.length - 1];
    
    if (lastMsg && (lastMsg.id !== lastMessageIdRef.current || loading || pendingApproval)) {
      lastMessageIdRef.current = lastMsg.id;
      scrollToBottom();
    }
  }, [visibleMessages, loading, pendingApproval]);

  const handleAgentSelect = (agent) => {
    setActiveAgentId(agent.id);
    localStorage.setItem("ragmate_active_agent_id", agent.id);
    setActiveSubAgentDetails(agent);
    selectSession(null);
  };

  // Auto-select the latest session when the sessions list loads for a selected agent
  useEffect(() => {
    if (sessions.length > 0 && !activeSessionId) {
      const latest = [...sessions].sort(
        (first, second) =>
          Number(Boolean(second.pinned)) - Number(Boolean(first.pinned)) ||
          new Date(second.updatedAt).getTime() - new Date(first.updatedAt).getTime(),
      )[0];
      if (latest) {
        selectSession(latest.id);
      }
    }
  }, [sessions, activeSessionId, selectSession]);

  const handleNewChat = () => {
    startNewChat({
      agentId: selectedAgentId || null,
      agentName: activeAgent?.name || "General",
    });
  };

  const handleSessionSelect = (session) => {
    selectSession(session.id);
    
    const targetId = session.projectId || session.agentId;
    if (targetId) {
      setActiveAgentId(targetId);
      localStorage.setItem("ragmate_active_agent_id", targetId);
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

  if (!hasLoadedInitially && (isLoadingProjects || isLoadingSessions)) {
    return <PageLoader text="Loading Chat..." />;
  }

  return (
    <div className="flex h-dvh w-screen overflow-hidden bg-background">
      {isSidebarOpen && (
        <ChatSidebar
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
          isLoadingAgents={isLoadingProjects}
          isLoadingSessions={isLoadingSessions}
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
           <button 
             onClick={toggleDarkMode} 
             className="p-2 bg-card/80 backdrop-blur border border-border shadow-sm rounded-xl hover:bg-muted text-muted-foreground transition-all"
             title="Toggle Theme"
           >
             {darkMode ? <Sun size={18} className="text-amber-500 animate-spin-slow" /> : <Moon size={18} className="text-indigo-400" />}
           </button>
        </div>

        {/* Centered Network Header Title */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 flex flex-col items-center pointer-events-none select-none bg-card/60 backdrop-blur-md border border-border px-5 py-2 rounded-full shadow-sm">
           <div className="flex items-center gap-2">
             <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
             <span className="text-xs font-bold text-foreground">
               {activeAgent?.name || "General Network"}
             </span>
           </div>
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

        <div ref={scrollContainerRef} onScroll={handleScroll} className="flex-1 overflow-y-auto pt-16 flex flex-col">
          <div className="max-w-6xl mx-auto px-8 pb-10 space-y-8 w-full flex-1">
            {isLoadingProjects && <LoadingSkeleton count={2} className="h-24" />}

            {isLoadingMessages ? (
              <div className="space-y-4">
                <LoadingSkeleton count={3} className="h-24" />
              </div>
            ) : (
              <>
                {!isLoadingProjects && projects.length === 0 && (
                  <div className="text-sm text-muted-foreground">
                    Create a network before starting a chat.
                  </div>
                )}

                {!isLoadingProjects &&
                  projects.length > 0 &&
                  visibleMessages.length === 0 && (
                    activeSessionId?.startsWith("optimistic-session") ? (
                      <div className="flex flex-col items-center justify-center flex-1 py-12">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
                        <p className="mt-4 text-sm text-muted-foreground animate-pulse">Creating new chat session...</p>
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-dashed border-border bg-card p-8 text-center mt-8">
                        <h3 className="font-semibold text-foreground">
                          {activeAgent ? activeAgent.name : "Start a chat"}
                        </h3>

                        <p className="mt-2 text-sm text-muted-foreground">
                          Select a chat from history or start a new chat with this network.
                        </p>
                      </div>
                    )
                  )
                }

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
              </>
            )}

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
