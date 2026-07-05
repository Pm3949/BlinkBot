import { getAuthHeaders } from "../lib/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  `${import.meta.env.VITE_API_BASE_URL}`;

async function getErrorMessage(response) {
  try {
    const data = await response.json();
    return data.detail || data.message;
  } catch {
    return null;
  }
}



export async function getChatSessions(workspaceId, userId) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions/${workspaceId}`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error("Failed to fetch chat sessions");
  return response.json();
}

export async function createChatSession(payload) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to create chat session");
  return response.json();
}

export async function updateChatSession(sessionId, payload) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions/${sessionId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to update chat session");
  return response.json();
}

export async function deleteChatSession(sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions/${sessionId}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error("Failed to delete chat session");
  return response.json();
}

export async function getChatMessages(sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/chat_messages/${sessionId}`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) throw new Error("Failed to fetch chat messages");
  return response.json();
}

export async function addChatMessage(payload) {
  const response = await fetch(`${API_BASE_URL}/api/chat_messages`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to add chat message");
  return response.json();
}
