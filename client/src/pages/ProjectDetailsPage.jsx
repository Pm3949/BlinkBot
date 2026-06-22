import React, { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAgentProjects, useProjectSubAgents, useUpdateAgent, useDeleteAgent } from '../hooks/useAgents';
import { useUIStore } from '../store/useUIStore';
import { ArrowLeft, Settings, Database, Bot, Activity, Plus, Trash2 } from 'lucide-react';
import AgentSettingsModal from '../components/agents/AgentSettingsModal';
import ApiToolsModal from '../components/agents/ApiToolsModal';
import CreateAgentWizard from '../components/agents/CreateAgentWizard';
import { Switch } from '../components/ui/switch';
import { Button } from '../components/ui/button';
import { ReactFlow, MiniMap, Controls, Background, useNodesState, useEdgesState } from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';
import LoadingSkeleton from '../components/shared/LoadingSkeleton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { toast } from "sonner";

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    // node dimensions are approximately 260x140
    dagreGraph.setNode(node.id, { width: 280, height: 160 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    const newNode = { ...node };
    
    newNode.targetPosition = isHorizontal ? 'left' : 'top';
    newNode.sourcePosition = isHorizontal ? 'right' : 'bottom';

    // Shift node to top-left to align properly
    newNode.position = {
      x: nodeWithPosition.x - 280 / 2,
      y: nodeWithPosition.y - 160 / 2,
    };

    return newNode;
  });

  return { nodes: newNodes, edges };
};

