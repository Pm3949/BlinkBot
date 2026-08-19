import { useState, useMemo, useEffect, useCallback } from "react";
import { useAgentSocket } from "./useAgentSocket";

export function useSandboxChat() {
  const [localMessages, setLocalMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [sandboxSessionId, setSandboxSessionId] = useState(() => "sandbox_" + Math.random().toString(36).substring(7));

  // Connection config
  const clientId = useMemo(() => {
    return "sandbox_" + Math.random().toString(36).substring(7);
  }, []);
  
  const wsUrl = useMemo(() => {
    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const baseWsUrl = apiBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
    return `${baseWsUrl}/ws/chat/${clientId}`;
  }, [clientId]);

  const { isConnected, agentTextChunks, agentStatus, agentSteps, sendChatRequest, clearTextChunks, pendingApproval, sendApprovalResponse } = useAgentSocket(wsUrl, sandboxSessionId);

  const messages = useMemo(() => {
    if (!isTyping) return localMessages;
    return [...localMessages, {
      id: "optimistic-assistant",
      role: "assistant",
      content: agentTextChunks || "",
      status: agentStatus,
      steps: agentSteps
    }];
  }, [localMessages, isTyping, agentTextChunks, agentStatus, agentSteps]);

  // Listen for custom stream_end event from useAgentSocket
  useEffect(() => {
    const handleStreamEnd = (e) => {
       const targetSessionId = e.detail?.session_id;
       // Only process end event if it belongs to this specific sandbox session
       if (targetSessionId !== sandboxSessionId) {
         return;
       }
       setIsTyping(false);
       const finalContent = e.detail?.content || '';
       const finalSteps = e.detail?.steps || null;
       if (finalContent) {
         setLocalMessages(prev => [
           ...prev,
           { id: Date.now().toString(), role: "assistant", content: finalContent, latency: 0, steps: finalSteps }
         ]);
       }
       clearTextChunks();
    };
    window.addEventListener('agent_stream_end', handleStreamEnd);
    return () => window.removeEventListener('agent_stream_end', handleStreamEnd);
  }, [clearTextChunks, sandboxSessionId]);

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
        language,
        session_id: sandboxSessionId
    });
  }, [localMessages, sendChatRequest, sandboxSessionId]);

  const clearSandbox = useCallback(() => {
    setLocalMessages([]);
    clearTextChunks();
    setIsTyping(false);
    setSandboxSessionId("sandbox_" + Math.random().toString(36).substring(7));
  }, [clearTextChunks]);

  return {
    messages,
    loading: isTyping,
    sendMessage,
    clearSandbox,
    pendingApproval,
    sendApprovalResponse
  };
}
