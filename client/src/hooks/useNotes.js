import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getNotes, createNote, deleteNote, togglePinNote } from "../services/noteService";
import { useUIStore } from "../store/useUIStore";
import { toast } from "sonner";

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
  const queryClient = useQueryClient();

  const { data: notes = [], isLoading } = useQuery({
    queryKey: ["notes", activeWorkspaceId],
    queryFn: () => getNotes(activeWorkspaceId),
    enabled: !!activeWorkspaceId,
  });

  const createMutation = useMutation({
    mutationFn: createNote,
    onMutate: async (newNote) => {
      await queryClient.cancelQueries({ queryKey: ["notes", activeWorkspaceId] });
      const previousNotes = queryClient.getQueryData(["notes", activeWorkspaceId]);
      const optimisticNote = {
        id: `temp-${Date.now()}`,
        userId: "temp",
        workspaceId: activeWorkspaceId,
        agentId: newNote.agent_id,
        agentName: newNote.agent_name,
        title: newNote.title,
        content: newNote.content,
        pinned: false,
        createdAt: new Date().toISOString()
      };
      queryClient.setQueryData(["notes", activeWorkspaceId], (old) => [optimisticNote, ...(old || [])]);
      return { previousNotes };
    },
    onError: (err, newNote, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(["notes", activeWorkspaceId], context.previousNotes);
      }
      toast.error("Failed to save note");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["notes", activeWorkspaceId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteNote,
    onMutate: async (noteId) => {
      await queryClient.cancelQueries({ queryKey: ["notes", activeWorkspaceId] });
      const previousNotes = queryClient.getQueryData(["notes", activeWorkspaceId]);
      queryClient.setQueryData(["notes", activeWorkspaceId], (old) => (old || []).filter((n) => n.id !== noteId));
      return { previousNotes };
    },
    onError: (err, noteId, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(["notes", activeWorkspaceId], context.previousNotes);
      }
      toast.error("Failed to delete note");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["notes", activeWorkspaceId] });
    },
  });

  const pinMutation = useMutation({
    mutationFn: ({ id, pinned }) => togglePinNote(id, pinned),
    onMutate: async ({ id, pinned }) => {
      await queryClient.cancelQueries({ queryKey: ["notes", activeWorkspaceId] });
      const previousNotes = queryClient.getQueryData(["notes", activeWorkspaceId]);
      queryClient.setQueryData(["notes", activeWorkspaceId], (old) => 
        (old || []).map((n) => n.id === id ? { ...n, pinned } : n)
      );
      return { previousNotes };
    },
    onError: (err, variables, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(["notes", activeWorkspaceId], context.previousNotes);
      }
      toast.error("Failed to update pin");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["notes", activeWorkspaceId] });
    },
  });

  const addNote = (content, agent) => {
    const text = content?.trim();
    if (!text) {
      toast.error("Nothing to save yet.");
      return null;
    }

    if (!activeWorkspaceId) {
      toast.error("No active workspace selected.");
      return null;
    }

    // Optimistic check
    const existing = notes.find(
      (note) => note.content === text && (note.agentId || null) === (agent?.id || null)
    );
    if (existing) return existing;

    const payload = {
      workspace_id: activeWorkspaceId,
      agent_id: agent?.id || null,
      agent_name: agent?.name || "General",
      title: createTitle(text),
      content: text,
    };

    createMutation.mutate(payload);
    return payload; // Optimistic return
  };

  const removeNote = (noteId) => {
    deleteMutation.mutate(noteId);
  };

  const togglePin = (noteId) => {
    const note = notes.find((n) => n.id === noteId);
    if (note) {
      pinMutation.mutate({ id: noteId, pinned: !note.pinned });
    }
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
    isLoading,
    addNote,
    deleteNote: removeNote,
    togglePin,
    isSaved,
  };
}
