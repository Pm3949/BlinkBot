import { supabase } from "../supabaseClient";
import { getAuthHeaders } from "../lib/api";

const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;

async function getAuthenticatedUser() {
  const userStr = localStorage.getItem("user");
  if (!userStr) throw new Error("You must be signed in.");
  return JSON.parse(userStr);
}

export async function getUserSettings() {
  const response = await fetch(`${API_URL}/api/settings`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to fetch user settings");
  }

  return response.json();
}

export async function updateUserSettings(settings) {
  const response = await fetch(`${API_URL}/api/settings`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    throw new Error("Failed to update user settings");
  }

  return response.json();
}

// Getting user's primary workspace (assuming the first one for simplicity, or the one they own)
export async function getPrimaryWorkspace() {
  const response = await fetch(`${API_URL}/api/workspaces/primary`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to fetch primary workspace");
  }

  return response.json();
}

export async function updateWorkspace(id, name) {
  if (!id) throw new Error("Workspace ID is required");
  const response = await fetch(`${API_URL}/api/workspaces/${id}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify({ name }),
  });

  if (!response.ok) {
    throw new Error("Failed to update workspace");
  }

  return response.json();
}

export async function getUserWorkspaces() {
  const response = await fetch(`${API_URL}/api/workspaces/user`, {
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to fetch user workspaces");
  }

  return response.json();
}

export async function createWorkspace(payload) {
  const response = await fetch(`${API_URL}/api/workspaces`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create workspace");
  }

  return response.json();
}
