import { supabase } from "../supabaseClient";
import { getAuthHeaders } from "../lib/api";

// We need the python backend URL to fetch analytics. It's usually VITE_API_BASE_URL or hardcoded for now.
const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function getAuthenticatedUser() {
  const userStr = localStorage.getItem("user");
  if (!userStr) throw new Error("You must be signed in.");
  return JSON.parse(userStr);
}

export async function getAnalytics() {
  const res = await fetch(`${API_URL}/analytics`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || "Failed to fetch analytics");
  }
  return res.json();
}
