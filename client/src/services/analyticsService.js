import { supabase } from "../supabaseClient";

// We need the python backend URL to fetch analytics. It's usually VITE_API_BASE_URL or hardcoded for now.
const API_URL = import.meta.env.VITE_API_BASE_URL || `${import.meta.env.VITE_API_BASE_URL}`;

async function getAuthenticatedUser() {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  if (!user?.id) throw new Error("You must be signed in.");
  return user;
}

export async function getAnalytics() {
  const user = await getAuthenticatedUser();
  const res = await fetch(`${API_URL}/analytics/${user.id}`);
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || "Failed to fetch analytics");
  }
  return res.json();
}
