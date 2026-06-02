import { useEffect, useState } from "react";
import { toast } from "sonner";

const STORAGE_KEY = "ragmate_notes";
const NOTES_UPDATED_EVENT = "ragmate-notes-updated";

function readNotes() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeNotes(notes) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
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
  const [notes, setNotes] = useState(readNotes);

  useEffect(() => {
    const syncNotes = () => {
      setNotes(readNotes());
    };

    window.addEventListener("storage", syncNotes);
    window.addEventListener(NOTES_UPDATED_EVENT, syncNotes);

    return () => {
      window.removeEventListener("storage", syncNotes);
      window.removeEventListener(NOTES_UPDATED_EVENT, syncNotes);
    };
  }, []);

  const addNote = (content, agent) => {
    const text = content?.trim();

    if (!text) {
      toast.error("Nothing to save yet.");
      return null;
    }

    const existingNote = readNotes().find(
      (note) =>
        note.content === text && (note.agentId || null) === (agent?.id || null),
    );

    if (existingNote) {
      return existingNote;
    }

    const note = {
      id: crypto.randomUUID(),
      title: createTitle(text),
      content: text,
      agentId: agent?.id || null,
      agentName: agent?.name || "General",
      pinned: false,
      createdAt: new Date().toISOString(),
    };

    const updatedNotes = [note, ...readNotes()];
    writeNotes(updatedNotes);
    setNotes(updatedNotes);

    return note;
  };

  const deleteNote = (noteId) => {
    const updatedNotes = readNotes().filter((note) => note.id !== noteId);
    writeNotes(updatedNotes);
    setNotes(updatedNotes);
  };

  const togglePin = (noteId) => {
    const updatedNotes = readNotes().map((note) =>
      note.id === noteId
        ? {
            ...note,
            pinned: !note.pinned,
          }
        : note,
    );

    writeNotes(updatedNotes);
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
