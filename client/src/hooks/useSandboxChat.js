import { useState, useMemo, useEffect, useCallback } from "react";
import { useAgentSocket } from "./useAgentSocket";

export function useSandboxChat() {
  const [localMessages, setLocalMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);

  // Connection config
  const clientId = useMemo(() => {
    return "sandbox_" + Math.random().toString(36).substring(7);
  }, []);
  
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
  const baseWsUrl = apiBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
  const wsUrl = `${baseWsUrl}/ws/chat/${clientId}`;

  const { isConnected, agentTextChunks, agentStatus, sendChatRequest, clearTextChunks } = useAgentSocket(wsUrl);

  const messages = useMemo(() => {
    if (!isTyping) return localMessages;
    return [...localMessages, {
      id: "optimistic-assistant",
      role: "assistant",
      content: agentTextChunks || "",
      status: agentStatus
    }];
  }, [localMessages, isTyping, agentTextChunks, agentStatus]);

  // Listen for custom stream_end event from useAgentSocket
  useEffect(() => {
    const handleStreamEnd = (e) => {
       if (isTyping) {
          setIsTyping(false);
          const finalContent = e.detail?.content || '';
          if (finalContent) {
            setLocalMessages(prev => [
              ...prev,
              { id: Date.now().toString(), role: "assistant", content: finalContent, latency: 0 }
            ]);
          }
          clearTextChunks();
       }
    };
    window.addEventListener('agent_stream_end', handleStreamEnd);
    return () => window.removeEventListener('agent_stream_end', handleStreamEnd);
  }, [isTyping, clearTextChunks]);

  const sendMessage = useCallback(({ agentId, agentName, content, language }) => {
    const message = content.trim();
    if (!agentId || !message) return;

    setLocalMessages(prev => [
      ...prev,
      { id: Date.now().toString(), role: "user", content: message }
    ]);

    setIsTyping(true);
    
    // We must send history to the agent to maintain conversation context
    const history = localMessages.map(({ role, content }) => ({ role, content }));
    sendChatRequest({
        agent_id: agentId,
        agent_name: agentName,
        message,
        history,
        language
    });
  }, [localMessages, sendChatRequest]);

  const clearSandbox = useCallback(() => {
    setLocalMessages([]);
    clearTextChunks();
    setIsTyping(false);
  }, [clearTextChunks]);

  return {
    messages,
    loading: isTyping,
    sendMessage,
    clearSandbox
  };
}
