import { useState, useEffect, useCallback } from 'react';
import { agentSocketClient } from '../lib/agentSocketClient';

export const useAgentSocket = (url, activeSessionId = "general") => {
  // Initialize singleton on first hook call
  useEffect(() => {
    agentSocketClient.init();
  }, []);

  const [isConnected, setIsConnected] = useState(agentSocketClient.isConnected);
  
  // Scoped state hooks
  const getFreshBuffers = useCallback(() => {
    return agentSocketClient.getBuffers(activeSessionId);
  }, [activeSessionId]);

  const [agentTextChunks, setAgentTextChunks] = useState(() => getFreshBuffers().textChunks);
  const [agentStatus, setAgentStatus] = useState(() => getFreshBuffers().status);
  const [agentSteps, setAgentSteps] = useState(() => getFreshBuffers().steps);
  const [pendingApproval, setPendingApproval] = useState(() => getFreshBuffers().pendingApproval);

  // Sync state whenever activeSessionId changes
  useEffect(() => {
    const buffers = getFreshBuffers();
    setAgentTextChunks(buffers.textChunks);
    setAgentStatus(buffers.status);
    setAgentSteps(buffers.steps);
    setPendingApproval(buffers.pendingApproval);
  }, [activeSessionId, getFreshBuffers]);

  useEffect(() => {
    const subscriptionId = "hook_" + Math.random().toString(36).substring(7);

    // Subscribe to global singleton events
    agentSocketClient.subscribe(
      subscriptionId,
      (data) => {
        // If event belongs to a different session, discard it here
        const msgSessionId = data.session_id || "general";
        if (msgSessionId !== activeSessionId) {
          return;
        }

        const buffers = agentSocketClient.getBuffers(activeSessionId);

        if (data.type === 'sync') {
          // Initial mount synchronization
          setAgentTextChunks(buffers.textChunks);
          setAgentStatus(buffers.status);
          setAgentSteps(buffers.steps);
          setPendingApproval(buffers.pendingApproval);
        } else if (data.type === 'text_chunk') {
          setAgentTextChunks(buffers.textChunks);
          setAgentStatus('');
        } else if (data.type === 'step') {
          setAgentSteps(buffers.steps);
        } else if (data.type === 'status') {
          setAgentStatus(buffers.status);
          setAgentSteps(buffers.steps);
        } else if (data.type === 'routing_decision') {
          setAgentSteps(buffers.steps);
        } else if (data.type === 'approval_required') {
          setPendingApproval(buffers.pendingApproval);
          setAgentStatus('');
        } else if (data.type === 'approval_cleared') {
          setPendingApproval(null);
        } else if (data.type === 'error' || data.type === 'stream_end') {
          setAgentStatus('idle');
          setAgentSteps(buffers.steps);
        }
      },
      (connected) => {
        setIsConnected(connected);
      }
    );

    return () => {
      // Unsubscribe from live updates, but do NOT close the WebSocket connection!
      agentSocketClient.unsubscribe(subscriptionId);
    };
  }, [activeSessionId]);

  const sendChatRequest = useCallback((payload) => {
    const sId = payload?.session_id || activeSessionId;
    agentSocketClient.sendRequest(payload);
    // Instantly sync local states
    setAgentTextChunks('');
    setAgentStatus('');
    setAgentSteps([]);
    setPendingApproval(null);
  }, [activeSessionId]);

  const clearTextChunks = useCallback(() => {
    agentSocketClient.clearBuffer(activeSessionId);
    setAgentTextChunks('');
    setAgentStatus('');
    setAgentSteps([]);
    setPendingApproval(null);
  }, [activeSessionId]);

  const clearAgentSteps = useCallback(() => {
    const buffers = agentSocketClient.getBuffers(activeSessionId);
    buffers.steps = [];
    setAgentSteps([]);
  }, [activeSessionId]);

  const sendApprovalResponse = useCallback((decision, toolCallId) => {
    agentSocketClient.sendApproval(decision, toolCallId, activeSessionId);
    setPendingApproval(null);
  }, [activeSessionId]);

  return {
    isConnected,
    agentTextChunks,
    agentStatus,
    agentSteps,
    sendChatRequest,
    clearTextChunks,
    clearAgentSteps,
    pendingApproval,
    sendApprovalResponse
  };
};

