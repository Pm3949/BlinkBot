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

export function useAgents(userId) {
  return useQuery({
    queryKey: ["agents", userId],

    queryFn: () =>
      getAgents(userId),

    enabled: !!userId,
  });
}

export function useCreateAgent(userId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createAgent,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agents", userId],
      });
    },
  });
}

export function useUpdateAgent(userId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }) =>
      updateAgent(id, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agents", userId],
      });
    },
  });
}

export function useDeleteAgent(userId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteAgent,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["agents", userId],
      });
    },
  });
}
