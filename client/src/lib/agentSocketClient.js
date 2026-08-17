import { toast } from 'sonner';
import { useTraceStore } from '../store/useTraceStore';

class AgentSocketClient {
  constructor() {
    this.socket = null;
    this.url = null;
    this.isConnected = false;
    this.clientId = this.getOrCreateClientId();
    
    // Listeners registered to receive live socket events
    this.listeners = new Map(); // listenerId -> { onMessage, onStatusChange }

    // In-memory state buffers mapped by session ID
    this.buffersBySession = {};

    this.reconnectTimeout = null;
    this.reconnectDelay = 1000; // start with 1s
    this.maxReconnectDelay = 30000; // max 30s
    
    this.pendingPayload = null; // queued requests if socket is not ready yet
  }

  getBuffers(sessionId) {
    const key = sessionId || "general";
    if (!this.buffersBySession[key]) {
      this.buffersBySession[key] = {
        textChunks: '',
        status: '',
        steps: [],
        pendingApproval: null,
        activeAgentName: 'Execution Agent'
      };
    }
    return this.buffersBySession[key];
  }

  get buffers() {
    return this.getBuffers("general");
  }

  getOrCreateClientId() {
    let cid = localStorage.getItem("dashboard_client_id");
    if (!cid) {
      cid = "client_" + Math.random().toString(36).substring(7);
      localStorage.setItem("dashboard_client_id", cid);
    }
    return cid;
  }

  init() {
    if (this.socket) return;

    const apiBase = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    const baseWsUrl = apiBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:');
    this.url = `${baseWsUrl}/ws/chat/${this.clientId}`;
    
    this.connect();
  }

  connect() {
    if (
      this.socket?.readyState === WebSocket.OPEN ||
      this.socket?.readyState === WebSocket.CONNECTING
    ) {
      return;
    }

    console.log('[WebSocketClient] Connecting to:', this.url);
    const ws = new WebSocket(this.url);
    this.socket = ws;

    ws.onopen = () => {
      console.log('[WebSocketClient] Connected successfully');
      this.isConnected = true;
      this.reconnectDelay = 1000; // reset delay on success
      
      this.notifyStatusChange();

      // Flush queued messages if any
      if (this.pendingPayload) {
        const queued = this.pendingPayload;
        this.pendingPayload = null;
        this.clearBuffer();
        this.sendRequest(queued);
      }
    };

    ws.onmessage = (event) => {
      if (typeof event.data !== 'string') return;
      
      try {
        const data = JSON.parse(event.data);
        this.handleIncomingMessage(data);
      } catch (err) {
        console.error('[WebSocketClient] Parse error:', err);
      }
    };

    ws.onclose = (event) => {
      console.log('[WebSocketClient] Disconnected:', event.reason);
      this.isConnected = false;
      this.socket = null;
      this.notifyStatusChange();
      
      // Auto-reconnect with Exponential Backoff
      if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = setTimeout(() => {
        console.log('[WebSocketClient] Reconnecting...');
        this.connect();
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      }, this.reconnectDelay);
    };

    ws.onerror = (error) => {
      console.error('[WebSocketClient] Connection error:', error);
    };
  }

