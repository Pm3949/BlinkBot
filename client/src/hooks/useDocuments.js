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

export function useUpdateUrl(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ docId, url }) => import("../services/documentService").then(m => m.updateUrl({ docId, url })),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}

export function useProcessText(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ filename, text }) => import("../services/documentService").then(m => m.processText({ agentId, filename, text })),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}

export function useUpdateText(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ docId, filename, text }) => import("../services/documentService").then(m => m.updateText({ docId, filename, text })),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}

export function useUpdateFile(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ docId, file }) => import("../services/documentService").then(m => m.updateFile({ docId, file })),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}

export function useSyncConnector(agentId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ docId }) => import("../services/documentService").then(m => m.syncConnector({ docId })),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", agentId],
      });
    },
  });
}
