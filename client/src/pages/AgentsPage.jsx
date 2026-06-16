import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  Bot,
  Plus,
  MessageSquare,
  Database,
  MoreHorizontal,
  Trash2,
  Settings,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAgents, useDeleteAgent } from "../hooks/useAgents";
import { useWorkspacePermissions } from "../hooks/useSettings";
import EmptyState from "../components/shared/EmptyState";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";
import AgentSettingsModal from "../components/agents/AgentSettingsModal";
import { useUIStore } from "../store/useUIStore";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "../components/ui/dialog";
import { Button } from "../components/ui/button";

function formatCreatedAt(value) {
  if (!value) return "Not available";

  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

export default function AgentsPage() {
  const setCreateAgentWizardOpen = useUIStore(
    (state) => state.setCreateAgentWizardOpen,
  );
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);

  const [openDropdownId, setOpenDropdownId] = useState(null);
  const [agentToDelete, setAgentToDelete] = useState(null);
  const [agentToEdit, setAgentToEdit] = useState(null);
  const deleteAgentMutation = useDeleteAgent(activeWorkspaceId);
  const { canManageAgents } = useWorkspacePermissions();


  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest('.agent-dropdown-container')) {
        setOpenDropdownId(null);
      }
    };
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const confirmDelete = async () => {
    if (!agentToDelete) return;
    try {
      await deleteAgentMutation.mutateAsync(agentToDelete.id);
      toast.success("Agent deleted successfully");
      setAgentToDelete(null);
    } catch (error) {
      toast.error("Failed to delete agent");
    }
  };

  const {
    data: agents = [],
    isError,
    isLoading,
    error,
  } = useAgents(activeWorkspaceId);

  if (isLoading) {
    return (
      <div className="p-10">
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-10">
        <div>
          <h1 className="text-4xl font-bold text-foreground">AI Agents</h1>

          <p className="text-muted-foreground mt-2">
            Build and manage custom RAG assistants.
          </p>
        </div>

        {canManageAgents && (
          <button onClick={() => setCreateAgentWizardOpen(true)}
            className="
            flex
            items-center
            gap-2
            px-5
            py-3
            rounded-2xl
            btn-primary
            text-white
            transition-all
          "
          >
            <Plus size={18} />
            Create Agent
          </button>
        )}
      </div>

      {isError && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
          {error?.message ||
            "Unable to load agents. Please try again."}
        </div>
      )}

      {agents.length === 0 && !isError ? (
        <EmptyState
          title="No agents yet"
          description="Create your first AI agent to connect models, instructions, and knowledge settings."
          action={
            canManageAgents && (
              <button onClick={() => setCreateAgentWizardOpen(true)}
                className="
                flex
                items-center
                gap-2
                px-5
                py-3
                rounded-2xl
                btn-primary
                text-white
                transition-all
              "
              >
                <Plus size={18} />
                Create Agent
              </button>
            )
          }
        />
      ) : (
      <div className="grid lg:grid-cols-3 gap-6">
        {agents.map((agent) => (
          <motion.div
            key={agent.id}
            whileHover={{
              y: -4,
            }}
            className="
              glass-card
              p-6
            "
          >
            <div className="flex items-start justify-between">
              <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Bot className="text-primary" />
              </div>

              {canManageAgents && (
                <div className="relative agent-dropdown-container">
                  <button
                    className="p-2 rounded-xl hover:bg-muted"
                    onClick={(e) => {
                      e.preventDefault();
                      setOpenDropdownId(openDropdownId === agent.id ? null : agent.id);
                    }}
                  >
                    <MoreHorizontal size={18} />
                  </button>
                  {openDropdownId === agent.id && (
                    <div className="absolute right-0 top-full mt-2 w-48 bg-card rounded-xl shadow-lg border border-border py-1 z-10 overflow-hidden">
                      <button
                        className="w-full text-left px-4 py-2 text-sm text-foreground hover:bg-muted flex items-center gap-2"
                        onClick={(e) => {
                          e.preventDefault();
                          setAgentToEdit(agent);
                          setOpenDropdownId(null);
                        }}
                      >
                        <Settings size={16} /> Agent Settings
                      </button>
                      <button
                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-500/10 flex items-center gap-2"
                        onClick={(e) => {
                          e.preventDefault();
                          setAgentToDelete(agent);
                          setOpenDropdownId(null);
                        }}
                      >
                        <Trash2 size={16} /> Delete Agent
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            <h3 className="font-semibold text-lg mt-5">
              {agent.name}
            </h3>

            {agent.description && (
              <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                {agent.description}
              </p>
            )}

            <div className="flex flex-wrap gap-2 mt-4">
              <span className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">
                {agent.provider}
              </span>

              <span className="px-3 py-1 rounded-full bg-muted text-foreground text-xs font-medium">
                {agent.model}
              </span>
            </div>

            <div className="mt-5 space-y-2">
              <div className="flex justify-between gap-4 text-sm">
                <span className="text-muted-foreground">Embedding</span>

                <span className="text-right">
                  {agent.embedding_model}
                </span>
              </div>

              <div className="flex justify-between gap-4 text-sm">
                <span className="text-muted-foreground">Chunking</span>

                <span className="text-right">
                  {agent.chunk_strategy}
                </span>
              </div>

              <div className="flex justify-between gap-4 text-sm">
                <span className="text-muted-foreground">Created</span>

                <span className="text-right">
                  {formatCreatedAt(agent.created_at)}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 mt-6">
              <Link
                to="/knowledge"
                className="
                  flex
                  items-center
                  justify-center
                  gap-2
                  py-3
                  rounded-2xl
                  border
                  border-border
                  hover:bg-muted
                "
              >
                <Database size={16} />
                Knowledge
              </Link>

              <Link
                to="/chat"
                className="
                  flex
                  items-center
                  justify-center
                  gap-2
                  py-3
                  rounded-2xl
                  btn-primary
                  text-white
                "
              >
                <MessageSquare size={16} />
                Chat
              </Link>
            </div>
          </motion.div>
        ))}
      </div>
      )}

      {agentToEdit && (
        <AgentSettingsModal agent={agentToEdit} onClose={() => setAgentToEdit(null)} />
      )}

      <Dialog open={!!agentToDelete} onOpenChange={() => setAgentToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Agent</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the agent "{agentToDelete?.name}"?
              This will permanently delete the agent, its settings, all vectorized documents, chat sessions, and chat history. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => setAgentToDelete(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={confirmDelete}
              disabled={deleteAgentMutation.isPending}
            >
              {deleteAgentMutation.isPending ? "Deleting..." : "Delete Permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
