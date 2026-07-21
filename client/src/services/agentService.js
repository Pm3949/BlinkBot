import { supabase } from "../supabaseClient";
import { getAuthHeaders } from "../lib/api";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function getAuthenticatedUser() {
  const userStr = localStorage.getItem("user");
  if (!userStr) throw new Error("You must be signed in.");
  return JSON.parse(userStr);
}

export async function getAgents(workspaceId, includeGateways = false) {
  if (!workspaceId) return [];

  const url = `${API_URL}/api/agents?workspace_id=${workspaceId}${includeGateways ? '&include_gateways=true' : ''}`;
  const response = await fetch(url, { headers: getAuthHeaders() });
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
    output_format: payload.output_format || "",
    api_key: payload.api_key || "",
    workspace_id: payload.workspace_id,
    web_search_enabled: payload.web_search_enabled || false,
    project_id: payload.project_id || null,
    parent_agent_id: payload.parent_agent_id || null,
  };

  const response = await fetch(`${API_URL}/api/agents`, {
    method: "POST",
    headers: getAuthHeaders(),
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
    headers: getAuthHeaders(),
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
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to delete agent");
  }
}

export async function getAgentProjects(workspaceId) {
  if (!workspaceId) return [];

  const response = await fetch(`${API_URL}/api/agent-projects?workspace_id=${workspaceId}`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to fetch agent projects");
  }

  return response.json();
}

export async function getProjectSubAgents(projectId) {
  if (!projectId) return [];

  const response = await fetch(`${API_URL}/api/agent-projects/${projectId}/sub-agents`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to fetch sub agents");
  }

  return response.json();
}

export async function deleteAgentProject(projectId) {
  await getAuthenticatedUser();

  const response = await fetch(`${API_URL}/api/agent-projects/${projectId}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to delete agent project");
  }
}

export async function createAgentProject(payload) {
  const user = await getAuthenticatedUser();
  if (!payload.workspace_id) {
    throw new Error("Workspace ID is required.");
  }

  const response = await fetch(`${API_URL}/api/agent-projects`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create agent project");
  }

  return response.json();
}
