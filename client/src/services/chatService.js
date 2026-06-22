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

export async function streamChat(payload, onChunk) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await getErrorMessage(response);
    throw new Error(message || "Failed to connect to chat.");
  }

  if (!response.body) {
    throw new Error("Chat response stream is empty.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let result = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) break;

    const chunk = decoder.decode(value, {
      stream: true,
    });

    result += chunk;
    onChunk(result);
  }

  const finalText = result.trim();

  if (!finalText) {
    throw new Error("The assistant returned an empty response.");
  }

  return finalText;
}

export async function getChatSessions(workspaceId, userId) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions/${workspaceId}?user_id=${userId}`);
  if (!response.ok) throw new Error("Failed to fetch chat sessions");
  return response.json();
}

export async function createChatSession(payload) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to create chat session");
  return response.json();
}

export async function updateChatSession(sessionId, payload) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions/${sessionId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to update chat session");
  return response.json();
}

export async function deleteChatSession(sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/chat_sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete chat session");
  return response.json();
}

export async function getChatMessages(sessionId) {
  const response = await fetch(`${API_BASE_URL}/api/chat_messages/${sessionId}`);
  if (!response.ok) throw new Error("Failed to fetch chat messages");
  return response.json();
}

export async function addChatMessage(payload) {
  const response = await fetch(`${API_BASE_URL}/api/chat_messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error("Failed to add chat message");
  return response.json();
}
