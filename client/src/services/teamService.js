import { supabase } from "../supabaseClient";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

  // If no workspace ID provided, derive it from the user's memberships
  if (!resolvedWorkspaceId) {
    const { data: userWorkspaces, error: wsError } = await supabase
      .from("workspace_members")
      .select("workspace_id")
      .eq("user_id", user.id)
      .limit(1);

    if (wsError) throw wsError;
    if (!userWorkspaces || userWorkspaces.length === 0) return [];
    resolvedWorkspaceId = userWorkspaces[0].workspace_id;
  }

  // Fetch members AND the workspace's owner_id in one go
  const [membersRes, workspaceRes] = await Promise.all([
    supabase
      .from("workspace_members")
      .select("*")
      .eq("workspace_id", resolvedWorkspaceId)
      .order("created_at", { ascending: true }),
    supabase
      .from("workspaces")
      .select("owner_id")
      .eq("id", resolvedWorkspaceId)
      .single(),
  ]);

  if (membersRes.error) throw membersRes.error;

  const ownerUserId = workspaceRes.data?.owner_id || null;

  return (membersRes.data || []).map((m) => ({
    ...m,
    isOwner: m.user_id === ownerUserId,
  }));
}

export async function inviteMember(email, role) {
  const user = await getAuthenticatedUser();
  
  // Find current user's workspace
  const { data: userWorkspaces } = await supabase
    .from("workspace_members")
    .select("workspace_id, workspaces(name)")
    .eq("user_id", user.id)
    .limit(1);

  if (!userWorkspaces || userWorkspaces.length === 0) {
    throw new Error("No workspace found.");
  }

  const workspaceId = userWorkspaces[0].workspace_id;
  const workspaceName = userWorkspaces[0].workspaces?.name || "Shared Workspace";
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
  await getAuthenticatedUser();

  // When promoting to Admin → grant all permissions automatically.
  // When demoting from Admin → reset permissions to defaults.
  const permissionsUpdate =
    role === "Admin" ? ADMIN_PERMISSIONS : DEFAULT_PERMISSIONS;

  const { data, error } = await supabase
    .from("workspace_members")
    .update({ role, permissions: permissionsUpdate })
    .eq("id", memberId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function updateMemberPermissions(memberId, permissions) {
  await getAuthenticatedUser();
  const { data, error } = await supabase
    .from("workspace_members")
    .update({ permissions })
    .eq("id", memberId)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function removeMember(memberId) {
  await getAuthenticatedUser();
  const { error } = await supabase
    .from("workspace_members")
    .delete()
    .eq("id", memberId);

  if (error) throw error;
}
