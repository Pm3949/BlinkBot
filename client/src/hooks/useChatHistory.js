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

export function useChatSessions() {
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);

  return useQuery({
    queryKey: ["chat_sessions", user?.id, activeWorkspaceId],
    queryFn: async () => {
      if (!user || !activeWorkspaceId) return [];
      const data = await getChatSessions(activeWorkspaceId, user.id);
      
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
      if (!sessionId) return [];
      return await getChatMessages(sessionId);
    },
    enabled: !!sessionId,
  });
}

export function useChatMutations() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const createSession = useMutation({
    mutationFn: async ({ agentId, title = "New chat" }) => {
      const activeWorkspaceId = useUIStore.getState().activeWorkspaceId;
      const data = await createChatSession({
        user_id: user.id,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
    }
  });

  const renameSession = useMutation({
    mutationFn: async ({ id, title }) => {
      await updateChatSession(id, { title });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
    }
  });

  const togglePinSession = useMutation({
    mutationFn: async ({ id, pinned }) => {
      await updateChatSession(id, { pinned });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
    }
  });

  const deleteSession = useMutation({
    mutationFn: async (id) => {
      await deleteChatSession(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
    }
  });

  const addMessage = useMutation({
    mutationFn: async ({ sessionId, role, content, latency }) => {
      const data = await addChatMessage({
        session_id: sessionId,
        role,
        content,
        latency: latency || null
      });
        
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["chat_messages", variables.sessionId] });
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
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
