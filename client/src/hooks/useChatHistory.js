import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { supabase } from "../supabaseClient";
import { useAuth } from "../context/AuthContext";

export function useChatSessions() {
  const { user } = useAuth();

  return useQuery({
    queryKey: ["chat_sessions", user?.id],
    queryFn: async () => {
      if (!user) return [];
      const { data, error } = await supabase
        .from("chat_sessions")
        .select(`
          id,
          agent_id,
          title,
          pinned,
          created_at,
          updated_at,
          agents(name)
        `)
        .eq("user_id", user.id)
        .order("pinned", { ascending: false })
        .order("updated_at", { ascending: false });

      if (error) throw error;
      
      // Map it to match the old store format closely
      return data.map(session => ({
        id: session.id,
        agentId: session.agent_id,
        agentName: session.agents?.name || "General",
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
      const { data, error } = await supabase
        .from("chat_messages")
        .select("id, role, content, created_at, latency")
        .eq("session_id", sessionId)
        .order("created_at", { ascending: true });

      if (error) throw error;
      return data;
    },
    enabled: !!sessionId,
  });
}

export function useChatMutations() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const createSession = useMutation({
    mutationFn: async ({ agentId, title = "New chat" }) => {
      const { data, error } = await supabase
        .from("chat_sessions")
        .insert([{
          user_id: user.id,
          agent_id: agentId || null,
          title
        }])
        .select()
        .single();
        
      if (error) throw error;
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
      const { error } = await supabase
        .from("chat_sessions")
        .update({ title, updated_at: new Date().toISOString() })
        .eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
    }
  });

  const togglePinSession = useMutation({
    mutationFn: async ({ id, pinned }) => {
      const { error } = await supabase
        .from("chat_sessions")
        .update({ pinned, updated_at: new Date().toISOString() })
        .eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
    }
  });

  const deleteSession = useMutation({
    mutationFn: async (id) => {
      const { error } = await supabase
        .from("chat_sessions")
        .delete()
        .eq("id", id);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["chat_sessions", user?.id] });
    }
  });

  const addMessage = useMutation({
    mutationFn: async ({ sessionId, role, content, latency }) => {
      const { data, error } = await supabase
        .from("chat_messages")
        .insert([{
          session_id: sessionId,
          role,
          content,
          latency: latency || null
        }])
        .select()
        .single();
        
      if (error) throw error;
      
      // Update session updated_at
      await supabase
        .from("chat_sessions")
        .update({ updated_at: new Date().toISOString() })
        .eq("id", sessionId);
        
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