export default function ProjectDetailsPage() {
  const { projectId } = useParams();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const [agentToEdit, setAgentToEdit] = useState(null);
  const [isToolsModalOpen, setIsToolsModalOpen] = useState(false);
  const [isCreateAgentOpen, setIsCreateAgentOpen] = useState(false);
  const [addingParentId, setAddingParentId] = useState(null);
  const [agentToDelete, setAgentToDelete] = useState(null);

  const handleAddAgent = (parentId = null) => {
    setAddingParentId(parentId);
    setIsCreateAgentOpen(true);
  };

  const { data: projects = [], isLoading: isProjectsLoading } = useAgentProjects(activeWorkspaceId);
  const { data: subAgents = [], isLoading: isAgentsLoading } = useProjectSubAgents(projectId);
  const updateAgentMutation = useUpdateAgent(activeWorkspaceId);
  const deleteAgentMutation = useDeleteAgent(activeWorkspaceId);

  const handleDeleteAgent = (agent) => {
    setAgentToDelete(agent);
  };

  const confirmDelete = async () => {
    if (!agentToDelete) return;
    try {
      await deleteAgentMutation.mutateAsync(agentToDelete.id);
      toast.success("Agent deleted successfully");
      setAgentToDelete(null);
    } catch (err) {
      toast.error("Failed to delete agent");
      console.error(err);
    }
  };

  const project = projects.find(p => p.id === projectId);

  const handleToggleActive = async (agent, currentStatus) => {
    try {
      await updateAgentMutation.mutateAsync({
        id: agent.id,
        payload: { is_active: !currentStatus }
      });
      toast.success(`Agent ${currentStatus ? 'deactivated' : 'activated'} successfully`);
    } catch (error) {
      toast.error("Failed to update agent status");
    }
  };

  const createInitialNodes = () => {
    if (!subAgents.length) return [];
    
    // Create a central Master Node
    const nodes = [
      {
        id: 'master',
        position: { x: 400, y: 50 },
        className: 'group',
        style: {
          backgroundColor: 'var(--card)',
          color: 'var(--text)',
          borderColor: 'var(--border)',
          borderRadius: '0.75rem',
          padding: '0.75rem',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          width: 192,
        },
        data: { 
          label: (
            <div className="flex flex-col items-center w-full relative">
              <div className="h-10 w-10 rounded-full bg-purple-500/20 flex items-center justify-center mb-2">
                <Bot className="text-purple-500" size={20} />
              </div>
              <strong className="text-sm font-semibold mb-2">Master Coordinator</strong>
              
              <button 
                onClick={(e) => { e.stopPropagation(); handleAddAgent(null); }}
                className="absolute -bottom-[28px] left-1/2 -translate-x-1/2 w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg nodrag z-50 cursor-pointer hover:bg-indigo-700 hover:scale-110"
                title="Add Root Agent"
              >
                <Plus size={18} />
              </button>
            </div>
          )
        },
        type: 'input',
      }
    ];

    subAgents.forEach((agent) => {
      nodes.push({
        id: agent.id,
        position: { x: 0, y: 0 },
        className: 'group',
        style: {
          backgroundColor: 'var(--card)',
          color: 'var(--text)',
          borderColor: 'var(--border)',
          borderRadius: '1rem',
          padding: '1rem',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          width: 280,
          height: 140,
        },
        data: {
          label: (
            <div className="flex flex-col h-full text-left">
              <div className="flex items-center justify-between mb-2 gap-2">
                <div className="flex items-center gap-2 overflow-hidden">
                  <div className={`h-2 w-2 rounded-full shrink-0 ${agent.is_active !== false ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
                  <strong className="text-[15px] font-bold truncate" title={agent.name}>{agent.name}</strong>
                </div>
                <div onClick={(e) => e.stopPropagation()} className="shrink-0 nodrag flex items-center gap-2">
                  <button
                    onClick={() => handleDeleteAgent(agent)}
                    disabled={deleteAgentMutation.isPending}
                    className="text-muted-foreground hover:text-red-500 transition-colors"
                    title="Delete Agent"
                  >
                    <Trash2 size={15} />
                  </button>
                  <Switch
                    checked={agent.is_active !== false}
                    disabled={updateAgentMutation.isPending}
                    onCheckedChange={() => handleToggleActive(agent, agent.is_active !== false)}
                  />
                </div>
              </div>
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-auto flex items-center gap-1">
                <Activity size={10} /> {agent.llm_model}
              </span>
              <div className="flex gap-2 mt-4 pt-3 border-t border-border/50">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setAgentToEdit(agent);
                  }}
                  className="flex items-center justify-center gap-1.5 p-2 rounded-lg flex-1 transition hover:bg-primary hover:text-primary-foreground bg-muted text-muted-foreground font-medium text-xs"
                  title="Settings"
                >
                  <Settings size={14} /> Settings
                </button>
                <Link
                  to="/knowledge"
                  className="flex items-center justify-center gap-1.5 p-2 rounded-lg flex-1 transition hover:bg-primary hover:text-primary-foreground bg-muted text-muted-foreground font-medium text-xs"
                  title="Knowledge Base"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Database size={14} /> Knowledge
                </Link>
              </div>
              
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleAddAgent(agent.id);
                }}
                className="absolute -bottom-[28px] left-1/2 -translate-x-1/2 w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg nodrag z-50 cursor-pointer hover:bg-indigo-700 hover:scale-110"
                title="Add Sub-Agent"
              >
                <Plus size={18} />
              </button>
            </div>
          )
        },
      });
    });

    return nodes;
  };

  const createInitialEdges = () => {
    if (!subAgents.length) return [];
    
    // First, connect any top-level agents (no parent) to the master node
    const rootEdges = subAgents
      .filter(agent => !agent.parent_agent_id)
      .map(agent => ({
        id: `e-master-${agent.id}`,
        source: 'master',
        target: agent.id,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#a855f7', strokeWidth: 2 }
      }));

    // Then, use the exact dynamic logic for hierarchical edges
    const dynamicEdges = subAgents
      .filter(agent => agent.parent_agent_id) // Only create edges if a parent exists
      .map(agent => ({
        id: `e-${agent.parent_agent_id}-${agent.id}`,
        source: agent.parent_agent_id,
        target: agent.id,
        type: 'smoothstep', // Using smoothstep as requested
        animated: true,
        style: { stroke: '#a855f7', strokeWidth: 2 }
      }));

    return [...rootEdges, ...dynamicEdges];
  };

  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    if (!subAgents.length) return { nodes: [], edges: [] };
    const rawNodes = createInitialNodes();
    const rawEdges = createInitialEdges();
    return getLayoutedElements(rawNodes, rawEdges, 'TB');
  }, [subAgents, updateAgentMutation.isPending]);

  if (isProjectsLoading || isAgentsLoading) {
    return <div className="p-10"><LoadingSkeleton /></div>;
  }

  if (!project) {
    return <div className="p-10 text-center">Project not found.</div>;
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/studio" className="p-2 bg-muted hover:bg-muted/80 text-foreground rounded-xl transition">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
              {project.name}
              <span className="px-3 py-1 rounded-full bg-purple-100 text-purple-700 text-[12px] font-bold uppercase tracking-wider">Network</span>
            </h1>
            <p className="text-muted-foreground mt-1 text-sm">{project.description}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setIsToolsModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 transition shadow-sm"
          >
            API Tools Manager
          </button>
        </div>
      </div>

      <div className="flex-1 bg-background rounded-2xl border border-border overflow-hidden relative">
        {subAgents.length > 0 ? (
          <ReactFlow 
            nodes={layoutedNodes} 
            edges={layoutedEdges}
            fitView
            attributionPosition="bottom-right"
            nodesDraggable={true}
            colorMode="system"
          >
            <Background gap={16} />
            <Controls />
            <MiniMap 
              nodeColor={(node) => {
                if (node.id === 'master') return '#e9d5ff';
                return '#fff';
              }}
              maskColor="rgba(0, 0, 0, 0.1)"
            />
          </ReactFlow>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            No sub-agents found in this network.
          </div>
        )}
      </div>

      {agentToEdit && (
        <AgentSettingsModal agent={agentToEdit} onClose={() => setAgentToEdit(null)} />
      )}
      
      {isToolsModalOpen && (
        <ApiToolsModal project={project} onClose={() => setIsToolsModalOpen(false)} />
      )}
      {isCreateAgentOpen && (
        <CreateAgentWizard 
          projectId={projectId}
          parentAgentId={addingParentId}
          onClose={() => setIsCreateAgentOpen(false)}
        />
      )}

      <Dialog open={!!agentToDelete} onOpenChange={() => setAgentToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Sub-Agent</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the agent "{agentToDelete?.name}"?
              This will permanently delete this agent, ALL of its sub-agents, their configurations, vectorized documents, and chat sessions. This action cannot be undone.
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
              {deleteAgentMutation.isPending ? "Deleting..." : "Cascade Delete Permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
