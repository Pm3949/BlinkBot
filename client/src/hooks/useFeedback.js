import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";
import { useUIStore } from "../store/useUIStore";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function useFeedback() {
  const { user } = useAuth();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const queryClient = useQueryClient();

  const getOpenFeedback = async () => {
    if (!user?.id || !activeWorkspaceId) return [];
    const response = await fetch(`${API_URL}/api/feedback/open?workspace_id=${activeWorkspaceId}&user_id=${user.id}`);
    if (!response.ok) throw new Error("Failed to fetch open feedback");
    return response.json();
  };

  const getPendingVerification = async () => {
    if (!user?.id || !activeWorkspaceId) return [];
    const response = await fetch(`${API_URL}/api/feedback/pending-verification?workspace_id=${activeWorkspaceId}&user_id=${user.id}`);
    if (!response.ok) throw new Error("Failed to fetch pending verifications");
    return response.json();
  };

  const submitFeedback = async (payload) => {
    if (!user?.id || !activeWorkspaceId) throw new Error("Not authenticated");
    const response = await fetch(`${API_URL}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, workspace_id: activeWorkspaceId, created_by: user.id }),
    });
    if (!response.ok) throw new Error("Failed to submit feedback");
    return response.json();
  };

  const resolveFeedback = async (feedbackId) => {
    if (!user?.id) throw new Error("Not authenticated");
    const response = await fetch(`${API_URL}/api/feedback/${feedbackId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ resolved_by: user.id }),
    });
    if (!response.ok) throw new Error("Failed to resolve feedback");
    return response.json();
  };

  const verifyFeedback = async ({ feedbackId, is_satisfied, comment }) => {
    if (!user?.id) throw new Error("Not authenticated");
    const response = await fetch(`${API_URL}/api/feedback/${feedbackId}/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_satisfied, comment, user_id: user.id }),
    });
    if (!response.ok) throw new Error("Failed to verify feedback");
    return response.json();
  };

  return {
    openFeedbackQuery: useQuery({
      queryKey: ["feedback", "open", activeWorkspaceId],
      queryFn: getOpenFeedback,
      enabled: !!user?.id && !!activeWorkspaceId,
    }),
    pendingVerificationsQuery: useQuery({
      queryKey: ["feedback", "pending", activeWorkspaceId],
      queryFn: getPendingVerification,
      enabled: !!user?.id && !!activeWorkspaceId,
    }),
    submitMutation: useMutation({
      mutationFn: submitFeedback,
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["feedback"] });
      },
    }),
    resolveMutation: useMutation({
      mutationFn: resolveFeedback,
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["feedback"] });
      },
    }),
    verifyMutation: useMutation({
      mutationFn: verifyFeedback,
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["feedback"] });
      },
    }),
  };
}
