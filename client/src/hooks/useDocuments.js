import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  deleteDocument,
  getDocuments,
  processUrl,
  uploadDocument,
  processConnector,
} from "../services/documentService";

export function useDocuments(agentId) {
  return useQuery({
    queryKey: ["documents", agentId],
    queryFn: () => getDocuments(agentId),
    enabled: !!agentId,
  });
}

export function useUploadDocument(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadDocument,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}

export function useProcessUrl(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: processUrl,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}

export function useProcessConnector(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: processConnector,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}

export function useDeleteDocument(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteDocument,

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}
