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
