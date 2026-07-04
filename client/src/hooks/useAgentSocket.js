import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';

export const useAgentSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  // Store the active message chunks
  const [agentTextChunks, setAgentTextChunks] = useState('');

  const connect = useCallback(() => {
    // Prevent multiple connections
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('Connected to Agent WebSocket');
      setIsConnected(true);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };

    ws.onmessage = async (event) => {
      if (typeof event.data === 'string') {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'text_chunk') {
            setAgentTextChunks((prev) => prev + data.content);
          } else if (data.type === 'error') {
            toast.error(data.content);
          } else if (data.type === 'stream_end') {
             // We can fire a custom event or let the parent handle the finalized string
             const event = new CustomEvent('agent_stream_end', { detail: { content: data.content } });
             window.dispatchEvent(event);
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
      socketRef.current.send(JSON.stringify({ type: 'chat_request', payload }));
    } else {
      toast.error("Cannot send text, socket not open");
      connect(); // try to reconnect
    }
  }, [connect]);
  
  const clearTextChunks = useCallback(() => setAgentTextChunks(''), []);

  return {
    isConnected,
    agentTextChunks,
    sendChatRequest,
    clearTextChunks
  };
};
