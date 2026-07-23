import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "../supabaseClient";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";

/**
 * usePermissionSync
 * -----------------
 * Listens for real-time changes to the current user's row(s) in
 * `workspace_members` via Supabase Realtime.
 *
 * When an Admin updates this user's role or permissions, the hook
 * immediately invalidates the `user_workspaces` query so the UI
 * reflects the new permissions without a page refresh.
 *
 * Must be mounted inside an authenticated context (AppShell).
 */
export function usePermissionSync() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  // Keep a ref to the channel so we can clean it up
  const channelRef = useRef(null);

  useEffect(() => {
    // Background polling sync fallback to ensure permissions stay up-to-date
    const interval = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ["user_workspaces"] });
      queryClient.invalidateQueries({ queryKey: ["workspace_members"] });
    }, 15000);

    return () => clearInterval(interval);
  }, [queryClient]);

  useEffect(() => {
    if (!user?.id) return;

    // Create a Supabase Realtime channel filtered to this user's rows only
    const channel = supabase
      .channel(`permission-sync-${user.id}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "workspace_members",
          // Only listen to rows where THIS user is the member
          filter: `user_id=eq.${user.id}`,
        },
        (payload) => {
          const oldData = payload.old;
          const newData = payload.new;

          const roleChanged = oldData.role !== newData.role;
          const permissionsChanged =
            JSON.stringify(oldData.permissions) !==
            JSON.stringify(newData.permissions);

          // Invalidate both queries so UI reflects changes immediately
          queryClient.invalidateQueries({ queryKey: ["user_workspaces"] });
          queryClient.invalidateQueries({ queryKey: ["workspace_members"] });

          // Show ONE toast — role message takes priority because permissions
          // are auto-updated together with role (Admin → all ON, others → all OFF)
          if (roleChanged) {
            const roleLabel = newData.role;
            const emoji =
              roleLabel === "Admin" ? "🛡️" : roleLabel === "Editor" ? "✏️" : "👁️";
            toast.info(
              `${emoji} Your role has been changed to "${roleLabel}" by an Admin.`,
              { duration: 6000 }
            );
          } else if (permissionsChanged) {
            // Only show permissions toast when ONLY permissions changed (not role)
            const perms = newData.permissions || {};
            const granted = Object.entries(perms)
              .filter(([, v]) => v)
              .map(([k]) => k.charAt(0).toUpperCase() + k.slice(1));
            const revoked = Object.entries(perms)
              .filter(([, v]) => !v)
              .map(([k]) => k.charAt(0).toUpperCase() + k.slice(1));

            const parts = [];
            if (granted.length) parts.push(`✅ Granted: ${granted.join(", ")}`);
            if (revoked.length) parts.push(`🚫 Revoked: ${revoked.join(", ")}`);

            toast.info(
              parts.length
                ? `Permissions updated — ${parts.join(" | ")}`
                : "Your workspace permissions were updated by an Admin.",
              { duration: 6000 }
            );
          }
        }
      )
      .subscribe();

    channelRef.current = channel;

    return () => {
      // Unsubscribe when the component unmounts or user changes
      supabase.removeChannel(channel);
      channelRef.current = null;
    };
  }, [user?.id, queryClient]);
}
