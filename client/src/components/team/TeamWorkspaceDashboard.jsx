import React, { useState } from "react";
import { Search, Plus, Crown, Check, Lock } from "lucide-react";
import { Button } from "../ui/button";
import { Switch } from "../ui/switch";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger
} from "../ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../ui/select";
import {
  useWorkspaceMembers,
  useInviteMember,
  useUpdateMemberRole,
  useUpdateMemberPermissions,
  useRemoveMember
} from "../../hooks/useTeam";
import { useAuth } from "../../context/AuthContext";
import { toast } from "sonner";
import LoadingSkeleton from "../shared/LoadingSkeleton";
import { useUserWorkspaces } from "../../hooks/useSettings";
import { useUIStore } from "../../store/useUIStore";

export default function TeamWorkspaceDashboard() {
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("Editor");
  const [loadingToggles, setLoadingToggles] = useState({});

  const { user: currentUser } = useAuth();
  const { data: members = [], isLoading } = useWorkspaceMembers();
  const inviteMutation = useInviteMember();
  const updateRoleMutation = useUpdateMemberRole();
  const updatePermissionsMutation = useUpdateMemberPermissions();
  const removeMutation = useRemoveMember();

  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const { data: workspaces = [] } = useUserWorkspaces();
  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId);

  // Derive current user's capabilities from their own member row
  const currentMember = members.find((m) => m.user_id === currentUser?.id);
  const isCurrentUserOwner = activeWorkspace?.owner_id === currentUser?.id;
  const isCurrentUserAdmin = isCurrentUserOwner || currentMember?.role?.toLowerCase() === "admin";

  const getInitials = (name) => {
    if (!name) return "??";
    return name.split(" ").map((n) => n[0]).join("").toUpperCase().substring(0, 2);
  };

  const handlePermissionToggle = async (memberId, currentPermissions, field) => {
    const key = `${memberId}-${field}`;
    setLoadingToggles((prev) => ({ ...prev, [key]: true }));

    const newPermissions = {
      ...currentPermissions,
      [field]: !currentPermissions[field]
    };
    try {
      await updatePermissionsMutation.mutateAsync({ memberId, permissions: newPermissions });
      toast.success("Permissions updated");
    } catch (e) {
      toast.error("Failed to update permissions");
    } finally {
      setLoadingToggles((prev) => {
        const next = { ...prev };
        delete next[key];
        return next;
      });
    }
  };

  const handleRoleChange = async (memberId, newRole) => {
    try {
      await updateRoleMutation.mutateAsync({ memberId, role: newRole });
      toast.success("Role updated");
    } catch (e) {
      toast.error("Failed to update role");
    }
  };

  const handleRemove = async (memberId) => {
    try {
      await removeMutation.mutateAsync(memberId);
      toast.success("Member removed");
    } catch (e) {
      toast.error("Failed to remove member");
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail) return;
    try {
      await inviteMutation.mutateAsync({ email: inviteEmail, role: inviteRole });
      toast.success("Invitation sent successfully!");
      setIsInviteOpen(false);
      setInviteEmail("");
      setInviteRole("Editor");
    } catch (e) {
      toast.error(e.message || "Failed to send invitation");
    }
  };

  if (isLoading) {
    return <LoadingSkeleton count={3} className="h-20 mb-4" />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Workspace Access Control</h1>
          <p className="text-sm text-muted-foreground mt-1">Manage your team members and their granular permissions.</p>
        </div>
        <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
          <DialogTrigger asChild>
            <Button className="btn-primary shadow-sm">
              <Plus className="mr-2 h-4 w-4" />
              Invite Member
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Invite a new member</DialogTitle>
              <DialogDescription>
                Send an invitation to join this workspace. They will receive an email to set up their account.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="flex flex-col space-y-1.5">
                <label htmlFor="email" className="text-sm font-medium text-foreground">Email address</label>
                <input
                  id="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="name@example.com"
                  className="flex h-10 w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
                />
              </div>
              <div className="flex flex-col space-y-1.5">
                <label className="text-sm font-medium text-foreground">Default Role</label>
                <Select value={inviteRole} onValueChange={setInviteRole}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Admin">Admin</SelectItem>
                    <SelectItem value="Editor">Editor</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsInviteOpen(false)}>Cancel</Button>
              <Button onClick={handleInvite} disabled={inviteMutation.isPending} className="btn-primary">
                {inviteMutation.isPending ? "Sending..." : "Send Invite"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Access Matrix Table Content */}
      <div className="glass-card overflow-hidden">
        {/* Table Header / Toolbar */}
        <div className="p-5 border-b border-border flex items-center justify-between bg-transparent">
          <div className="relative w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search members..."
              className="pl-9 h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground text-foreground focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
            />
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-muted/50 border-b border-border">
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Member</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Role</th>
                <th className="px-6 py-4 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Permissions
                  <div className="flex items-center space-x-6 mt-1 text-muted-foreground/70 text-[10px]">
                    <span className="w-12 text-center">Agents</span>
                    <span className="w-12 text-center">Databases</span>
                  </div>
                </th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border bg-transparent">
              {members.map((member) => (
                <tr
                  key={member.id}
                  className={`hover:bg-muted/30 transition-colors ${
                    member.isOwner ? "bg-primary/5" : ""
                  }`}
                >
                  {/* Member info */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-4">
                      <div className="relative">
                        <Avatar>
                          <AvatarImage src={`https://i.pravatar.cc/150?u=${member.email}`} />
                          <AvatarFallback className="bg-primary/10 text-primary font-medium">
                            {getInitials(member.name || member.email)}
                          </AvatarFallback>
                        </Avatar>
                        {member.isOwner && (
                          <span className="absolute -top-1 -right-1 bg-amber-400 rounded-full p-0.5">
                            <Crown className="w-2.5 h-2.5 text-white" />
                          </span>
                        )}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-foreground">
                            {member.name || member.email}
                          </p>
                          {member.isOwner && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-400/15 text-amber-500 border border-amber-400/30">
                              <Crown className="w-2.5 h-2.5" />
                              Owner
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{member.email}</p>
                      </div>
                    </div>
                  </td>

                  {/* Role column */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="w-36">
                      {activeWorkspace?.owner_id === member.user_id ? (
                        // Owner row — always fixed
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-400/10 text-amber-500 border border-amber-400/20">
                          <Crown className="w-3 h-3" />
                          Owner
                        </span>
                      ) : !member.user_id ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">
                          Pending
                        </span>
                      ) : isCurrentUserAdmin ? (
                        // Admin/Owner can change roles
                        <Select
                          value={member.role}
                          onValueChange={(val) => handleRoleChange(member.id, val)}
                        >
                          <SelectTrigger className="h-9">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Admin">Admin</SelectItem>
                            <SelectItem value="Editor">Editor</SelectItem>
                          </SelectContent>
                        </Select>
                      ) : (
                        // Others — role is read-only for them
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                          member.role === "Admin"
                            ? "bg-primary/10 text-primary border-primary/20"
                            : member.role === "Editor"
                            ? "bg-blue-500/10 text-blue-500 border-blue-500/20"
                            : "bg-muted text-muted-foreground border-border"
                        }`}>
                          <Lock className="w-3 h-3" />
                          {member.role}
                        </span>
                      )}
                    </div>
                  </td>

                  {/* Permissions column */}
                  <td className="px-6 py-4 whitespace-nowrap">
                    {member.isOwner || member.role === "Admin" ? (
                      // Owner / Admin — full access locked checkmarks
                      <div className="flex items-center space-x-6">
                        {["agents", "database"].map((perm) => (
                          <div key={perm} className="w-12 flex justify-center">
                            <span
                              title={member.isOwner ? "Owner has full access" : "Admin has full access"}
                              className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/15 text-primary"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : isCurrentUserAdmin ? (
                      // Current user is Admin/Owner → can toggle permissions of non-admin members
                      <div className="flex items-center space-x-6">
                        <div className="w-12 flex justify-center">
                          <Switch
                            checked={member.permissions?.agents || false}
                            disabled={loadingToggles[`${member.id}-agents`]}
                            onCheckedChange={() =>
                              handlePermissionToggle(member.id, member.permissions || {}, "agents")
                            }
                          />
                        </div>
                        <div className="w-12 flex justify-center">
                          <Switch
                            checked={member.permissions?.database || false}
                            disabled={loadingToggles[`${member.id}-database`]}
                            onCheckedChange={() =>
                              handlePermissionToggle(member.id, member.permissions || {}, "database")
                            }
                          />
                        </div>
                      </div>
                    ) : (
                      // Current user is not Admin — show read-only permission dots
                      <div className="flex items-center space-x-6">
                        {["agents", "database"].map((perm) => (
                          <div key={perm} className="w-12 flex justify-center">
                            <span
                              className={`w-2.5 h-2.5 rounded-full ${
                                member.permissions?.[perm]
                                  ? "bg-primary"
                                  : "bg-muted-foreground/30"
                              }`}
                              title={member.permissions?.[perm] ? "Enabled" : "Disabled"}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </td>

                  {/* Actions column */}
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    {activeWorkspace?.owner_id === member.user_id ? (
                      <span className="text-muted-foreground text-xs font-semibold mr-4">Owner (Cannot Remove)</span>
                    ) : isCurrentUserAdmin ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveMember(member.id)}
                        className="text-muted-foreground hover:text-red-600 hover:bg-red-500/10"
                      >
                        Remove
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
              {members.length === 0 && (
                <tr>
                  <td colSpan="4" className="px-6 py-8 text-center text-sm text-muted-foreground">
                    No team members found in this workspace.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
