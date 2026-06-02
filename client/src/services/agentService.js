import { supabase } from "../supabaseClient";

async function getAuthenticatedUser() {
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error) throw error;

  if (!user?.id) {
    throw new Error(
      "You must be signed in to manage agents.",
    );
  }

  return user;
}

export async function getAgents(userId) {
  if (!userId) return [];

  const { data, error } = await supabase
    .from("agents")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", {
      ascending: false,
    });

  if (error) throw error;

  return data || [];
}

export async function createAgent(payload) {
  const user = await getAuthenticatedUser();

  const agentPayload = {
    name: payload.name,
    description: payload.description || "",
    provider: payload.provider,
    model: payload.model,
    embedding_model: payload.embedding_model,
    chunk_strategy: payload.chunk_strategy,
    system_prompt: payload.system_prompt || "",
    api_key: payload.api_key || "",
    user_id: user.id,
  };

  const { data, error } = await supabase
    .from("agents")
    .insert(agentPayload)
    .select()
    .single();

  if (error) throw error;

  return data;
}

export async function updateAgent(
  id,
  payload
) {
  const user = await getAuthenticatedUser();

  const { data, error } = await supabase
    .from("agents")
    .update(payload)
    .eq("id", id)
    .eq("user_id", user.id)
    .select()
    .single();

  if (error) throw error;

  return data;
}

export async function deleteAgent(id) {
  const user = await getAuthenticatedUser();

  const { error } = await supabase
    .from("agents")
    .delete()
    .eq("id", id)
    .eq("user_id", user.id);

  if (error) throw error;
}
