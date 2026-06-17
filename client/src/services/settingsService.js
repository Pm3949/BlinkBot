import { supabase } from "../supabaseClient";

const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;

async function getAuthenticatedUser() {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  if (!user?.id) throw new Error("You must be signed in.");
  return user;
}

export async function getUserSettings() {
  const user = await getAuthenticatedUser();
  const response = await fetch(`${API_URL}/api/settings/${user.id}`);

  if (!response.ok) {
    throw new Error("Failed to fetch user settings");
  }

  return response.json();
}

export async function updateUserSettings(settings) {
  const user = await getAuthenticatedUser();
  const response = await fetch(`${API_URL}/api/settings/${user.id}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });

  if (!response.ok) {
    throw new Error("Failed to update user settings");
  }

  return response.json();
}

// Getting user's primary workspace (assuming the first one for simplicity, or the one they own)
export async function getPrimaryWorkspace() {
  const user = await getAuthenticatedUser();
  const response = await fetch(`${API_URL}/api/workspaces/primary/${user.id}`);

  if (!response.ok) {
    throw new Error("Failed to fetch primary workspace");
  }

  return response.json();
}

export async function updateWorkspace(id, name) {
  if (!id) throw new Error("Workspace ID is required");
  const response = await fetch(`${API_URL}/api/workspaces/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });

  if (!response.ok) {
    throw new Error("Failed to update workspace");
  }

  return response.json();
}

export async function getUserWorkspaces() {
  const user = await getAuthenticatedUser();
  const response = await fetch(`${API_URL}/api/workspaces/user/${user.id}`);

  if (!response.ok) {
    throw new Error("Failed to fetch user workspaces");
  }

  return response.json();
}
