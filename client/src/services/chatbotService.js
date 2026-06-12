const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function getChatbots(workspaceId) {
  const response = await fetch(`${API_URL}/api/chatbots?workspace_id=${workspaceId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch chatbots");
  }
  return response.json();
}

export async function getChatbotById(id) {
  const response = await fetch(`${API_URL}/api/chatbots/${id}`);
  if (!response.ok) {
    throw new Error("Failed to fetch chatbot by id");
  }
  return response.json();
}

export async function importChatbot(payload) {
  const response = await fetch(`${API_URL}/api/chatbots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      agent_id: payload.agent_id,
      name: payload.name,
      settings: payload.settings || {},
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Error importing chatbot");
  }

  return response.json();
}

export async function updateChatbot(id, payload) {
  const response = await fetch(`${API_URL}/api/chatbots/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Error updating chatbot");
  }

  return response.json();
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
