import LoadingSkeleton from "../shared/LoadingSkeleton";
import AccessDeniedScreen from "./AccessDeniedScreen";
import { useWorkspacePermissions } from "../../hooks/useSettings";
import { useUserWorkspaces } from "../../hooks/useSettings";

/**
 * RoleRoute
 * ---------
 * Blocks access to a route unless the current user has the required role
 * in their active workspace.
 *
 * Props:
 *  - requiredRole : "Admin" | "Member" | "Viewer"
 *  - children     : ReactNode — the protected page
 *
 * Usage:
 *  <RoleRoute requiredRole="Admin">
 *    <TeamPage />
 *  </RoleRoute>
 */
export default function RoleRoute({ requiredRole = "Admin", children }) {
  // Wait for workspaces to finish loading before making an access decision
  const { isLoading } = useUserWorkspaces();
  const { role, isAdmin } = useWorkspacePermissions();

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="w-full max-w-md px-6">
          <LoadingSkeleton count={2} className="h-24" />
        </div>
      </div>
    );
  }

  // Role hierarchy: Owner > Admin > Member > Viewer
  const ROLE_RANK = { Owner: 4, Admin: 3, Member: 2, Viewer: 1 };
  const userRank = ROLE_RANK[role] ?? 0;
  const requiredRank = ROLE_RANK[requiredRole] ?? 3;

  if (userRank < requiredRank) {
    const requiredTitle = requiredRole === "Owner" ? "Workspace Owner Access Required" : "Admin Access Required";
    const requiredDesc = requiredRole === "Owner" 
      ? `You are signed in as ${role || "a Member"}. Only the Workspace Owner can access Workspace Settings.`
      : `You are signed in as a ${role || "Member"}. Only Admins can access this section. Contact your workspace administrator for help.`;

    return (
      <AccessDeniedScreen
        title={requiredTitle}
        description={requiredDesc}
      />
    );
  }

  return children;
}
