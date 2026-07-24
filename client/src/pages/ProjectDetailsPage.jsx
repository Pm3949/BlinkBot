import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAgentProjects, useProjectSubAgents, useUpdateAgent, useDeleteAgent } from '../hooks/useAgents';
import { useSandboxChat } from '../hooks/useSandboxChat';
import { useUIStore } from '../store/useUIStore';
import { ArrowLeft, Settings, Database, Bot, Activity, Plus, Trash2, MessagesSquare } from 'lucide-react';
import CreateAgentWizard from '../components/agents/CreateAgentWizard';
import StudioSandboxChat from '../components/chat/StudioSandboxChat';
import TracePanel from '../components/chat/TracePanel';
import { Switch } from '../components/ui/switch';
import { Button } from '../components/ui/button';
import { ReactFlow, MiniMap, Controls, Background, useNodesState, useEdgesState, addEdge, Handle, Position } from '@xyflow/react';

const MasterNode = ({ data }) => (
  <>
    {data.label}
    <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-purple-500 border-2 border-background" />
  </>
);

const AgentNode = ({ data }) => {
  return (
    <>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-indigo-500 border-2 border-background" />
      <div className={`transition-all duration-500 relative rounded-xl ${data.isActiveRoute ? 'scale-[1.03] z-10' : ''}`}>
        {data.isActiveRoute && (
          <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-purple-500 via-indigo-500 to-purple-500 opacity-50 blur-xl animate-pulse -z-10" />
        )}
        <div className={`relative bg-card border border-border p-3 rounded-xl transition-all duration-500 ${data.isActiveRoute ? 'ring-2 ring-purple-500 ring-offset-4 ring-offset-background shadow-[0_0_40px_rgba(168,85,247,0.4)] border-transparent' : ''}`}>
          {data.label}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-indigo-500 border-2 border-background" />
    </>
  );
};

const nodeTypes = {
  masterNode: MasterNode,
  agentNode: AgentNode,
};
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
    dagreGraph.setNode(node.id, { width: 320, height: 160 });
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
      x: nodeWithPosition.x - 320 / 2,
      y: nodeWithPosition.y - 160 / 2,
    };

    return newNode;
  });

  return { nodes: newNodes, edges };
};

const getBoundaryTags = (agent) => {
  return [];
};

