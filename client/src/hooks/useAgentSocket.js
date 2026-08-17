import { useState, useEffect, useCallback } from 'react';
import { agentSocketClient } from '../lib/agentSocketClient';

export const useAgentSocket = (url) => {
  // Initialize singleton on first hook call
  useEffect(() => {
    agentSocketClient.init();
  }, []);

  const [isConnected, setIsConnected] = useState(agentSocketClient.isConnected);
  const [agentTextChunks, setAgentTextChunks] = useState(agentSocketClient.buffers.textChunks);
  const [agentStatus, setAgentStatus] = useState(agentSocketClient.buffers.status);
  const [agentSteps, setAgentSteps] = useState(agentSocketClient.buffers.steps);
  const [pendingApproval, setPendingApproval] = useState(agentSocketClient.buffers.pendingApproval);

  useEffect(() => {
    const subscriptionId = "hook_" + Math.random().toString(36).substring(7);

    // Subscribe to global singleton events
    agentSocketClient.subscribe(
      subscriptionId,
      (data) => {
        if (data.type === 'sync') {
          // Initial mount synchronization
          setAgentTextChunks(data.textChunks);
          setAgentStatus(data.status);
          setAgentSteps(data.steps);
          setPendingApproval(data.pendingApproval);
        } else if (data.type === 'text_chunk') {
          setAgentTextChunks(agentSocketClient.buffers.textChunks);
          setAgentStatus('');
        } else if (data.type === 'step') {
          setAgentSteps(agentSocketClient.buffers.steps);
        } else if (data.type === 'status') {
          setAgentStatus(agentSocketClient.buffers.status);
          setAgentSteps(agentSocketClient.buffers.steps);
        } else if (data.type === 'routing_decision') {
          setAgentSteps(agentSocketClient.buffers.steps);
        } else if (data.type === 'approval_required') {
          setPendingApproval(agentSocketClient.buffers.pendingApproval);
          setAgentStatus('');
        } else if (data.type === 'approval_cleared') {
          setPendingApproval(null);
        } else if (data.type === 'error' || data.type === 'stream_end') {
          setAgentStatus('idle');
          setAgentSteps(agentSocketClient.buffers.steps);
        }
      },
      (connected) => {
        setIsConnected(connected);
      }
    );

    return () => {
      // Unsubscribe from live updates, but do NOT close the WebSocket connection!
      // This keeps the stream running in the background.
      agentSocketClient.unsubscribe(subscriptionId);
    };
  }, []);

  const sendChatRequest = useCallback((payload) => {
    agentSocketClient.sendRequest(payload);
    // Instantly sync local states
    setAgentTextChunks('');
    setAgentStatus('');
    setAgentSteps([]);
    setPendingApproval(null);
  }, []);

  const clearTextChunks = useCallback(() => {
    agentSocketClient.clearBuffer();
    setAgentTextChunks('');
    setAgentStatus('');
    setAgentSteps([]);
    setPendingApproval(null);
  }, []);

  const clearAgentSteps = useCallback(() => {
    agentSocketClient.buffers.steps = [];
    setAgentSteps([]);
  }, []);

  const sendApprovalResponse = useCallback((decision, toolCallId) => {
    agentSocketClient.sendApproval(decision, toolCallId);
    setPendingApproval(null);
  }, []);

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

