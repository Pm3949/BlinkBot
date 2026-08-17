import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAuthHeaders } from "../lib/api";

const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Fetch active models for dropdowns
export function useActiveModels() {
  return useQuery({
    queryKey: ["active-models"],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/models`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error("Failed to fetch active models");
      return response.json();
    },
    staleTime: 1000 * 60 * 5, // 5 minutes cache
  });
}

// Fetch all models for Admin management
export function useAllModels() {
  return useQuery({
    queryKey: ["all-models"],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/models/all`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error("Failed to fetch all models");
      return response.json();
    },
  });
}

// Create custom model
export function useCreateModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload) => {
      const response = await fetch(`${API_URL}/api/models`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Failed to create model");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-models"] });
      queryClient.invalidateQueries({ queryKey: ["all-models"] });
    },
  });
}

// Update model or toggle status
export function useUpdateModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ modelId, data }) => {
      const response = await fetch(`${API_URL}/api/models/${modelId}`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
      });
      if (!response.ok) throw new Error("Failed to update model");
      return response.json();
    },
    // Optimistic update: flip is_active in cache immediately before the server responds
    onMutate: async ({ modelId, data }) => {
      if (!("is_active" in data)) return; // only optimise toggle actions

      // Cancel any in-flight refetches so they don't overwrite our optimistic value
      await queryClient.cancelQueries({ queryKey: ["all-models"] });
      await queryClient.cancelQueries({ queryKey: ["active-models"] });

      // Snapshot current cache for rollback
      const previousAllModels = queryClient.getQueryData(["all-models"]);
      const previousActiveModels = queryClient.getQueryData(["active-models"]);

      // Apply optimistic patch to all-models cache
      queryClient.setQueryData(["all-models"], (old) => {
        if (!old?.models) return old;
        return {
          ...old,
          models: old.models.map((m) =>
            m.id === modelId ? { ...m, is_active: data.is_active } : m
          ),
        };
      });

      // Apply optimistic patch to active-models cache
      queryClient.setQueryData(["active-models"], (old) => {
        if (!old?.models) return old;
        return {
          ...old,
          models: old.models.map((m) =>
            m.id === modelId ? { ...m, is_active: data.is_active } : m
          ),
        };
      });

      // Return snapshot so onError can roll back
      return { previousAllModels, previousActiveModels };
    },
    // Roll back cache if the server call fails
    onError: (_err, _vars, context) => {
      if (context?.previousAllModels !== undefined) {
        queryClient.setQueryData(["all-models"], context.previousAllModels);
      }
      if (context?.previousActiveModels !== undefined) {
        queryClient.setQueryData(["active-models"], context.previousActiveModels);
      }
    },
    // Always re-sync with server after mutation settles
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["active-models"] });
      queryClient.invalidateQueries({ queryKey: ["all-models"] });
    },
  });
}

// Delete model
export function useDeleteModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (modelId) => {
      const response = await fetch(`${API_URL}/api/models/${modelId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error("Failed to delete model");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["active-models"] });
      queryClient.invalidateQueries({ queryKey: ["all-models"] });
    },
  });
}

// Test Provider Key Connectivity
export function useTestProviderKey() {
  return useMutation({
    mutationFn: async ({ provider, api_key, base_url }) => {
      const response = await fetch(`${API_URL}/api/models/test-key`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ provider, api_key, base_url }),
      });
      if (!response.ok) throw new Error("Connection test failed");
      return response.json();
    },
  });
}

// Test Single Model Live Execution
export function useTestSingleModel() {
  return useMutation({
    mutationFn: async ({ provider, model_id, api_key, base_url }) => {
      const response = await fetch(`${API_URL}/api/models/test-model`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ provider, model_id, api_key, base_url }),
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || "Model test failed");
      }
      return response.json();
    },
  });
}

// Fetch available models with billing and byok info
export function useAvailableModels() {
  return useQuery({
    queryKey: ["available-models"],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/models/available`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error("Failed to fetch available models");
      return response.json();
    },
    staleTime: 1000 * 60 * 30, // 30 minutes — models rarely change mid-session
  });
}

