import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getChatbots,
  getChatbotById,
  importChatbot,
  updateChatbot,
  deleteChatbot,
} from "../services/chatbotService";

export function useChatbots(workspaceId) {
  return useQuery({
    queryKey: ["chatbots", workspaceId],
    queryFn: () => getChatbots(workspaceId),
    enabled: !!workspaceId,
  });
}

export function useChatbotById(id) {
  return useQuery({
    queryKey: ["chatbot", id],
    queryFn: () => getChatbotById(id),
    enabled: !!id,
  });
}

export function useImportChatbot(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importChatbot,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["chatbots", workspaceId],
      });
    },
  });
}

export function useUpdateChatbot(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }) => updateChatbot(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["chatbots", workspaceId],
      });
    },
  });
}

export function useDeleteChatbot(workspaceId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteChatbot,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["chatbots", workspaceId],
      });
    },
  });
}
