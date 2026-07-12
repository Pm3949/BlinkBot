import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import {
  Bot,
  Plus,
  MessageSquare,
  Database,
  MoreHorizontal,
  Trash2,
  Settings,
  Network,
  ArrowLeft,
  Wand2,
  FlaskConical,
  Zap,
  Sparkles,
  Clock,
  ChevronRight,
  Power,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { useAgents, useDeleteAgent, useAgentProjects, useDeleteAgentProject, useUpdateAgent, useCreateAgentProject } from "../hooks/useAgents";
import { useWorkspacePermissions } from "../hooks/useSettings";
import EmptyState from "../components/shared/EmptyState";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";

import AgentBuilder from "../components/AgentBuilder";
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
import { Switch } from "../components/ui/switch";

function formatCreatedAt(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.4, ease: "easeOut" },
  }),
};

export default function StudioPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const setCreateAgentWizardOpen = useUIStore((state) => state.setCreateAgentWizardOpen);
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);

  const [openDropdownId, setOpenDropdownId] = useState(null);
  const [agentToDelete, setAgentToDelete] = useState(null);
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [agentToEdit, setAgentToEdit] = useState(null);
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("all");
  const [deleteAgentConfirmText, setDeleteAgentConfirmText] = useState("");
  const [deleteProjectConfirmText, setDeleteProjectConfirmText] = useState("");

  const [isNetworkDialogOpen, setIsNetworkDialogOpen] = useState(false);
  const [networkMode, setNetworkMode] = useState(null);
  const [networkForm, setNetworkForm] = useState({ name: "", description: "" });

  const deleteAgentMutation = useDeleteAgent(activeWorkspaceId);
  const updateAgentMutation = useUpdateAgent(activeWorkspaceId);
  const deleteProjectMutation = useDeleteAgentProject(activeWorkspaceId);
  const createProjectMutation = useCreateAgentProject(activeWorkspaceId);
  const { canManageAgents } = useWorkspacePermissions();

  const handleCreateManualNetwork = async (e) => {
    e.preventDefault();
    if (!networkForm.name.trim()) return toast.error("Network name is required");
    try {
      const res = await createProjectMutation.mutateAsync({
        name: networkForm.name,
        description: networkForm.description,
        workspace_id: activeWorkspaceId,
      });
      toast.success("Network created successfully");
      setIsNetworkDialogOpen(false);
      setNetworkForm({ name: "", description: "" });
      window.location.href = `/studio/project/${res.id}`;
    } catch {
      toast.error("Failed to create network");
    }
  };

  const handleToggleActive = async (agent) => {
    try {
      const currentStatus = agent.is_active !== false;
      await updateAgentMutation.mutateAsync({ id: agent.id, payload: { is_active: !currentStatus } });
      toast.success(`Agent ${currentStatus ? "deactivated" : "activated"}`);
    } catch {
      toast.error("Failed to update agent status");
    }
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (!e.target.closest(".agent-dropdown-container")) setOpenDropdownId(null);
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  const confirmDelete = async () => {
    if (!agentToDelete) return;
    try {
      await deleteAgentMutation.mutateAsync(agentToDelete.id);
      toast.success("Agent deleted");
      setAgentToDelete(null);
      setDeleteAgentConfirmText("");
    } catch {
      toast.error("Failed to delete agent");
    }
  };

  const confirmDeleteProject = async () => {
    if (!projectToDelete) return;
    try {
      await deleteProjectMutation.mutateAsync(projectToDelete.id);
      toast.success("Network deleted");
      setProjectToDelete(null);
      setDeleteProjectConfirmText("");
    } catch {
      toast.error("Failed to delete network");
    }
  };

  const { data: agents = [], isError: isAgentsError, isLoading: isAgentsLoading } = useAgents(activeWorkspaceId);
  const { data: projects = [], isError: isProjectsError, isLoading: isProjectsLoading } = useAgentProjects(activeWorkspaceId);

  const activeAgents = agents.filter((a) => a.is_active !== false);

  const filteredItems = () => {
    if (activeTab === "agents") return { agents, projects: [] };
    if (activeTab === "networks") return { agents: [], projects };
    return { agents, projects };
  };

  const { agents: visibleAgents, projects: visibleProjects } = filteredItems();
  const hasItems = agents.length > 0 || projects.length > 0;
  const hasError = isAgentsError || isProjectsError;

  if (isAgentsLoading || isProjectsLoading) {
    return (
      <div className="p-10">
        <LoadingSkeleton />
      </div>
    );
  }

  if (isBuilderOpen) {
    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
        <button
          onClick={() => setIsBuilderOpen(false)}
          className="mb-6 flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors font-medium"
        >
          <ArrowLeft size={16} /> Back to Studio
        </button>
        <AgentBuilder />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* ── Header ── */}
      <div className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-primary/10 via-background to-background p-8">
        {/* decorative glow */}
        <div className="pointer-events-none absolute -top-20 -right-20 w-72 h-72 rounded-full bg-primary/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-10 -left-10 w-48 h-48 rounded-full bg-primary/10 blur-2xl" />

        <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 ring-2 ring-primary/30">
              <FlaskConical className="text-primary" size={26} />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-foreground">Studio</h1>
              <p className="text-muted-foreground mt-0.5 text-sm">
                Build standalone agents or generate massive AI networks.
              </p>
            </div>
          </div>

          {canManageAgents && (
            <div className="flex items-center gap-3">
              <button
                onClick={() => setCreateAgentWizardOpen(true)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border bg-background/80 hover:bg-muted text-foreground font-medium text-sm transition-all"
              >
                <Plus size={16} />
                New Agent
              </button>
              <button
                onClick={() => { setIsNetworkDialogOpen(true); setNetworkMode(null); }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl btn-primary text-white font-medium text-sm transition-all shadow-lg shadow-primary/25"
              >
                <Plus size={16} />
                Create Network
              </button>
            </div>
          )}
        </div>

        {/* Quick stats */}
        <div className="relative z-10 mt-7 flex flex-wrap gap-6">
          <div className="flex items-center gap-2.5 text-sm">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15">
              <Bot size={14} className="text-primary" />
            </span>
            <span className="text-foreground font-semibold">{agents.length}</span>
            <span className="text-muted-foreground">Agents</span>
          </div>
          <div className="flex items-center gap-2.5 text-sm">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-violet-500/15">
              <Network size={14} className="text-violet-500" />
            </span>
            <span className="text-foreground font-semibold">{projects.length}</span>
            <span className="text-muted-foreground">Networks</span>
          </div>
          <div className="flex items-center gap-2.5 text-sm">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-green-500/15">
              <Zap size={14} className="text-green-500" />
            </span>
            <span className="text-foreground font-semibold">{activeAgents.length}</span>
            <span className="text-muted-foreground">Active</span>
          </div>
        </div>
      </div>

      {/* ── Tab Filter ── */}
      {hasItems && (
        <div className="flex items-center gap-1 rounded-xl border border-border bg-muted/40 p-1 w-fit">
          {[
            { key: "all", label: "All" },
            { key: "agents", label: "Agents" },
            { key: "networks", label: "Networks" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.key
                  ? "bg-primary text-white shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* ── Error Banner ── */}
      {hasError && (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-5 py-4 text-sm text-red-500">
          Unable to load studio items. Please try again.
        </div>
      )}

      {/* ── Empty State ── */}
      {!hasItems && !hasError && (
        <div className="flex flex-col items-center justify-center rounded-3xl border border-dashed border-border py-24 text-center">
          <div className="mb-5 flex h-20 w-20 items-center justify-center rounded-2xl bg-primary/10 ring-2 ring-primary/20">
            <Sparkles className="text-primary" size={32} />
          </div>
          <h2 className="text-xl font-bold text-foreground">Studio is empty</h2>
          <p className="mt-2 text-muted-foreground text-sm max-w-sm">
            Create your first standalone agent or let AI generate a full multi-agent network in seconds.
          </p>
          {canManageAgents && (
            <div className="mt-6 flex gap-3">
              <button
                onClick={() => setCreateAgentWizardOpen(true)}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-border hover:bg-muted font-medium text-sm transition-all"
              >
                <Plus size={16} /> New Agent
              </button>
              <button
                onClick={() => { setIsNetworkDialogOpen(true); setNetworkMode(null); }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl btn-primary text-white font-medium text-sm shadow-lg shadow-primary/20"
              >
                <Plus size={16} /> Create Network
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Grid ── */}
      {hasItems && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Network Cards */}
          <AnimatePresence>
            {visibleProjects.map((project, i) => (
              <motion.div
                key={`proj-${project.id}`}
                custom={i}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                className="group relative glass-card p-6 border-violet-500/20 hover:border-violet-500/40 transition-all"
              >
                {/* glow */}
                <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-violet-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="relative flex items-start justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-500/15 ring-1 ring-violet-500/30">
                    <Network className="text-violet-500" size={20} />
                  </div>
                  {canManageAgents && (
                    <div className="relative agent-dropdown-container">
                      <button
                        className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition"
                        onClick={(e) => {
                          e.preventDefault();
                          setOpenDropdownId(openDropdownId === project.id ? null : project.id);
                        }}
                      >
                        <MoreHorizontal size={16} />
                      </button>
                      {openDropdownId === project.id && (
                        <div className="absolute right-0 top-full mt-2 w-44 bg-card rounded-xl shadow-xl border border-border py-1 z-20">
                          <button
                            className="w-full text-left px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 flex items-center gap-2 transition"
                            onClick={(e) => { e.preventDefault(); setProjectToDelete(project); setOpenDropdownId(null); }}
                          >
                            <Trash2 size={14} /> Delete Network
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-4">
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-foreground">{project.name}</h3>
                    <span className="px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-500 text-[10px] font-bold uppercase tracking-wider">Network</span>
                  </div>
                  {project.description && (
                    <p className="mt-1.5 text-sm text-muted-foreground line-clamp-2">{project.description}</p>
                  )}
                </div>

                <div className="mt-5 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <span className="text-green-500 font-medium capitalize">{project.status}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground flex items-center gap-1"><Clock size={12} /> Created</span>
                    <span>{formatCreatedAt(project.created_at)}</span>
                  </div>
                </div>

                <div className="mt-5">
                  <Link
                    to={`/studio/project/${project.id}`}
                    className="flex items-center justify-center gap-2 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white font-medium text-sm transition"
                  >
                    Open Network <ChevronRight size={14} />
                  </Link>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Agent Cards */}
          <AnimatePresence>
            {visibleAgents.map((agent, i) => (
              <motion.div
                key={agent.id}
                custom={i + visibleProjects.length}
                variants={cardVariants}
                initial="hidden"
                animate="visible"
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                className="group relative glass-card p-6 hover:border-primary/40 transition-all"
              >
                {/* glow */}
                <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="relative flex items-start justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 ring-1 ring-primary/25">
                    <Bot className="text-primary" size={20} />
                  </div>

                  {canManageAgents && (
                    <div className="flex items-center gap-2 relative agent-dropdown-container">
                      <div
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                          agent.is_active !== false
                            ? "bg-green-500/15 text-green-500"
                            : "bg-muted text-muted-foreground"
                        }`}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Power size={10} />
                        <Switch
                          checked={agent.is_active !== false}
                          disabled={updateAgentMutation.isPending}
                          onCheckedChange={() => handleToggleActive(agent)}
                          className="scale-75 -my-0.5"
                        />
                      </div>
                      <button
                        className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition"
                        onClick={(e) => { e.preventDefault(); setOpenDropdownId(openDropdownId === agent.id ? null : agent.id); }}
                      >
                        <MoreHorizontal size={16} />
                      </button>
                      {openDropdownId === agent.id && (
                        <div className="absolute right-0 top-full mt-2 w-44 bg-card rounded-xl shadow-xl border border-border py-1 z-20">
                          <button
                            className="w-full text-left px-4 py-2 text-sm text-foreground hover:bg-muted flex items-center gap-2 transition"
                            onClick={(e) => { e.preventDefault(); navigate(`/agent/${agent.id}/settings`, { state: { agent } }); setOpenDropdownId(null); }}
                          >
                            <Settings size={14} /> Settings
                          </button>
                          <button
                            className="w-full text-left px-4 py-2 text-sm text-red-500 hover:bg-red-500/10 flex items-center gap-2 transition"
                            onClick={(e) => { e.preventDefault(); setAgentToDelete(agent); setOpenDropdownId(null); }}
                          >
                            <Trash2 size={14} /> Delete
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-4">
                  <h3 className="font-bold text-foreground">{agent.name}</h3>
                  {agent.description && (
                    <p className="mt-1.5 text-sm text-muted-foreground line-clamp-2">{agent.description}</p>
                  )}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="px-2.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium">{agent.provider}</span>
                  <span className="px-2.5 py-1 rounded-full bg-muted text-foreground text-xs font-medium">{agent.model}</span>
                </div>

                <div className="mt-4 space-y-2 text-sm border-t border-border pt-4">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Embedding</span>
                    <span className="truncate ml-4 text-right">{agent.embedding_model}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Chunking</span>
                    <span>{agent.chunk_strategy}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground flex items-center gap-1"><Clock size={12} /> Created</span>
                    <span>{formatCreatedAt(agent.created_at)}</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mt-5">
                  <button
                    onClick={(e) => { e.preventDefault(); navigate(`/agent/${agent.id}/settings`, { state: { agent } }); }}
                    className="flex items-center justify-center gap-1.5 py-2 rounded-xl border border-border hover:bg-muted text-sm font-medium transition"
                  >
                    <Settings size={14} /> Settings
                  </button>
                  <Link
                    to="/chat"
                    className="flex items-center justify-center gap-1.5 py-2 rounded-xl btn-primary text-white text-sm font-medium transition"
                  >
                    <MessageSquare size={14} /> Chat
                  </Link>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* ── Modals ── */}
      <Dialog open={!!agentToDelete} onOpenChange={(open) => {
        if (!open) {
          setAgentToDelete(null);
          setDeleteAgentConfirmText("");
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Agent</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>"{agentToDelete?.name}"</strong>? This will permanently remove the agent, its vectorized documents, and all chat history. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            <p className="text-sm font-medium mb-2">Please type <strong>{agentToDelete?.name}</strong> to confirm.</p>
            <input
              type="text"
              value={deleteAgentConfirmText}
              onChange={(e) => setDeleteAgentConfirmText(e.target.value)}
              placeholder={agentToDelete?.name}
              className="w-full border border-border rounded-lg p-2.5 bg-background focus:ring-2 focus:ring-red-500/50 focus:outline-none"
            />
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => { setAgentToDelete(null); setDeleteAgentConfirmText(""); }}>Cancel</Button>
            <Button 
              variant="destructive" 
              className="bg-red-600 hover:bg-red-700 text-white" 
              onClick={confirmDelete} 
              disabled={deleteAgentMutation.isPending || deleteAgentConfirmText !== agentToDelete?.name}
            >
              {deleteAgentMutation.isPending ? "Deleting..." : "Delete Permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!projectToDelete} onOpenChange={(open) => {
        if (!open) {
          setProjectToDelete(null);
          setDeleteProjectConfirmText("");
        }
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Agent Network</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>"{projectToDelete?.name}"</strong>? This will cascade-delete all sub-agents, tools, knowledge bases, and chats. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            <p className="text-sm font-medium mb-2">Please type <strong>{projectToDelete?.name}</strong> to confirm.</p>
            <input
              type="text"
              value={deleteProjectConfirmText}
              onChange={(e) => setDeleteProjectConfirmText(e.target.value)}
              placeholder={projectToDelete?.name}
              className="w-full border border-border rounded-lg p-2.5 bg-background focus:ring-2 focus:ring-red-500/50 focus:outline-none"
            />
          </div>
          <DialogFooter className="mt-4">
            <Button variant="outline" onClick={() => { setProjectToDelete(null); setDeleteProjectConfirmText(""); }}>Cancel</Button>
            <Button 
              variant="destructive" 
              className="bg-red-600 hover:bg-red-700 text-white" 
              onClick={confirmDeleteProject} 
              disabled={deleteProjectMutation.isPending || deleteProjectConfirmText !== projectToDelete?.name}
            >
              {deleteProjectMutation.isPending ? "Deleting..." : "Delete Network"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={isNetworkDialogOpen} onOpenChange={(open) => {
        setIsNetworkDialogOpen(open);
        if (!open) setNetworkMode(null);
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Create Agent Network</DialogTitle>
            <DialogDescription>
              Choose how you want to build your new agent network.
            </DialogDescription>
          </DialogHeader>

          {!networkMode ? (
            <div className="grid grid-cols-2 gap-4 py-4">
              <button 
                onClick={() => {
                  setIsNetworkDialogOpen(false);
                  setIsBuilderOpen(true);
                }}
                className="flex flex-col items-center justify-center p-6 border-2 border-primary/20 rounded-2xl hover:border-primary hover:bg-primary/5 transition-all text-center gap-3"
              >
                <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                  <Wand2 size={24} />
                </div>
                <div>
                  <h4 className="font-bold text-foreground mb-1">AI Generated</h4>
                  <p className="text-xs text-muted-foreground">Describe what you want and AI builds it.</p>
                </div>
              </button>

              <button 
                onClick={() => setNetworkMode("manual")}
                className="flex flex-col items-center justify-center p-6 border-2 border-border rounded-2xl hover:border-foreground/20 hover:bg-muted/50 transition-all text-center gap-3"
              >
                <div className="w-12 h-12 rounded-full bg-muted text-foreground flex items-center justify-center">
                  <Plus size={24} />
                </div>
                <div>
                  <h4 className="font-bold text-foreground mb-1">Blank Network</h4>
                  <p className="text-xs text-muted-foreground">Start from scratch and add agents manually.</p>
                </div>
              </button>
            </div>
          ) : (
            <form onSubmit={handleCreateManualNetwork} className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Network Name</label>
                <input 
                  autoFocus
                  required
                  value={networkForm.name}
                  onChange={e => setNetworkForm({...networkForm, name: e.target.value})}
                  className="w-full border border-border bg-background rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-primary/50"
                  placeholder="e.g. Sales Team"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Description <span className="text-muted-foreground font-normal">(Optional)</span></label>
                <textarea 
                  value={networkForm.description}
                  onChange={e => setNetworkForm({...networkForm, description: e.target.value})}
                  className="w-full border border-border bg-background rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-primary/50 resize-y"
                  rows={3}
                  placeholder="What is the purpose of this network?"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <Button type="button" variant="outline" onClick={() => setNetworkMode(null)}>
                  Back
                </Button>
                <Button type="submit" disabled={createProjectMutation.isPending} className="btn-primary">
                  {createProjectMutation.isPending ? "Creating..." : "Create Network"}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
