import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getUserSettings, updateUserSettings, getPrimaryWorkspace, updateWorkspace, getUserWorkspaces, createWorkspace } from "../services/settingsService";
import { useUIStore } from "../store/useUIStore";

export function useUserSettings() {
  return useQuery({
    queryKey: ["user_settings"],
    queryFn: getUserSettings,
  });
}

export function useUpdateUserSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings) => updateUserSettings(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user_settings"] });
    },
  });
}

export function usePrimaryWorkspace() {
  return useQuery({
    queryKey: ["primary_workspace"],
    queryFn: getPrimaryWorkspace,
  });
}

export function useUpdateWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }) => updateWorkspace(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["primary_workspace"] });
    },
  });
}

export function useUserWorkspaces() {
  return useQuery({
    queryKey: ["user_workspaces"],
    queryFn: getUserWorkspaces,
  });
}


export function useWorkspacePermissions() {
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { data: workspaces = [] } = useUserWorkspaces();
  
  const currentWorkspace = workspaces.find((w) => w.id === activeWorkspaceId);
  if (!currentWorkspace) {
    return {
      isOwner: false,
      isAdmin: false,
      canManageStudio: false,
      canManageModels: false,
      canManageAgents: false,
      role: "Viewer"
    };
  }
  const role = currentWorkspace.role;
  const isOwner = role === "Owner";
  const isAdmin = role === "Admin" || isOwner;
  const canManageStudio = isAdmin || currentWorkspace.permissions?.studio === true || currentWorkspace.permissions?.agents === true;
  const canManageModels = isAdmin || currentWorkspace.permissions?.models === true;
  return {
    role,
    isOwner,
    isAdmin,
    canManageStudio,
    canManageModels,
    canManageAgents: canManageStudio,
  };
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => createWorkspace(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user_workspaces"] });
    },
  });
}