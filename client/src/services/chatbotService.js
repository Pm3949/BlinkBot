import { supabase } from "../supabaseClient";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function getChatbots(workspaceId) {
  const { data, error } = await supabase
    .from("chatbots")
    .select(`
      *,
      agents!inner (
        workspace_id,
        name
      )
    `)
    .eq("agents.workspace_id", workspaceId)
    .order("created_at", { ascending: false });

  if (error) {
    console.error("Error fetching chatbots:", error);
    throw error;
  }

  return data;
}

export async function getChatbotById(id) {
  const { data, error } = await supabase
    .from("chatbots")
    .select(`
      *,
      agents!inner (
        workspace_id,
        name
      )
    `)
    .eq("id", id)
    .single();

  if (error) {
    console.error("Error fetching chatbot by id:", error);
    throw error;
  }

  return data;
}

export async function importChatbot(payload) {
  const { data, error } = await supabase
    .from("chatbots")
    .insert([
      {
        agent_id: payload.agent_id,
        name: payload.name,
        settings: payload.settings || {},
      },
    ])
    .select()
    .single();

  if (error) {
    console.error("Error importing chatbot:", error);
    throw error;
  }

  return data;
}

export async function updateChatbot(id, payload) {
  const { data, error } = await supabase
    .from("chatbots")
    .update(payload)
    .eq("id", id)
    .select()
    .single();

  if (error) {
    console.error("Error updating chatbot:", error);
    throw error;
  }

  return data;
}

export async function deleteChatbot(id) {
  const response = await fetch(`${API_URL}/chatbots/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to delete chatbot");
  }

  return true;
}
