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

export async function getDocuments(agentId) {
  if (!agentId) return [];

  const response = await fetch(
    `${API_BASE_URL}/agents/${agentId}/documents`,
    {
      method: "GET",
      headers: {
        "ngrok-skip-browser-warning": "69420", // Ye line Ngrok ka HTML page bypass karegi
        "Content-Type": "application/json"
      }
    }
  );

  if (!response.ok) {
    const message = await getErrorMessage(response);
    throw new Error(
      message || "Failed to fetch documents.",
    );
  }
  const data = await response.json();
  return data.documents || [];
}

export async function uploadDocument({
  agentId,
  file,
}) {
  const formData = new FormData();
  formData.append("agent_id", agentId);
  formData.append("file", file);

  const response = await fetch(
    `${API_BASE_URL}/process-file`,
    {
      method: "POST",
      body: formData,
    },
  );

  if (!response.ok) {
    const message = await getErrorMessage(response);
    throw new Error(
      message || "Failed to upload document.",
    );
  }

  return response.json();
}

export async function processUrl({
  agentId,
  url,
}) {
  const response = await fetch(
    `${API_BASE_URL}/process-url`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        agent_id: agentId,
        url,
      }),
    },
  );

  if (!response.ok) {
    const message = await getErrorMessage(response);
    throw new Error(
      message || "Failed to process URL.",
    );
  }

  return response.json();
}

export async function processConnector({
  agentId,
  connectorId,
}) {
  const response = await fetch(
    `${API_BASE_URL}/process-connector`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        agent_id: agentId,
        connector_id: connectorId,
      }),
    },
  );

  if (!response.ok) {
    const message = await getErrorMessage(response);
    throw new Error(
      message || "Failed to process connector.",
    );
  }

  return response.json();
}

export async function deleteDocument(id) {
  const response = await fetch(
    `${API_BASE_URL}/documents/${id}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok) {
    const message = await getErrorMessage(response);
    throw new Error(
      message || "Failed to delete document.",
    );
  }

  return response.json();
}
