import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import { useChatSessions, useChatMessages, useChatMutations } from "./useChatHistory";
import { useAgentSocket } from "./useAgentSocket";

export function useChat() {
  const { data: sessions = [] } = useChatSessions();
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isTyping, setIsTyping] = useState(false);

  // Connection config
  const clientId = useMemo(() => {
    let cid = localStorage.getItem("dashboard_client_id");
    if (!cid) {
        cid = Math.random().toString(36).substring(7);
        localStorage.setItem("dashboard_client_id", cid);
    }
    return cid;
  }, []);
  
  const wsUrl = useMemo(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const baseWsUrl = apiBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
    return `${baseWsUrl}/ws/chat/${clientId}`;
  }, [clientId]);

  const { isConnected, agentTextChunks, agentStatus, agentSteps, sendChatRequest, clearTextChunks, pendingApproval, sendApprovalResponse } = useAgentSocket(wsUrl);

  // Initialize activeSessionId from first session if null
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  const activeSession = useMemo(() => 
    sessions.find(s => s.id === activeSessionId), 
  [sessions, activeSessionId]);

  const { data: dbMessages = [] } = useChatMessages(activeSessionId);
  const { createSession, renameSession: renameDb, togglePinSession: pinDb, deleteSession: delDb, addMessage } = useChatMutations();

  const messages = useMemo(() => {
    if (!isTyping) return dbMessages;
    return [...dbMessages, {
      id: "optimistic-assistant",
      role: "assistant",
      content: agentTextChunks || "",
      status: agentStatus,
      steps: agentSteps,
    }];
  }, [dbMessages, isTyping, agentTextChunks, agentStatus, agentSteps]);

  // Listen for custom stream_end event from useAgentSocket
  useEffect(() => {
    const handleStreamEnd = async (e) => {
       setIsTyping(false);
       if (activeSessionId) {
          const finalContent = e.detail?.content || '';
          const finalSteps = e.detail?.steps || null;
          if (finalContent) {
            try {
              await addMessage.mutateAsync({ sessionId: activeSessionId, role: "assistant", content: finalContent, latency: 0, steps: finalSteps });
            } catch (err) {
              console.error("Database save failed for assistant message:", err);
            }
          }
          clearTextChunks();
       }
    };
    window.addEventListener('agent_stream_end', handleStreamEnd);
    return () => window.removeEventListener('agent_stream_end', handleStreamEnd);
  }, [activeSessionId, addMessage, clearTextChunks]);


  const startNewChat = async ({ agentId, agentName } = {}) => {
    try {
      const newSession = await createSession.mutateAsync({ agentId, title: "New chat" });
      setActiveSessionId(newSession.id);
    } catch (e) {
      toast.error("Failed to start new chat");
    }
  };

  const sendMessage = async ({ agentId, agentName, content, language }) => {
    const message = content.trim();
    if (!agentId) {
      toast.error("Select an agent before starting chat.");
      return;
    }
    if (!message) return;

    let currentSessionId = activeSessionId;
    const belongsToAgent = sessions.find(s => s.id === currentSessionId)?.agentId === agentId;
    
    if (!currentSessionId || !belongsToAgent) {
      const newSession = await createSession.mutateAsync({ agentId, title: message.slice(0, 40) });
      currentSessionId = newSession.id;
      setActiveSessionId(currentSessionId);
    } else {
       if (dbMessages.length === 0 && activeSession?.title === "New chat") {
           renameDb.mutateAsync({ id: currentSessionId, title: message.slice(0, 40) });
       }
    }

    setIsTyping(true);

    await addMessage.mutateAsync({ sessionId: currentSessionId, role: "user", content: message });
    
    const history = dbMessages.map(({ role, content }) => ({ role, content }));
    sendChatRequest({
        agent_id: agentId,
        agent_name: agentName,
        message,
        history,
        language,
        session_id: currentSessionId
    });
  };

  const selectSession = (id) => setActiveSessionId(id);
  const renameSession = (id, title) => {
    if (title.trim()) renameDb.mutateAsync({ id, title: title.trim() });
  };
  const togglePinSession = (id) => {
    const session = sessions.find(s => s.id === id);
    if (session) pinDb.mutateAsync({ id, pinned: !session.pinned });
  };
  const deleteSession = async (id) => {
    await delDb.mutateAsync(id);
    if (activeSessionId === id) setActiveSessionId(null);
  };

  return {
    activeSessionId,
    activeSession,
    sessions,
    messages,
    loading: isTyping,
    sendMessage,
    startNewChat,
    selectSession,
    renameSession,
    togglePinSession,
    deleteSession,
    pendingApproval,
    sendApprovalResponse,
  };
}
