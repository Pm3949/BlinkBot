import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createAgent,
  deleteAgent,
  getAgents,
  updateAgent,
} from "../services/agentService";

export function useAgents(workspaceId) {
  return useQuery({
    queryKey: ["agents", workspaceId],

    queryFn: () =>
      getAgents(workspaceId),

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
    },
  });
}
