import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { useTraceStore } from '../store/useTraceStore';

export const useAgentSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [agentTextChunks, setAgentTextChunks] = useState('');
  const [agentStatus, setAgentStatus] = useState('');
  const [agentSteps, _setAgentSteps] = useState([]);
  const agentStepsRef = useRef([]);

  const setAgentSteps = useCallback((val) => {
    let next;
    if (typeof val === 'function') {
      next = val(agentStepsRef.current);
    } else {
      next = val;
    }
    agentStepsRef.current = next;
    _setAgentSteps(next);
  }, []);

  const [pendingApproval, setPendingApproval] = useState(null);
  // Queue for messages that arrive before the socket is OPEN
  const pendingPayloadRef = useRef(null);
  // Ref to track accumulated text outside React state (avoids stale closure in stream_end)
  const textAccRef = useRef('');
  // Ref to track active agent name during multi-agent routing cycles
  const activeAgentNameRef = useRef('Execution Agent');

  const connect = useCallback(() => {
    // Prevent duplicate connections if already open or connecting
    if (
      socketRef.current?.readyState === WebSocket.OPEN ||
      socketRef.current?.readyState === WebSocket.CONNECTING
    ) return;

    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to Agent WebSocket');
      setIsConnected(true);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      // Flush any message that was queued while the socket was connecting
      if (pendingPayloadRef.current) {
        const queued = pendingPayloadRef.current;
        pendingPayloadRef.current = null;
        setAgentTextChunks('');
        ws.send(JSON.stringify({ type: 'chat_request', payload: queued }));
      }
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === 'string') {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'text_chunk') {
            textAccRef.current += data.content;
            setAgentTextChunks((prev) => prev + data.content);
            setAgentStatus('');
          } else if (data.type === 'step') {
            if (data.status.startsWith('tool_call_')) {
              const toolName = data.status.replace('tool_call_', '');
              window.dispatchEvent(new CustomEvent('agent_tool_start', { detail: { tool_name: toolName } }));
            } else if (data.status.startsWith('tool_done_')) {
              const toolName = data.status.replace('tool_done_', '');
              window.dispatchEvent(new CustomEvent('agent_tool_end', { detail: { tool_name: toolName } }));
            }
            
            // Add step to Trace Store so it is visible in the Execution Trace panel
            useTraceStore.getState().addStep({
              type: data.status.includes('tool_') ? 'tool' : 'routing',
              agentName: activeAgentNameRef.current,
              action: data.label || 'Executing Step',
              logs: data.label || data.status,
              payload: data
            });

            // Upsert: update label if same status already exists, otherwise append
            setAgentSteps(prev => {
              // Mark all previous steps as done since a new one is executing
              const markedPrev = prev.map(s => ({ ...s, done: true }));
              // Match by both status and label to distinguish multiple steps of same type
              const exists = markedPrev.find(s => s.status === data.status && s.label === data.label);
              if (exists) {
                return markedPrev.map(s => (s.status === data.status && s.label === data.label)
                  ? { ...s, done: false } // only the current active step remains loading
                  : s
                );
              }
              return [...markedPrev, { status: data.status, label: data.label, done: false }];
            });
          } else if (data.type === 'status') {
            setAgentStatus(data.content);
            if (data.content) {
              useTraceStore.getState().addStep({
                type: 'tool',
                agentName: activeAgentNameRef.current,
                action: 'Executing Tool Context',
                logs: data.content,
                payload: data
              });
              setAgentSteps(prev => {
                const markedPrev = prev.map(s => ({ ...s, done: true }));
                const exists = markedPrev.find(s => s.label === data.content);
                if (exists) return markedPrev;
                return [...markedPrev, { status: 'status', label: data.content, done: false }];
              });
            }
          } else if (data.type === 'routing_decision') {
            const routingEvent = new CustomEvent('agent_routing_decision', { detail: { agent_id: data.agent_id, agent_name: data.agent_name } });
            window.dispatchEvent(routingEvent);
            activeAgentNameRef.current = data.agent_name || 'Execution Agent';
            useTraceStore.getState().addStep({
              type: 'routing',
              agentName: 'Supervisor Router',
              action: `Routed execution path to: ${data.agent_name}`,
              logs: `Selected Target Agent: ${data.agent_name}`,
              payload: data
            });
            setAgentSteps(prev => {
              const markedPrev = prev.map(s => ({ ...s, done: true }));
              return [...markedPrev, { status: 'routing', label: `Routed to: ${data.agent_name || 'Agent'}`, done: false }];
            });
          } else if (data.type === 'error') {
            console.error('WebSocket received error:', data.content);
            toast.error(data.content);
            useTraceStore.getState().addStep({
              type: 'error',
              agentName: 'Execution Pipeline',
              action: 'Operation Encountered Error',
              logs: data.content,
              payload: data
            });
            const fullContent = textAccRef.current;
            textAccRef.current = '';
            setAgentStatus('idle');
            
            const doneSteps = agentStepsRef.current.map(s => ({ ...s, done: true }));
            setAgentSteps(doneSteps);
            
            const streamEndEvent = new CustomEvent('agent_stream_end', { detail: { content: fullContent, steps: doneSteps } });
            window.dispatchEvent(streamEndEvent);
          } else if (data.type === 'approval_required') {
            console.log('WebSocket RECEIVED approval_required:', data.payload);
            setPendingApproval(data.payload);
            setAgentStatus('');
          } else if (data.type === 'stream_end') {
            const fullContent = textAccRef.current;
            textAccRef.current = '';
            setAgentStatus('idle');
            
            const doneSteps = agentStepsRef.current.map(s => ({ ...s, done: true }));
            setAgentSteps(doneSteps);
            
            const streamEndEvent = new CustomEvent('agent_stream_end', { detail: { content: fullContent, steps: doneSteps } });
            window.dispatchEvent(streamEndEvent);
            
            useTraceStore.getState().addStep({
              type: 'routing',
              agentName: activeAgentNameRef.current || 'Execution Pipeline',
              action: 'Stream generation completed successfully',
              logs: fullContent ? `Emitted ${fullContent.length} characters response` : 'Response generated successfully.',
              payload: { response_content: fullContent }
            });
          }
        } catch (err) {
          console.error('Failed to parse WebSocket text message:', err);
        }
      }
    };

    ws.onclose = (event) => {
      console.log('Disconnected from Agent WebSocket:', event.reason);
      setIsConnected(false);
      socketRef.current = null;
      
      const fullContent = textAccRef.current;
      textAccRef.current = '';
      setAgentStatus('idle');
      
      const doneSteps = agentStepsRef.current.map(s => ({ ...s, done: true }));
      setAgentSteps(doneSteps);
      
      const streamEndEvent = new CustomEvent('agent_stream_end', { detail: { content: fullContent, steps: doneSteps } });
      window.dispatchEvent(streamEndEvent);
      
      // Auto-reconnect logic
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log('Attempting to reconnect...');
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
      // onclose will be called after this, handling the reconnect
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      // Clear any pending payload on unmount to avoid stale sends
      pendingPayloadRef.current = null;
      if (socketRef.current) {
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [connect]);

  const sendChatRequest = useCallback((payload) => {
    if (payload && payload.agent_name) {
      activeAgentNameRef.current = payload.agent_name;
    }
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      setAgentTextChunks(''); // clear on new send
      setAgentStatus('');
      setAgentSteps([]);     // reset steps for new message
      useTraceStore.getState().clearSteps(); // clear the trace log panel for the new request
      textAccRef.current = '';
      socketRef.current.send(JSON.stringify({ type: 'chat_request', payload }));
    } else {
      // Socket is CONNECTING or closed — queue the payload and ensure we're connecting
      console.warn('WebSocket not open yet — queuing message and waiting for connection...');
      pendingPayloadRef.current = payload;
      setAgentTextChunks('');
      // Only reconnect if socket is fully closed (not just still CONNECTING)
      if (!socketRef.current || socketRef.current.readyState === WebSocket.CLOSED) {
        connect();
      }
      // The queued payload will be sent in ws.onopen
    }
  }, [connect]);
  
  const clearTextChunks = useCallback(() => {
    textAccRef.current = '';
    setAgentTextChunks('');
    setAgentStatus('');
  }, []);

  const clearAgentSteps = useCallback(() => {
    agentStepsRef.current = [];
    _setAgentSteps([]);
  }, []);

  const sendApprovalResponse = useCallback((decision, toolCallId) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        type: 'tool_approval_response',
        payload: {
          decision,
          tool_call_id: toolCallId
        }
      }));
      setPendingApproval(null);
    }
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
