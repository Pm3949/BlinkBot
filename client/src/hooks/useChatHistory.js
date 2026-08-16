import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getChatSessions,
  createChatSession,
  updateChatSession,
  deleteChatSession,
  getChatMessages,
  addChatMessage
} from "../services/chatService";
import { useAuth } from "../context/AuthContext";
import { useUIStore } from "../store/useUIStore";

export function useChatSessions(agentId = null) {
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);

  return useQuery({
    queryKey: ["chat_sessions", user?.id, activeWorkspaceId, agentId],
    queryFn: async () => {
      if (!user || !activeWorkspaceId) return [];
      const data = await getChatSessions(activeWorkspaceId, user.id, agentId);
      
      // Map it to match the old store format closely
      return data.map(session => ({
        id: session.id,
        agentId: session.agent_id,
        agentName: session.agent_name || "General",
        title: session.title,
        pinned: session.pinned,
        createdAt: session.created_at,
        updatedAt: session.updated_at,
      }));
    },
    enabled: !!user,
  });
}

export function useChatMessages(sessionId) {
  return useQuery({
    queryKey: ["chat_messages", sessionId],
    queryFn: async () => {
      if (!sessionId || sessionId.startsWith("optimistic-session")) return [];
      const msgs = await getChatMessages(sessionId);
      // Map steps from DB (already parsed JSON from JSONB column) onto each message
      return msgs.map(msg => ({
        ...msg,
        steps: msg.steps || null
      }));
    },
    enabled: !!sessionId && !sessionId.startsWith("optimistic-session"),
  });
}

export function useChatMutations() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const createSession = useMutation({
    mutationFn: async ({ agentId, title = "New chat" }) => {
      const activeWorkspaceId = useUIStore.getState().activeWorkspaceId;
      const data = await createChatSession({
        workspace_id: activeWorkspaceId,
        agent_id: agentId || null,
        title
      });
        
      return {
        id: data.id,
        agentId: data.agent_id,
        title: data.title,
        pinned: data.pinned,
        createdAt: data.created_at,
        updatedAt: data.updated_at
      };
    },
    onSuccess: (newSession, variables) => {
      const activeWorkspaceId = useUIStore.getState().activeWorkspaceId;
      queryClient.setQueryData(
        ["chat_sessions", user?.id, activeWorkspaceId, variables.agentId || null],
        (old = []) => {
          if (old.some(s => s.id === newSession.id)) return old;
          return [newSession, ...old];
        }
      );
    }
  });

  const renameSession = useMutation({
    mutationFn: async ({ id, title }) => {
      await updateChatSession(id, { title });
      return { id, title };
    },
    onSuccess: (data) => {
      queryClient.setQueriesData({ queryKey: ["chat_sessions", user?.id] }, (oldData) => {
        if (!oldData) return oldData;
        return oldData.map(session => {
          if (session.id === data.id) {
            return { ...session, title: data.title };
          }
          return session;
        });
      });
    }
  });

  const togglePinSession = useMutation({
    mutationFn: async ({ id, pinned }) => {
      await updateChatSession(id, { pinned });
      return { id, pinned };
    },
    onSuccess: (data) => {
      queryClient.setQueriesData({ queryKey: ["chat_sessions", user?.id] }, (oldData) => {
        if (!oldData) return oldData;
        return oldData.map(session => {
          if (session.id === data.id) {
            return { ...session, pinned: data.pinned };
          }
          return session;
        });
      });
    }
  });

  const deleteSession = useMutation({
    mutationFn: async (id) => {
      await deleteChatSession(id);
      return id;
    },
    onSuccess: (deletedSessionId) => {
      queryClient.setQueriesData({ queryKey: ["chat_sessions", user?.id] }, (oldData) => {
        if (!oldData) return oldData;
        return oldData.filter(session => session.id !== deletedSessionId);
      });
    }
  });

  const addMessage = useMutation({
    mutationFn: async ({ sessionId, role, content, latency, steps }) => {
      const data = await addChatMessage({
        session_id: sessionId,
        role,
        content,
        latency: latency || null,
        steps: steps || null
      });
        
      return data;
    },
    onSuccess: (newData, variables) => {
      const activeWorkspaceId = useUIStore.getState().activeWorkspaceId;

      // 1. Direct update to the messages cache for this session
      queryClient.setQueryData(["chat_messages", variables.sessionId], (old = []) => {
        const formatted = {
          ...newData,
          steps: newData.steps || null
        };
        if (old.some(m => m.id === formatted.id)) return old;
        return [...old, formatted];
      });

      // 2. Direct update to the sessions cache to bump the updatedAt timestamp
      queryClient.setQueryData(["chat_sessions", user?.id, activeWorkspaceId, variables.agentId || null], (old = []) => {
        return old.map(session => {
          if (session.id === variables.sessionId) {
            return {
              ...session,
              updatedAt: new Date().toISOString()
            };
          }
          return session;
        });
      });
    }
  });

  return {
    createSession,
    renameSession,
    togglePinSession,
    deleteSession,
    addMessage
  };
}
