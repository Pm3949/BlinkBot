import { useState, useMemo, useEffect } from "react";
import { toast } from "sonner";
import { streamChat } from "../services/chatService";
import { useChatSessions, useChatMessages, useChatMutations } from "./useChatHistory";

export function useChat() {
  const { data: sessions = [] } = useChatSessions();
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");

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
      content: streamingContent || "Thinking..."
    }];
  }, [dbMessages, isTyping, streamingContent]);

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
    
    // Check if the current session belongs to the selected agent
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

    // Save User Message to DB
    await addMessage.mutateAsync({ sessionId: currentSessionId, role: "user", content: message });

    // Stream
    setIsTyping(true);
    setStreamingContent("");

    let finalContent = "";
    const startTime = Date.now();
    try {
      const history = dbMessages.map(({ role, content }) => ({ role, content }));
      
      await streamChat(
        {
          agent_id: agentId,
          message,
          history,
          language,
        },
        (streamedText) => {
          setStreamingContent(streamedText);
          finalContent = streamedText;
        },
      );
      
      // Save Assistant Message to DB
      if (finalContent) {
        const latency = Date.now() - startTime;
        await addMessage.mutateAsync({ sessionId: currentSessionId, role: "assistant", content: finalContent, latency });
      }
    } catch (error) {
      toast.error(error.message || "Unable to get a response.");
      // Optional: Save an error message so the user knows it failed
    } finally {
      setIsTyping(false);
      setStreamingContent("");
    }
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