  handleIncomingMessage(data) {
    const sessionId = data.session_id || "general";
    const buffers = this.getBuffers(sessionId);

    if (data.type === 'text_chunk') {
      buffers.textChunks += data.content;
      buffers.status = '';
    } else if (data.type === 'step') {
      if (data.status.startsWith('tool_call_')) {
        const toolName = data.status.replace('tool_call_', '');
        window.dispatchEvent(new CustomEvent('agent_tool_start', { detail: { session_id: sessionId, tool_name: toolName } }));
      } else if (data.status.startsWith('tool_done_')) {
        const toolName = data.status.replace('tool_done_', '');
        window.dispatchEvent(new CustomEvent('agent_tool_end', { detail: { session_id: sessionId, tool_name: toolName } }));
      }

      // Trace logs update
      let logsContent = data.label || data.status;
      if (data.tool_input) {
        const inputStr = typeof data.tool_input === 'object' ? JSON.stringify(data.tool_input, null, 2) : String(data.tool_input);
        logsContent = `${data.label}\n\nInput Parameters:\n${inputStr}`;
      } else if (data.tool_output) {
        const outputStr = typeof data.tool_output === 'object' ? JSON.stringify(data.tool_output, null, 2) : String(data.tool_output);
        logsContent = `${data.label}\n\nOutput Results:\n${outputStr}`;
      }

      useTraceStore.getState().addStep({
        type: data.status.includes('tool_') ? 'tool' : 'routing',
        agentName: buffers.activeAgentName,
        action: data.label || 'Executing Step',
        logs: logsContent,
        payload: data
      });

      // Steps update
      const markedPrev = buffers.steps.map(s => ({ ...s, done: true }));
      const exists = markedPrev.find(s => s.status === data.status && s.label === data.label);
      if (exists) {
        buffers.steps = markedPrev.map(s => (s.status === data.status && s.label === data.label)
          ? { ...s, done: false }
          : s
        );
      } else {
        buffers.steps = [...markedPrev, { status: data.status, label: data.label, done: false }];
      }
    } else if (data.type === 'status') {
      buffers.status = data.content;
      if (data.content) {
        useTraceStore.getState().addStep({
          type: 'tool',
          agentName: buffers.activeAgentName,
          action: 'Executing Tool Context',
          logs: data.content,
          payload: data
        });
        const markedPrev = buffers.steps.map(s => ({ ...s, done: true }));
        const exists = markedPrev.find(s => s.label === data.content);
        if (!exists) {
          buffers.steps = [...markedPrev, { status: 'status', label: data.content, done: false }];
        }
      }
    } else if (data.type === 'routing_decision') {
      window.dispatchEvent(new CustomEvent('agent_routing_decision', { detail: { session_id: sessionId, agent_id: data.agent_id, agent_name: data.agent_name } }));
      buffers.activeAgentName = data.agent_name || 'Execution Agent';
      
      useTraceStore.getState().addStep({
        type: 'routing',
        agentName: 'Supervisor Router',
        action: `Routed execution path to: ${data.agent_name}`,
        logs: `Selected Target Agent: ${data.agent_name}`,
        payload: data
      });
      const markedPrev = buffers.steps.map(s => ({ ...s, done: true }));
      buffers.steps = [...markedPrev, { status: 'routing', label: `Routed to: ${data.agent_name || 'Agent'}`, done: false }];
    } else if (data.type === 'approval_required') {
      buffers.pendingApproval = data.payload;
      buffers.status = '';
    } else if (data.type === 'error') {
      console.error('[WebSocketClient] Pipeline error:', data.content);
      toast.error(data.content);
      
      useTraceStore.getState().addStep({
        type: 'error',
        agentName: 'Execution Pipeline',
        action: 'Operation Encountered Error',
        logs: data.content,
        payload: data
      });
      
      buffers.status = 'idle';
      buffers.steps = buffers.steps.map(s => ({ ...s, done: true }));
      
      this.emitStreamEnd(sessionId, buffers.textChunks, buffers.steps);
    } else if (data.type === 'stream_end') {
      const fullResponse = buffers.textChunks;
      buffers.status = 'idle';
      buffers.steps = buffers.steps.map(s => ({ ...s, done: true }));
      
      this.emitStreamEnd(sessionId, fullResponse, buffers.steps);

      useTraceStore.getState().addStep({
        type: 'routing',
        agentName: buffers.activeAgentName || 'Execution Pipeline',
        action: 'Stream generation completed successfully',
        logs: fullResponse ? `Emitted ${fullResponse.length} characters response` : 'Response generated successfully.',
        payload: { response_content: fullResponse }
      });
    }

    this.broadcastMessage(data);
  }

  emitStreamEnd(sessionId, content, steps) {
    window.dispatchEvent(new CustomEvent('agent_stream_end', { detail: { session_id: sessionId, content, steps } }));
  }

  sendRequest(payload) {
    const sessionId = payload?.session_id || "general";
    const buffers = this.getBuffers(sessionId);
    if (payload && payload.agent_name) {
      buffers.activeAgentName = payload.agent_name;
    }

    if (this.socket?.readyState === WebSocket.OPEN) {
      this.clearBuffer(sessionId);
      this.socket.send(JSON.stringify({ type: 'chat_request', payload }));
    } else {
      console.warn('[WebSocketClient] Socket connecting, queuing request...');
      this.pendingPayload = payload;
      this.clearBuffer(sessionId);
      this.connect();
    }
  }

  sendApproval(decision, toolCallId, sessionId) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({
        type: 'tool_approval_response',
        payload: { decision, tool_call_id: toolCallId }
      }));
      const buffers = this.getBuffers(sessionId);
      buffers.pendingApproval = null;
      this.broadcastMessage({ type: 'approval_cleared', session_id: sessionId });
    }
  }

  clearBuffer(sessionId) {
    const buffers = this.getBuffers(sessionId || "general");
    buffers.textChunks = '';
    buffers.status = '';
    buffers.steps = [];
    buffers.pendingApproval = null;
    useTraceStore.getState().clearSteps();
  }

  // ─── Subscription Model for UI Components ─────────────────────────────────

  subscribe(id, onMessage, onStatusChange) {
    this.listeners.set(id, { onMessage, onStatusChange });
    
    // Sync general buffer state by default upon mount
    if (onMessage) {
      const buffers = this.getBuffers("general");
      onMessage({
        type: 'sync',
        textChunks: buffers.textChunks,
        status: buffers.status,
        steps: buffers.steps,
        pendingApproval: buffers.pendingApproval
      });
    }
  }

  unsubscribe(id) {
    this.listeners.delete(id);
  }

  broadcastMessage(msg) {
    this.listeners.forEach(({ onMessage }) => {
      if (onMessage) onMessage(msg);
    });
  }

  notifyStatusChange() {
    this.listeners.forEach(({ onStatusChange }) => {
      if (onStatusChange) onStatusChange(this.isConnected);
    });
  }
}

// Global Singleton instance (one socket connection app-wide)
export const agentSocketClient = new AgentSocketClient();
