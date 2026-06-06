import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getWorkspaceMembers,
  inviteMember,
  updateMemberRole,
  updateMemberPermissions,
  removeMember
} from "../services/teamService";
import { useUIStore } from "../store/useUIStore";

const ADMIN_PERMISSIONS = { agents: true, database: true, notes: true };
const DEFAULT_PERMISSIONS = { agents: false, database: false, notes: false };

export function useWorkspaceMembers() {
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  return useQuery({
    queryKey: ["workspace_members", activeWorkspaceId],
    queryFn: () => getWorkspaceMembers(activeWorkspaceId),
    // Don't fetch until we know which workspace is active
    enabled: !!activeWorkspaceId,
  });
}

export function useInviteMember() {
  const queryClient = useQueryClient();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  return useMutation({
    mutationFn: ({ email, role }) => inviteMember(email, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace_members", activeWorkspaceId] });
    },
  });
}

export function useUpdateMemberRole() {
  const queryClient = useQueryClient();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  return useMutation({
    mutationFn: ({ memberId, role }) => updateMemberRole(memberId, role),
    // Optimistic update: immediately reflect new role + permissions in the UI
    onMutate: async ({ memberId, role }) => {
      await queryClient.cancelQueries({ queryKey: ["workspace_members", activeWorkspaceId] });
      const previous = queryClient.getQueryData(["workspace_members", activeWorkspaceId]);

      const autoPerms = role === "Admin" ? ADMIN_PERMISSIONS : DEFAULT_PERMISSIONS;
      queryClient.setQueryData(["workspace_members", activeWorkspaceId], (old) =>
        old
          ? old.map((m) =>
              m.id === memberId ? { ...m, role, permissions: autoPerms } : m
            )
          : []
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["workspace_members", activeWorkspaceId], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace_members", activeWorkspaceId] });
    },
  });
}

export function useUpdateMemberPermissions() {
  const queryClient = useQueryClient();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  return useMutation({
    mutationFn: ({ memberId, permissions }) => updateMemberPermissions(memberId, permissions),
    onMutate: async ({ memberId, permissions }) => {
      await queryClient.cancelQueries({ queryKey: ["workspace_members", activeWorkspaceId] });
      const previousMembers = queryClient.getQueryData(["workspace_members", activeWorkspaceId]);

      queryClient.setQueryData(["workspace_members", activeWorkspaceId], (old) =>
        old ? old.map((m) => (m.id === memberId ? { ...m, permissions } : m)) : []
      );
      return { previousMembers };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousMembers) {
        queryClient.setQueryData(["workspace_members", activeWorkspaceId], context.previousMembers);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace_members", activeWorkspaceId] });
    },
  });
}

export function useRemoveMember() {
  const queryClient = useQueryClient();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  return useMutation({
    mutationFn: removeMember,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workspace_members", activeWorkspaceId] });
    },
  });
}
