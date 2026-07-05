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
  
  // Derive WS base URL from VITE_API_BASE_URL (same strategy as NotificationBell)
  // This ensures the chat WebSocket connects to the backend, not the frontend host.
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const baseWsUrl = apiBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');

  const wsUrl = `${baseWsUrl}/ws/chat/${clientId}`;

  const { isConnected, agentTextChunks, sendChatRequest, clearTextChunks } = useAgentSocket(wsUrl);

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
      content: agentTextChunks || "Thinking..."
    }];
  }, [dbMessages, isTyping, agentTextChunks]);

  // Listen for custom stream_end event from useAgentSocket
  useEffect(() => {
    const handleStreamEnd = async (e) => {
       if (isTyping && activeSessionId) {
          setIsTyping(false);
          // Use e.detail.content (accumulated via ref in useAgentSocket) — NOT agentTextChunks state
          // which may be stale due to React's async batching when the event fires
          const finalContent = e.detail?.content || '';
          if (finalContent) {
            await addMessage.mutateAsync({ sessionId: activeSessionId, role: "assistant", content: finalContent, latency: 0 });
          }
          clearTextChunks();
       }
    };
    window.addEventListener('agent_stream_end', handleStreamEnd);
    return () => window.removeEventListener('agent_stream_end', handleStreamEnd);
  }, [isTyping, activeSessionId, addMessage, clearTextChunks]);


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

    await addMessage.mutateAsync({ sessionId: currentSessionId, role: "user", content: message });

    setIsTyping(true);
    
    const history = dbMessages.map(({ role, content }) => ({ role, content }));
    sendChatRequest({
        agent_id: agentId,
        message,
        history,
        language
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
  };
}
