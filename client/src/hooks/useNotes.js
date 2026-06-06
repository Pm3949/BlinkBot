import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useUIStore } from "../store/useUIStore";
import { encodeId } from "../lib/idCrypt";

/**
 * Returns a workspace-scoped, obfuscated localStorage key.
 * The workspace UUID is encoded so raw IDs never appear in storage.
 * Falls back to a shared "default" bucket when no workspace is active.
 */
function getStorageKey(workspaceId) {
  if (!workspaceId) return "ragmate_notes_default";
  return `ragmate_notes_${encodeId(workspaceId)}`;
}

const NOTES_UPDATED_EVENT = "ragmate-notes-updated";

function readNotes(key) {
  try {
    return JSON.parse(localStorage.getItem(key) || "[]");
  } catch {
    return [];
  }
}

function writeNotes(key, notes) {
  localStorage.setItem(key, JSON.stringify(notes));
  window.dispatchEvent(new Event(NOTES_UPDATED_EVENT));
}

function createTitle(content) {
  const firstLine = content
    .split("\n")
    .map((line) => line.trim())
    .find(Boolean);

  if (!firstLine) return "Saved response";

  const title = firstLine
    .replace(/^#{1,6}\s+/, "")
    .replace(/^[-*+]\s+/, "")
    .replace(/^\d+\.\s+/, "")
    .replace(/\*\*/g, "")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .trim();

  return title.length > 72 ? `${title.slice(0, 72)}...` : title;
}

export function useNotes() {
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const storageKey = getStorageKey(activeWorkspaceId);

  const [notes, setNotes] = useState(() => readNotes(storageKey));

  // Reload notes whenever the active workspace changes
  useEffect(() => {
    setNotes(readNotes(storageKey));
  }, [storageKey]);

  useEffect(() => {
    const syncNotes = () => {
      setNotes(readNotes(storageKey));
    };

    window.addEventListener("storage", syncNotes);
    window.addEventListener(NOTES_UPDATED_EVENT, syncNotes);

    return () => {
      window.removeEventListener("storage", syncNotes);
      window.removeEventListener(NOTES_UPDATED_EVENT, syncNotes);
    };
  }, [storageKey]);

  const addNote = (content, agent) => {
    const text = content?.trim();

    if (!text) {
      toast.error("Nothing to save yet.");
      return null;
    }

    const existing = readNotes(storageKey).find(
      (note) =>
        note.content === text && (note.agentId || null) === (agent?.id || null),
    );

    if (existing) return existing;

    const note = {
      id: crypto.randomUUID(),
      title: createTitle(text),
      content: text,
      agentId: agent?.id || null,
      agentName: agent?.name || "General",
      pinned: false,
      createdAt: new Date().toISOString(),
    };

    const updatedNotes = [note, ...readNotes(storageKey)];
    writeNotes(storageKey, updatedNotes);
    setNotes(updatedNotes);

    return note;
  };

  const deleteNote = (noteId) => {
    const updatedNotes = readNotes(storageKey).filter(
      (note) => note.id !== noteId,
    );
    writeNotes(storageKey, updatedNotes);
    setNotes(updatedNotes);
  };

  const togglePin = (noteId) => {
    const updatedNotes = readNotes(storageKey).map((note) =>
      note.id === noteId ? { ...note, pinned: !note.pinned } : note,
    );
    writeNotes(storageKey, updatedNotes);
    setNotes(updatedNotes);
  };

  const isSaved = (content, agentId = null) => {
    const text = content?.trim();
    if (!text) return false;
    return notes.some(
      (note) => note.content === text && (note.agentId || null) === agentId,
    );
  };

  return {
    notes,
    addNote,
    deleteNote,
    togglePin,
    isSaved,
  };
}
