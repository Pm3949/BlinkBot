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
    onSuccess: () => {
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
