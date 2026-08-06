import { getAuthHeaders } from "../lib/api";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export async function getWorkspaceTools(workspaceId) {
  const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/tools`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to fetch workspace tools");
  }
  return response.json();
}

export async function createWorkspaceTool(workspaceId, payload) {
  const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/tools`, {
    method: "POST",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || "Failed to create workspace tool");
  }
  return response.json();
}

export async function updateWorkspaceTool(workspaceId, toolId, payload) {
  const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/tools/${toolId}`, {
    method: "PUT",
    headers: {
      ...getAuthHeaders(),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || errorData.detail || "Failed to update workspace tool");
  }
  return response.json();
}

export async function deleteWorkspaceTool(workspaceId, toolId) {
  const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/tools/${toolId}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to delete workspace tool");
  }
  return response.json();
}

export async function getAgentAttachedTools(agentId) {
  const response = await fetch(`${API_URL}/api/agents/${agentId}/tools`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to fetch attached tools");
  }
  return response.json();
}

export async function attachToolToAgent(agentId, toolId) {
  const response = await fetch(`${API_URL}/api/agents/${agentId}/tools/${toolId}`, {
    method: "POST",
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to attach tool");
  }
  return response.json();
}

export async function detachToolFromAgent(agentId, toolId) {
  const response = await fetch(`${API_URL}/api/agents/${agentId}/tools/${toolId}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to detach tool");
  }
  return response.json();
}
