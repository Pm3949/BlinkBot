const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

async function getErrorMessage(response) {
  try {
    const data = await response.json();
    return data.detail || data.message;
  } catch {
    return null;
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem("access_token");
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

export async function getDocuments(agentId) {
  if (!agentId) return [];

  const response = await fetch(
    `${API_BASE_URL}/agents/${agentId}/documents`,
    {
      method: "GET",
      headers: {
        "ngrok-skip-browser-warning": "69420",
        "Content-Type": "application/json",
        ...getAuthHeaders()
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
  const headers = getAuthHeaders();

  // 1. Initiate chunked upload session
  const initResponse = await fetch(
    `${API_BASE_URL}/api/documents/upload/initiate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...headers
      },
      body: JSON.stringify({
        agent_id: agentId,
        filename: file.name,
        file_size_bytes: file.size,
      })
    }
  );

  if (!initResponse.ok) {
    const message = await getErrorMessage(initResponse);
    throw new Error(
      message || "Failed to initiate document upload.",
    );
  }

  const { upload_id, chunk_size_bytes } = await initResponse.json();

  // 2. Slice and upload file chunks sequentially
  const totalChunks = Math.ceil(file.size / chunk_size_bytes);
  for (let i = 0; i < totalChunks; i++) {
    const start = i * chunk_size_bytes;
    const end = Math.min(file.size, start + chunk_size_bytes);
    const chunkSlice = file.slice(start, end);

    const formData = new FormData();
    formData.append("chunk", chunkSlice, file.name);

    const chunkResponse = await fetch(
      `${API_BASE_URL}/api/documents/upload/chunk?upload_id=${upload_id}&chunk_index=${i}`,
      {
        method: "PUT",
        headers: {
          ...headers
        },
        body: formData
      }
    );

    if (!chunkResponse.ok) {
      const message = await getErrorMessage(chunkResponse);
      throw new Error(
        message || `Failed to upload chunk ${i + 1} of ${totalChunks}.`,
      );
    }
  }

  // 3. Finalize upload assembly
  const completeResponse = await fetch(
    `${API_BASE_URL}/api/documents/upload/complete`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...headers
      },
      body: JSON.stringify({
        upload_id,
        agent_id: agentId,
        filename: file.name,
      })
    }
  );

  if (!completeResponse.ok) {
    const message = await getErrorMessage(completeResponse);
    throw new Error(
      message || "Failed to finalize document upload.",
    );
  }

  return completeResponse.json();
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
        ...getAuthHeaders()
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
        ...getAuthHeaders()
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
      headers: {
        ...getAuthHeaders()
      }
    }
  );

  if (!response.ok) {
    const message = await getErrorMessage(response);
    throw new Error(
      message || "Failed to delete document.",
    );
  }

  return response.json();
}
