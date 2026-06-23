import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { useCreateWorkspace } from "../../hooks/useSettings";
import { useAuth } from "../../context/AuthContext";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { Building2 } from "lucide-react";
import { useUIStore } from "../../store/useUIStore";

export default function CreateWorkspaceModal({ open, onOpenChange }) {
  const [name, setName] = useState("");
  const { user } = useAuth();
  const createMutation = useCreateWorkspace();
  const navigate = useNavigate();
  const setActiveWorkspaceId = useUIStore((state) => state.setActiveWorkspaceId);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    try {
      const payload = {
        name: name.trim(),
        owner_id: user.id,
        email: user.email,
        user_name: user.user_metadata?.full_name || user.email?.split("@")[0] || "User"
      };
      
      const newWorkspace = await createMutation.mutateAsync(payload);
      toast.success("Workspace created successfully");
      setActiveWorkspaceId(newWorkspace.id);
      setName("");
      onOpenChange(false);
    } catch (err) {
      if (err.message.includes("limit reached")) {
        toast.error("Workspace limit reached. Redirecting to upgrade...");
        onOpenChange(false);
        navigate("/billing");
      } else {
        toast.error(err.message || "Failed to create workspace");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Building2 className="text-primary" size={20} />
            Create Workspace
          </DialogTitle>
          <DialogDescription>
            Workspaces allow you to separate different projects, agents, and billing environments.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Workspace Name</label>
            <input
              autoFocus
              className="w-full border border-border rounded-xl p-3 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="e.g., Marketing Team"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              className="btn-primary"
              disabled={createMutation.isPending || !name.trim()}
            >
              {createMutation.isPending ? "Creating..." : "Create"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
