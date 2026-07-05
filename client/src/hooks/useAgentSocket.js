import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';

export const useAgentSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const [agentTextChunks, setAgentTextChunks] = useState('');
  const [agentStatus, setAgentStatus] = useState('');
  // Queue for messages that arrive before the socket is OPEN
  const pendingPayloadRef = useRef(null);
  // Ref to track accumulated text outside React state (avoids stale closure in stream_end)
  const textAccRef = useRef('');

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
          } else if (data.type === 'status') {
            setAgentStatus(data.content);
          } else if (data.type === 'error') {
            toast.error(data.content);
          } else if (data.type === 'stream_end') {
            // Pass the accumulated text via the event so consumers don't rely on stale React state
            const fullContent = textAccRef.current;
            textAccRef.current = '';
            setAgentStatus('');
            const streamEndEvent = new CustomEvent('agent_stream_end', { detail: { content: fullContent } });
            window.dispatchEvent(streamEndEvent);
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
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      setAgentTextChunks(''); // clear on new send
      setAgentStatus('');
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

  return {
    isConnected,
    agentTextChunks,
    agentStatus,
    sendChatRequest,
    clearTextChunks
  };
};
