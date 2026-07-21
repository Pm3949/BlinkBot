import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { getAuthHeaders } from "../lib/api";

import {
  createAgent,
  deleteAgent,
  getAgents,
  updateAgent,
} from "../services/agentService";

export function useAgents(workspaceId, includeGateways = false) {
  return useQuery({
    queryKey: ["agents", workspaceId, includeGateways],

    queryFn: () =>
      getAgents(workspaceId, includeGateways),

    enabled: !!workspaceId,
  });
}

export function useCreateAgent(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createAgent,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agents", workspaceId],
      });
      queryClient.invalidateQueries({
        queryKey: ["agent-projects-sub-agents"],
      });
    },
  });
}

export function useCreateAgentProject(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => import("../services/agentService").then(m => m.createAgentProject(payload)),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agent-projects", workspaceId],
      });
    },
  });
}

export function useUpdateAgent(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }) =>
      updateAgent(id, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agents", workspaceId],
      });
      queryClient.invalidateQueries({
        queryKey: ["agent-projects-sub-agents"],
      });
    },
  });
}

export function useDeleteAgent(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteAgent,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agents", workspaceId],
      });
      queryClient.invalidateQueries({
        queryKey: ["agent-projects-sub-agents"],
      });
    },
  });
}

export function useAgentProjects(workspaceId) {
  return useQuery({
    queryKey: ["agent-projects", workspaceId],

    queryFn: () =>
      import("../services/agentService").then((m) => m.getAgentProjects(workspaceId)),

    enabled: !!workspaceId,
  });
}

export function useProjectSubAgents(projectId) {
  return useQuery({
    queryKey: ["agent-projects-sub-agents", projectId],

    queryFn: () =>
      import("../services/agentService").then((m) => m.getProjectSubAgents(projectId)),

    enabled: !!projectId,
  });
}

export function useDeleteAgentProject(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => import("../services/agentService").then(m => m.deleteAgentProject(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agent-projects", workspaceId],
      });
    },
  });
}

export function useProjectTools(projectId) {
  return useQuery({
    queryKey: ["agent-projects-tools", projectId],
    queryFn: async () => {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/api/agent-projects/${projectId}/tools`, {
        headers: getAuthHeaders()
      });
      if (!response.ok) throw new Error("Failed to fetch tools");
      return response.json();
    },
    enabled: !!projectId,
  });
}

export function useUpdateTool(projectId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }) => {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/api/tools/${id}`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Failed to update tool");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-projects-tools", projectId] });
    },
  });
}

export function useCreateTool(projectId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload) => {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/api/agent-projects/${projectId}/tools`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("Failed to create tool");
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agent-projects-tools", projectId] });
    },
  });
}
