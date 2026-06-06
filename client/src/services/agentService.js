import { supabase } from "../supabaseClient";

async function getAuthenticatedUser() {
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error) throw error;

  if (!user?.id) {
    throw new Error(
      "You must be signed in to manage agents.",
    );
  }

  return user;
}

export async function getAgents(workspaceId) {
  if (!workspaceId) return [];

  const { data, error } = await supabase
    .from("agents")
    .select("*")
    .eq("workspace_id", workspaceId)
    .order("created_at", {
      ascending: false,
    });

  if (error) throw error;

  return data || [];
}

export async function createAgent(payload) {
  const user = await getAuthenticatedUser();
  if (!payload.workspace_id) {
    throw new Error("Workspace ID is required to create an agent.");
  }

  const agentPayload = {
    name: payload.name,
    description: payload.description || "",
    llm_provider: payload.provider,
    llm_model: payload.model,
    embedding_model: payload.embedding_model,
    chunk_strategy: payload.chunk_strategy,
    system_prompt: payload.system_prompt || "",
    api_key: payload.api_key || "",
    user_id: user.id,
    workspace_id: payload.workspace_id,
  };

  const { data, error } = await supabase
    .from("agents")
    .insert(agentPayload)
    .select()
    .single();

  if (error) throw error;

  return data;
}

export async function updateAgent(
  id,
  payload
) {
  const user = await getAuthenticatedUser();

  const { data, error } = await supabase
    .from("agents")
    .update(payload)
    .eq("id", id)
    .eq("user_id", user.id)
    .select()
    .single();

  if (error) throw error;

  return data;
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function deleteAgent(id) {
  await getAuthenticatedUser(); // Verify auth locally

  const response = await fetch(`${API_URL}/agents/${id}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to delete agent");
  }
}
