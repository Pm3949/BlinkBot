import { supabase } from "../supabaseClient";

async function getAuthenticatedUser() {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  if (!user?.id) throw new Error("You must be signed in.");
  return user;
}

export async function getUserSettings() {
  const user = await getAuthenticatedUser();
  const { data, error } = await supabase
    .from("user_settings")
    .select("*")
    .eq("user_id", user.id)
    .single();

  if (error && error.code !== "PGRST116") {
    throw error;
  }
  
  if (!data) {
    return {
      openai_api_key: "",
      groq_api_key: "",
      gemini_api_key: "",
      two_factor_enabled: false
    };
  }
  return data;
}

export async function updateUserSettings(settings) {
  const user = await getAuthenticatedUser();
  const { data, error } = await supabase
    .from("user_settings")
    .upsert({
      user_id: user.id,
      ...settings,
      updated_at: new Date().toISOString()
    }, { onConflict: 'user_id' })
    .select()
    .single();

  if (error) throw error;
  return data;
}

// Getting user's primary workspace (assuming the first one for simplicity, or the one they own)
export async function getPrimaryWorkspace() {
  const user = await getAuthenticatedUser();
  const { data, error } = await supabase
    .from("workspaces")
    .select("*")
    .eq("owner_id", user.id)
    .limit(1)
    .single();
    
  if (error && error.code !== "PGRST116") throw error;
  return data || { name: "" };
}

export async function updateWorkspace(id, name) {
  if (!id) throw new Error("Workspace ID is required");
  const { data, error } = await supabase
    .from("workspaces")
    .update({ name })
    .eq("id", id)
    .select()
    .single();

  if (error) throw error;
  return data;
}

export async function getUserWorkspaces() {
  const user = await getAuthenticatedUser();
  const { data, error } = await supabase
    .from("workspace_members")
    .select("role, permissions, workspace:workspaces(id, name, owner_id)")
    .eq("user_id", user.id);

  if (error) throw error;
  
  // Filter out any null joins and return clean objects
  return data
    .filter(member => member.workspace !== null)
    .map(member => ({
      id: member.workspace.id,
      name: member.workspace.name,
      owner_id: member.workspace.owner_id,
      role: member.role,
      permissions: member.permissions
    }));
}
