import React, { useState, useEffect } from "react";
import {
  Building2,
  Key,
  Shield,
  Trash2,
  Save,
  Users,
  ExternalLink
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { usePrimaryWorkspace, useUpdateWorkspace } from "../hooks/useSettings";
import { toast } from "sonner";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";

export default function SettingsPage() {
  const navigate = useNavigate();
  const { data: workspace, isLoading: loadingWorkspace } = usePrimaryWorkspace();
  const updateWorkspaceMutation = useUpdateWorkspace();

  const [workspaceName, setWorkspaceName] = useState("");

  useEffect(() => {
    if (workspace?.name) setWorkspaceName(workspace.name);
  }, [workspace]);

  const handleSaveWorkspace = async () => {
    if (!workspace?.id) return;
    try {
      await updateWorkspaceMutation.mutateAsync({ id: workspace.id, name: workspaceName });
      toast.success("Workspace updated successfully");
    } catch (e) {
      toast.error("Failed to update workspace");
    }
  };

  if (loadingWorkspace) {
    return <LoadingSkeleton count={3} className="h-40 mb-4" />;
  }

  return (
    <div className="max-w-5xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">
          Workspace Settings
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage workspace identity, team access policies, and workspace management.
        </p>
      </div>

      <div className="space-y-6">
        {/* Workspace Identity */}
        <div className="glass-card p-8">
          <div className="flex items-center gap-3 mb-6">
            <Building2 className="text-primary" />
            <h2 className="text-xl font-semibold text-foreground">
              Workspace Identity
            </h2>
          </div>

          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-sm font-semibold mb-2">Workspace Name</label>
              <input
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="w-full border border-border rounded-2xl p-4 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                placeholder="Workspace Name"
              />
            </div>
            <button 
              type="button"
              onClick={handleSaveWorkspace}
              disabled={updateWorkspaceMutation.isPending}
              className="px-6 py-3 btn-primary rounded-xl flex items-center gap-2 font-semibold disabled:opacity-50"
            >
              <Save size={16} />
              {updateWorkspaceMutation.isPending ? "Saving..." : "Save Workspace"}
            </button>
          </div>
        </div>

        {/* Quick Links Hub Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Team Management Banner */}
          <div className="glass-card p-6 flex flex-col justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-2xl bg-blue-500/10 text-blue-500 flex items-center justify-center font-bold shrink-0">
                <Users size={20} />
              </div>
              <div>
                <h3 className="font-bold text-base text-foreground">Team Access & Granular Permissions</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Invite team members, assign Roles (Owner, Admin, Editor), and toggle Studio & Models permissions.
                </p>
              </div>
            </div>
            <button 
              type="button"
              onClick={() => navigate("/team")}
              className="px-4 py-2.5 bg-muted hover:bg-muted/80 text-foreground transition-colors rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 self-start"
            >
              Manage Workspace Team Access <ExternalLink size={14} />
            </button>
          </div>

          {/* AI Model Credentials Link Banner */}
          <div className="glass-card p-6 flex flex-col justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-2xl bg-amber-500/10 text-amber-500 flex items-center justify-center font-bold shrink-0">
                <Key size={20} />
              </div>
              <div>
                <h3 className="font-bold text-base text-foreground">AI Model & Provider API Credentials</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Manage AES-256 encrypted API keys for OpenAI, Groq, OpenRouter, Anthropic, Gemini & HuggingFace.
                </p>
              </div>
            </div>
            <button 
              type="button"
              onClick={() => navigate("/models")}
              className="px-4 py-2.5 bg-muted hover:bg-muted/80 text-foreground transition-colors rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 self-start"
            >
              Manage Credentials in Models Hub <ExternalLink size={14} />
            </button>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-red-50 border border-red-200 rounded-3xl p-8 dark:bg-red-500/10 dark:border-red-500/30">
          <div className="flex items-center gap-3 mb-4">
            <Trash2 className="text-red-600" />
            <h2 className="text-xl font-semibold text-red-600">
              Workspace Danger Zone
            </h2>
          </div>

          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <div className="font-semibold text-foreground">
                Delete Workspace
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Permanently remove this workspace and all associated Agents, Chatbots, and Documents. This action cannot be undone.
              </div>
            </div>
            <button type="button" className="px-5 py-2.5 rounded-xl bg-red-600 text-white hover:bg-red-700 text-xs font-semibold shrink-0">
              Delete Workspace
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
