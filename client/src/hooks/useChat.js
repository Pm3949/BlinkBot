import { useState, useMemo, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useChatSessions, useChatMessages, useChatMutations } from "./useChatHistory";
import { useAgentSocket } from "./useAgentSocket";

export function useChat(agentId = null) {
  const queryClient = useQueryClient();
  const { data: dbSessions = [], isLoading: isLoadingSessions } = useChatSessions(agentId);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [generatingSessionIds, setGeneratingSessionIds] = useState({});
  const isTyping = !!generatingSessionIds[activeSessionId];
  const [optimisticSession, setOptimisticSession] = useState(null);

  const sessions = useMemo(() => {
    let list = [...dbSessions];
    if (optimisticSession) {
      const exists = dbSessions.some(s => s.id === optimisticSession.id);
      if (!exists) {
        list.push(optimisticSession);
      }
    }
    return list;
  }, [dbSessions, optimisticSession]);

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

  const { isConnected, agentTextChunks, agentStatus, agentSteps, sendChatRequest, clearTextChunks, clearAgentSteps, pendingApproval, sendApprovalResponse } = useAgentSocket(wsUrl, activeSessionId);

  // Initialize activeSessionId from first session if null
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  const activeSession = useMemo(() => 
    sessions.find(s => s.id === activeSessionId), 
  [sessions, activeSessionId]);

  const { 
    data: dbMessages = [],
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: isLoadingMessages
  } = useChatMessages(activeSessionId);
  const { createSession, renameSession: renameDb, togglePinSession: pinDb, deleteSession: delDb, addMessage } = useChatMutations();

  const [optimisticUserMessage, setOptimisticUserMessage] = useState(null);

  const messages = useMemo(() => {
    let list = [...dbMessages];
    if (optimisticUserMessage) {
      list.push(optimisticUserMessage);
    }
    if (isTyping) {
      list.push({
        id: "optimistic-assistant",
        role: "assistant",
        content: agentTextChunks || "",
        status: agentStatus,
        steps: agentSteps,
      });
    }
    return list;
  }, [dbMessages, optimisticUserMessage, isTyping, agentTextChunks, agentStatus, agentSteps]);

  // Listen for custom stream_end event from useAgentSocket
  useEffect(() => {
    const handleStreamEnd = async (e) => {
       const targetSessionId = e.detail?.session_id;
       if (!targetSessionId || targetSessionId.startsWith("sandbox_")) {
          return;
       }
       
       if (targetSessionId) {
          setGeneratingSessionIds(prev => {
             const next = { ...prev };
             delete next[targetSessionId];
             return next;
          });
          if (targetSessionId === activeSessionId) {
             clearTextChunks();
          }
          
          const finalContent = e.detail?.content || '';
          const finalSteps = e.detail?.steps || null;

          // Directly update the local chat messages cache for the targeted session (supporting Infinite Query structure)
          queryClient.setQueryData(["chat_messages", targetSessionId], (old) => {
            const newMsg = {
              id: "assistant-cache-" + Date.now(),
              role: "assistant",
              content: finalContent,
              steps: finalSteps,
              created_at: new Date().toISOString()
            };

            if (!old || !old.pages) {
              return {
                pages: [[newMsg]],
                pageParams: [undefined]
              };
            }

            const updatedPages = [...old.pages];
            const firstPage = updatedPages[0] || [];
             
            updatedPages[0] = [...firstPage, newMsg];

            return {
              ...old,
              pages: updatedPages
            };
          });

       }
    };
    window.addEventListener('agent_stream_end', handleStreamEnd);
    return () => window.removeEventListener('agent_stream_end', handleStreamEnd);
  }, [activeSessionId, clearTextChunks, queryClient]);

  // Clear optimistic user message if the session changes
  useEffect(() => {
    setOptimisticUserMessage(null);
  }, [activeSessionId]);


  const startNewChat = ({ agentId, agentName } = {}) => {
    const tempId = "optimistic-session-" + Date.now();
    setOptimisticSession({
      id: tempId,
      agentId,
      agentName: agentName || "General",
      title: "New chat",
      updatedAt: new Date().toISOString()
    });
    setActiveSessionId(tempId);

    createSession.mutate(
      { agentId, title: "New chat" },
      {
        onSuccess: (newSession) => {
          setActiveSessionId(newSession.id);
          setOptimisticSession(null);
        },
        onError: () => {
          toast.error("Failed to start new chat");
          setOptimisticSession(null);
          setActiveSessionId(null);
        }
      }
    );
  };

  const sendMessage = async ({ agentId, agentName, content, language }) => {
    const message = content.trim();
    if (!agentId) {
      toast.error("Select an agent before starting chat.");
      return;
    }
    if (!message) return;

    // 1. Instantly update UI states (snappy, 0ms latency)
    clearTextChunks();
    clearAgentSteps();
    
    let currentSessionId = activeSessionId;
    const tempId = "optimistic-session-" + Date.now();
    setGeneratingSessionIds(prev => ({ ...prev, [currentSessionId || tempId]: true }));

    setOptimisticUserMessage({ id: "optimistic-user-" + Date.now(), role: "user", content: message });

    // 2. If no session exists or is an optimistic placeholder, create optimistic session and save to DB in background
    if (!currentSessionId || currentSessionId.startsWith("optimistic-session")) {
      setOptimisticSession({
        id: tempId,
        agentId,
        agentName: agentName || "General",
        title: message.slice(0, 40),
        updatedAt: new Date().toISOString()
      });
      setActiveSessionId(tempId);

      // Trigger DB session creation in the background
      createSession.mutate(
        { agentId, title: message.slice(0, 40) },
        {
          onSuccess: (newSession) => {
            setOptimisticSession(null);
            setActiveSessionId(newSession.id);
            setGeneratingSessionIds(prev => {
              const next = { ...prev };
              delete next[tempId];
              next[newSession.id] = true;
              return next;
            });
            
            // Save message and run WebSocket request on the newly created session
            addMessage.mutate(
              { sessionId: newSession.id, role: "user", content: message, agentId },
              {
                onSuccess: () => {
                  setOptimisticUserMessage(null);
                }
              }
            );

            sendChatRequest({
                agent_id: agentId,
                agent_name: agentName,
                message,
                history: [],
                language,
                session_id: newSession.id
            });
          },
          onError: () => {
            toast.error("Failed to create chat session");
            setGeneratingSessionIds(prev => {
              const next = { ...prev };
              delete next[tempId];
              return next;
            });
            setOptimisticUserMessage(null);
            setOptimisticSession(null);
            setActiveSessionId(null);
          }
        }
      );
      return;
    } else {
       if (dbMessages.length === 0 && activeSession?.title === "New chat") {
           renameDb.mutateAsync({ id: currentSessionId, title: message.slice(0, 40) });
       }
    }

    // 3. Save message to database in the background (fire-and-forget)
    addMessage.mutate(
      { sessionId: currentSessionId, role: "user", content: message, agentId },
      {
        onSuccess: () => {
          setOptimisticUserMessage(null);
        }
      }
    );
    
    // 4. Send WebSocket request
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
    // 1. Optimistically switch active session if deleting the current one
    if (activeSessionId === id) {
      const remaining = sessions.filter(s => s.id !== id);
      if (remaining.length > 0) {
        setActiveSessionId(remaining[0].id);
      } else {
        setActiveSessionId(null);
      }
    }

    // 2. Run backend deletion in the background
    try {
      await delDb.mutateAsync(id);
    } catch (e) {
      toast.error("Failed to delete chat session");
    }
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
    isLoadingSessions,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoadingMessages,
  };
}
