import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getUserSettings, updateUserSettings, getPrimaryWorkspace, updateWorkspace, getUserWorkspaces } from "../services/settingsService";
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
      isAdmin: false,
      canManageAgents: false,
      canManageDatabase: false,
      canManageNotes: false,
      role: "Viewer"
    };
  }
  const role = currentWorkspace.role;
  const isAdmin = role === "Admin";
  return {
    role,
    isAdmin,
    canManageAgents: isAdmin || currentWorkspace.permissions?.agents === true,
    canManageDatabase: isAdmin || currentWorkspace.permissions?.database === true,
    canManageNotes: isAdmin || currentWorkspace.permissions?.notes === true,
  };
}