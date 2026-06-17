import { supabase } from "../supabaseClient";

const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;

async function getAuthenticatedUser() {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  if (!user?.id) throw new Error("You must be signed in.");
  return user;
}

/**
 * Fetch all members of a workspace.
 * @param {string|null} workspaceId - Pass the active workspace ID;
 *   falls back to the first workspace the user belongs to.
 */
export async function getWorkspaceMembers(workspaceId = null) {
  const user = await getAuthenticatedUser();

  let resolvedWorkspaceId = workspaceId;

  // If no workspace ID provided, derive it from the user's primary workspace endpoint
  if (!resolvedWorkspaceId) {
    const wsRes = await fetch(`${API_URL}/api/workspaces/primary/${user.id}`);
    if (wsRes.ok) {
      const wsData = await wsRes.json();
      resolvedWorkspaceId = wsData.id;
    }
  }

  if (!resolvedWorkspaceId) return [];

  const response = await fetch(`${API_URL}/api/workspaces/${resolvedWorkspaceId}/members`);
  if (!response.ok) {
    throw new Error("Failed to fetch workspace members");
  }

  return response.json();
}

export async function inviteMember(email, role) {
  const user = await getAuthenticatedUser();

  // Find current user's workspace
  const wsRes = await fetch(`${API_URL}/api/workspaces/primary/${user.id}`);
  if (!wsRes.ok) throw new Error("No workspace found.");

  const wsData = await wsRes.json();
  const workspaceId = wsData.id;
  const workspaceName = wsData.name || "Shared Workspace";
  const invitedByName = user.email; // Can change to user.user_metadata.full_name if available

  // FastAPI backend Call
  const response = await fetch(`${API_URL}/api/workspaces/invite`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      role,
      workspace_id: workspaceId,
      workspace_name: workspaceName,
      invited_by_name: invitedByName
    }),
  });

  if (!response.ok) {
    const errData = await response.json();
    throw new Error(errData.detail || "Failed to send invite");
  }

  return await response.json();
}

const ADMIN_PERMISSIONS = { agents: true, database: true, notes: true };
const DEFAULT_PERMISSIONS = { agents: false, database: false, notes: false };

export async function updateMemberRole(memberId, role) {
  const response = await fetch(`${API_URL}/api/workspaces/members/${memberId}/role`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });

  if (!response.ok) {
    throw new Error("Failed to update member role");
  }

  return response.json();
}

export async function updateMemberPermissions(memberId, permissions) {
  const response = await fetch(`${API_URL}/api/workspaces/members/${memberId}/permissions`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ permissions }),
  });

  if (!response.ok) {
    throw new Error("Failed to update member permissions");
  }

  return response.json();
}

export async function removeMember(memberId) {
  const response = await fetch(`${API_URL}/api/workspaces/members/${memberId}`, {
    method: "DELETE"
  });

  if (!response.ok) {
    throw new Error("Failed to remove member");
  }
}
