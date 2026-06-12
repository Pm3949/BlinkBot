import { supabase } from "../supabaseClient";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function getAuthenticatedUser() {
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error) throw error;
  if (!user?.id) throw new Error("You must be signed in to manage notes.");
  return user;
}

export async function getNotes(workspaceId) {
  if (!workspaceId) return [];
  const response = await fetch(`${API_URL}/api/notes?workspace_id=${workspaceId}`);
  if (!response.ok) throw new Error("Failed to fetch notes");
  return response.json();
}

export async function createNote(payload) {
  const user = await getAuthenticatedUser();
  const response = await fetch(`${API_URL}/api/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, user_id: user.id }),
  });
  if (!response.ok) throw new Error("Failed to create note");
  return response.json();
}

export async function deleteNote(noteId) {
  const response = await fetch(`${API_URL}/api/notes/${noteId}`, {
    method: "DELETE",
  });
  if (!response.ok) throw new Error("Failed to delete note");
  return response.json();
}

export async function togglePinNote(noteId, pinned) {
  const response = await fetch(`${API_URL}/api/notes/${noteId}/pin`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pinned }),
  });
  if (!response.ok) throw new Error("Failed to update note pin");
  return response.json();
}
