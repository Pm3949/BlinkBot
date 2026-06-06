import LoadingSkeleton from "../shared/LoadingSkeleton";
import AccessDeniedScreen from "./AccessDeniedScreen";
import { useWorkspacePermissions } from "../../hooks/useSettings";
import { useUserWorkspaces } from "../../hooks/useSettings";

/**
 * PermissionRoute
 * ---------------
 * Blocks access to a route unless the current user has the required
 * feature permission in their active workspace.
 *
 * Props:
 *  - permission : keyof WorkspacePermissions
 *      "canManageAgents" | "canManageDatabase" | "canManageNotes"
 *  - label      : human-readable feature name for the error message
 *  - children   : ReactNode — the protected page
 *
 * Usage:
 *  <PermissionRoute permission="canManageAgents" label="Agents">
 *    <AgentsPage />
 *  </PermissionRoute>
 */
export default function PermissionRoute({
  permission,
  label = "this feature",
  children,
}) {
  const { isLoading } = useUserWorkspaces();
  const permissions = useWorkspacePermissions();

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="w-full max-w-md px-6">
          <LoadingSkeleton count={2} className="h-24" />
        </div>
      </div>
    );
  }

  // Admins always pass — they have every permission
  if (permissions.isAdmin) return children;

  if (!permissions[permission]) {
    return (
      <AccessDeniedScreen
        title="Permission Required"
        description={`Your role (${permissions.role}) doesn't include access to ${label}. Ask your workspace Admin to enable this permission for you.`}
      />
    );
  }

  return children;
}
