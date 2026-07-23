import { supabase } from "../supabaseClient";
import { getAuthHeaders } from "../lib/api";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function getAuthenticatedUser() {
  const userStr = localStorage.getItem("user");
  if (!userStr) throw new Error("You must be signed in.");
  return JSON.parse(userStr);
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
    const wsRes = await fetch(`${API_URL}/api/workspaces/primary`, {
      headers: getAuthHeaders()
    });
    if (wsRes.ok) {
      const wsData = await wsRes.json();
      resolvedWorkspaceId = wsData.id;
    }
  }

  if (!resolvedWorkspaceId) return [];

  const response = await fetch(`${API_URL}/api/workspaces/${resolvedWorkspaceId}/members`, {
    headers: getAuthHeaders()
  });
  if (!response.ok) {
    throw new Error("Failed to fetch workspace members");
  }

  return response.json();
}

export async function inviteMember(email, role) {
  const user = await getAuthenticatedUser();

  // Find current user's workspace
  const wsRes = await fetch(`${API_URL}/api/workspaces/primary`, {
    headers: getAuthHeaders()
  });
  if (!wsRes.ok) throw new Error("No workspace found.");

  const wsData = await wsRes.json();
  const workspaceId = wsData.id;
  const workspaceName = wsData.name || "Shared Workspace";
  const invitedByName = user.email; // Can change to user.user_metadata.full_name if available

  // FastAPI backend Call
  const response = await fetch(`${API_URL}/api/workspaces/invite`, {
    method: "POST",
    headers: getAuthHeaders(),
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
    headers: getAuthHeaders(),
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
    headers: getAuthHeaders(),
    body: JSON.stringify({ permissions }),
  });

  if (!response.ok) {
    throw new Error("Failed to update member permissions");
  }

  return response.json();
}

export async function removeMember(memberId) {
  const response = await fetch(`${API_URL}/api/workspaces/members/${memberId}`, {
    method: "DELETE",
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to remove member");
  }
}

export async function claimPendingInvitesApi() {
  const response = await fetch(`${API_URL}/api/workspaces/claim-invites`, {
    method: "POST",
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    throw new Error("Failed to claim pending workspace invites");
  }

  return response.json();
}

export async function resendInviteMember(memberId) {
  const response = await fetch(`${API_URL}/api/workspaces/members/${memberId}/resend-invite`, {
    method: "POST",
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || "Failed to resend invitation");
  }

  return response.json();
}
