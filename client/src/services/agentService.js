import { supabase } from "../supabaseClient";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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

  const response = await fetch(`${API_URL}/api/agents?workspace_id=${workspaceId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch agents");
  }

  return response.json();
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

  const response = await fetch(`${API_URL}/api/agents`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(agentPayload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create agent");
  }

  return response.json();
}

export async function updateAgent(
  id,
  payload
) {
  const user = await getAuthenticatedUser();

  const response = await fetch(`${API_URL}/api/agents/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update agent");
  }

  return response.json();
}

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