export default function ProjectDetailsPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const [agentToEdit, setAgentToEdit] = useState(null);
  const [isCreateAgentOpen, setIsCreateAgentOpen] = useState(false);
  const [addingParentId, setAddingParentId] = useState(null);
  const [agentToDelete, setAgentToDelete] = useState(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [isSandboxOpen, setIsSandboxOpen] = useState(false);
  const [activeRoutingAgentId, setActiveRoutingAgentId] = useState(null);
  const [chatLanguage, setChatLanguage] = useState("en");

  const {
    messages,
    loading,
    sendMessage,
    clearSandbox
  } = useSandboxChat();

  useEffect(() => {
    const handleRoutingDecision = (e) => {
      setActiveRoutingAgentId(e.detail.agent_id);
    };
    const handleStreamEnd = () => {
      setTimeout(() => setActiveRoutingAgentId(null), 1000); // Wait a second before clearing
    };
    
    window.addEventListener('agent_routing_decision', handleRoutingDecision);
    window.addEventListener('agent_stream_end', handleStreamEnd);
    return () => {
      window.removeEventListener('agent_routing_decision', handleRoutingDecision);
      window.removeEventListener('agent_stream_end', handleStreamEnd);
    };
  }, []);

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
    
    const nodes = [];
    subAgents.forEach((agent) => {
      const isActiveRoute = activeRoutingAgentId === agent.id;
      nodes.push({
        id: agent.id,
        type: agent.name === 'Network Manager' ? 'masterNode' : 'agentNode',
        position: { x: 0, y: 0 },
        className: 'group',
        style: agent.name === 'Network Manager' ? {
          backgroundColor: 'var(--card)',
          color: 'var(--text)',
          borderColor: '#a855f7',
          borderWidth: '2px',
          borderRadius: '0.75rem',
          padding: '0.75rem',
          width: 320,
        } : {
          width: 320,
          border: 'none',
          background: 'transparent',
        },
        data: {
          isActiveRoute,
          label: (
            <div className="flex flex-col h-full text-left">
              <div className="flex items-center justify-between mb-2 gap-2">
                <div className="flex items-center gap-2 overflow-hidden">
                  <div className={`h-2 w-2 rounded-full shrink-0 ${agent.is_active !== false ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
                  <strong className="text-[15px] font-bold truncate" title={agent.name}>{agent.name}</strong>
                </div>
                <div onClick={(e) => e.stopPropagation()} className="shrink-0 nodrag flex items-center gap-2">
                  {!['Network Manager', 'General Assistant'].includes(agent.name) && (
                    <button
                      onClick={() => handleDeleteAgent(agent)}
                      disabled={deleteAgentMutation.isPending}
                      className="text-muted-foreground hover:text-red-500 transition-colors"
                      title="Delete Agent"
                    >
                      <Trash2 size={15} />
                    </button>
                  )}
                  <Switch
                    checked={agent.is_active !== false}
                    disabled={updateAgentMutation.isPending}
                    onCheckedChange={() => handleToggleActive(agent, agent.is_active !== false)}
                  />
                </div>
              </div>
              <div className="flex flex-wrap gap-1 mb-2">
                {getBoundaryTags(agent).map((tag, idx) => (
                  <span 
                    key={idx} 
                    className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border ${tag.class}`}
                  >
                    {tag.label}
                  </span>
                ))}
              </div>
              <span className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-auto flex items-center gap-1">
                <Activity size={10} /> {agent.llm_model}
              </span>
              <div className="flex gap-2 mt-4 pt-3 border-t border-border/50">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/agent/${agent.id}/settings`, { state: { agent } });
                  }}
                  className="flex items-center justify-center gap-1.5 p-2 rounded-lg flex-1 transition hover:bg-primary hover:text-primary-foreground bg-muted text-muted-foreground font-medium text-xs"
                  title="Settings"
                >
                  <Settings size={14} /> Settings
                </button>
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

    // Build a set of all agent IDs in the active path (from active agent up to root)
    const activePathSet = new Set();
    let currentId = activeRoutingAgentId;
    while (currentId) {
      activePathSet.add(currentId);
      const currentAgent = subAgents.find(a => a.id === currentId);
      if (currentAgent && currentAgent.parent_agent_id) {
        currentId = currentAgent.parent_agent_id;
      } else {
        currentId = null;
      }
    }

    const dynamicEdges = subAgents
      .filter(agent => agent.parent_agent_id)
      .map(agent => {
        const isEdgeActive = activePathSet.has(agent.id) && activePathSet.has(agent.parent_agent_id);
        
        return {
          id: `e-${agent.parent_agent_id}-${agent.id}`,
          source: agent.parent_agent_id,
          target: agent.id,
          type: 'smoothstep',
          animated: isEdgeActive || activeRoutingAgentId === agent.parent_agent_id,
          style: { 
            stroke: isEdgeActive ? '#a855f7' : '#6b7280', 
            strokeWidth: isEdgeActive ? 3 : 2 
          }
        };
      });

    return dynamicEdges;
  };

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!subAgents.length) {
      setNodes([]);
      setEdges([]);
      return;
    }
    const rawNodes = createInitialNodes();
    const rawEdges = createInitialEdges();
    const layout = getLayoutedElements(rawNodes, rawEdges, 'TB');
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [subAgents, activeRoutingAgentId, updateAgentMutation.isPending]);

  const onConnect = useCallback(
    async (params) => {
      setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#a855f7', strokeWidth: 2 } }, eds));
      try {
        const targetAgent = subAgents.find(a => a.id === params.target);
        if (targetAgent) {
          await updateAgentMutation.mutateAsync({ 
            id: targetAgent.id, 
            payload: { parent_agent_id: params.source }
          });
          toast.success("Connection updated");
        }
      } catch (err) {
        toast.error("Failed to update connection");
      }
    },
    [setEdges, subAgents, updateAgentMutation]
  );

  const onEdgesDelete = useCallback(
    async (deletedEdges) => {
      try {
        for (const edge of deletedEdges) {
          const targetAgent = subAgents.find(a => a.id === edge.target);
          if (targetAgent) {
            await updateAgentMutation.mutateAsync({
              id: targetAgent.id,
              payload: { parent_agent_id: null }
            });
          }
        }
        toast.success("Connection removed");
      } catch (err) {
        toast.error("Failed to remove connection");
      }
    },
    [subAgents, updateAgentMutation]
  );

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
        
        {subAgents.length === 0 && (
          <div className="flex items-center gap-3">
            <button 
              onClick={() => handleAddAgent(null)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition shadow-sm"
            >
              <Plus size={16} /> Create Master Agent
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 relative flex overflow-hidden">
        <div className="flex-1 relative h-[calc(100vh-140px)]">
          {!isSandboxOpen && (
            <button
              onClick={() => setIsSandboxOpen(true)}
              className="absolute top-4 right-4 z-10 flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-full shadow-lg transition-colors font-medium text-sm"
            >
              <MessagesSquare size={16} />
              Test Network
            </button>
          )}

          {subAgents.length > 0 ? (
            <ReactFlow 
              nodes={nodes} 
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onEdgesDelete={onEdgesDelete}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-right"
              nodesDraggable={true}
              colorMode="system"
            >
              <Background gap={16} />
              <Controls className="!bg-card !border-border !fill-foreground" />
            </ReactFlow>
          ) : (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground gap-4">
              <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
                <Bot size={32} />
              </div>
              <p>No agents in this network yet.</p>
              <button
                onClick={() => handleAddAgent(null)}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                Create Master Agent
              </button>
            </div>
          )}
        </div>
        
        {isSandboxOpen && (
          <>
            <StudioSandboxChat
              messages={messages}
              loading={loading}
              onSend={(content) => {
                const manager = subAgents.find(a => a.name === 'Network Manager');
                if (manager) {
                  sendMessage({
                    agentId: manager.id,
                    agentName: manager.name,
                    content,
                    language: chatLanguage
                  });
                } else {
                  toast.error("Network Manager not found!");
                }
              }}
              agent={subAgents.find(a => a.name === 'Network Manager')}
              chatLanguage={chatLanguage}
              setChatLanguage={setChatLanguage}
              onClose={() => {
                setIsSandboxOpen(false);
                clearSandbox();
              }}
            />
            <TracePanel onClose={() => {
              setIsSandboxOpen(false);
              clearSandbox();
            }} />
          </>
        )}
      </div>


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
