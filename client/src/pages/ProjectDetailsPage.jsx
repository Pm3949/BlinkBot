import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAgentProjects, useProjectSubAgents, useUpdateAgent, useDeleteAgent } from '../hooks/useAgents';
import { useSandboxChat } from '../hooks/useSandboxChat';
import { useUIStore } from '../store/useUIStore';
import { ArrowLeft, Settings, Database, Bot, Activity, Plus, Trash2, MessagesSquare, Wrench, FileText, X, Loader2 } from 'lucide-react';
import CreateAgentWizard from '../components/agents/CreateAgentWizard';
import StudioSandboxChat from '../components/chat/StudioSandboxChat';
import TracePanel from '../components/chat/TracePanel';
import { Switch } from '../components/ui/switch';
import { Button } from '../components/ui/button';
import { ReactFlow, MiniMap, Controls, Background, useNodesState, useEdgesState, addEdge, Handle, Position } from '@xyflow/react';
import { getAgentAttachedTools, getWorkspaceTools, attachToolToAgent, detachToolFromAgent } from '../services/workspaceToolsService';
import { getDocuments, getBatchDocuments } from '../services/documentService';
import { useUploadDocument } from '../hooks/useDocuments';

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

const ToolNode = ({ data }) => (
  <>
    <Handle type="target" position={Position.Top} className="w-2.5 h-2.5 bg-amber-500 border-2 border-background" />
    <div className="relative rounded-xl bg-card border border-amber-500/30 p-2.5 shadow-md flex items-center gap-2 max-w-[200px]">
      <div className="h-7 w-7 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-500 shrink-0">
        <Wrench size={14} />
      </div>
      <div className="overflow-hidden">
        <div className="text-[12px] font-semibold text-foreground truncate" title={data.name}>{data.name}</div>
        <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Tool</div>
      </div>
    </div>
  </>
);

const KBNode = ({ data }) => (
  <>
    <Handle type="target" position={Position.Top} className="w-2.5 h-2.5 bg-teal-500 border-2 border-background" />
    <div 
      onClick={data.onClick}
      className={`relative rounded-xl bg-card border transition-all duration-300 p-2.5 shadow-md flex items-center justify-between gap-3 min-w-[220px] cursor-pointer hover:border-teal-500/60 ${data.isExpanded ? 'ring-2 ring-teal-500/40 border-teal-500' : 'border-teal-500/30'}`}
    >
      <div className="flex items-center gap-2 overflow-hidden">
        <div className="h-7 w-7 rounded-lg bg-teal-500/10 flex items-center justify-center text-teal-500 shrink-0">
          <Database size={14} />
        </div>
        <div className="overflow-hidden">
          <div className="text-[12px] font-semibold text-foreground truncate">Knowledge Base</div>
          <div className="text-[10px] text-muted-foreground font-medium">{data.docCount} {data.docCount === 1 ? 'doc' : 'docs'}</div>
        </div>
      </div>
      <div className="text-[10px] text-teal-500 font-semibold px-2 py-0.5 bg-teal-500/10 rounded-full shrink-0">
        {data.isExpanded ? 'Hide' : 'Show Docs'}
      </div>
    </div>
    <Handle type="source" position={Position.Bottom} className="w-2.5 h-2.5 bg-teal-500 border-2 border-background" />
  </>
);

const DocNode = ({ data }) => (
  <>
    <Handle type="target" position={Position.Top} className="w-2.5 h-2.5 bg-sky-500 border-2 border-background" />
    <div className="relative rounded-xl bg-card border border-sky-500/20 p-2 shadow-sm flex items-center gap-2 max-w-[180px]">
      <div className="h-6 w-6 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-500 shrink-0">
        <FileText size={12} />
      </div>
      <div className="overflow-hidden">
        <div className="text-[10px] font-semibold text-foreground truncate" title={data.name}>{data.name}</div>
        <div className="text-[9px] text-muted-foreground truncate">{data.status}</div>
      </div>
    </div>
  </>
);

const nodeTypes = {
  masterNode: MasterNode,
  agentNode: AgentNode,
  toolNode: ToolNode,
  kbNode: KBNode,
  docNode: DocNode,
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
    let width = 320;
    let height = 160;
    if (node.type === 'toolNode') {
      width = 200;
      height = 60;
    } else if (node.type === 'kbNode') {
      width = 220;
      height = 60;
    } else if (node.type === 'docNode') {
      width = 180;
      height = 50;
    }
    dagreGraph.setNode(node.id, { width, height });
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

    let width = 320;
    let height = 160;
    if (node.type === 'toolNode') {
      width = 200;
      height = 60;
    } else if (node.type === 'kbNode') {
      width = 220;
      height = 60;
    } else if (node.type === 'docNode') {
      width = 180;
      height = 50;
    }

    newNode.position = {
      x: nodeWithPosition.x - width / 2,
      y: nodeWithPosition.y - height / 2,
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

  const [agentsTools, setAgentsTools] = useState({});
  const [agentsDocs, setAgentsDocs] = useState({});
  const [expandedKbs, setExpandedKbs] = useState(new Set());
  const [loadingExtras, setLoadingExtras] = useState(false);

  // Layout orientation TB (Vertical) or LR (Horizontal)
  const [layoutDirection, setLayoutDirection] = useState('TB');

  // Interactive Node Selection
  const [selectedNode, setSelectedNode] = useState(null);

  // Loading state when attaching/detaching tools
  const [updatingToolId, setUpdatingToolId] = useState(null);

  // Dynamic Highlight Execution States
  const [activeExecutingTools, setActiveExecutingTools] = useState(new Set());

  // Workspace tools list for quick attach drawer
  const [allWorkspaceTools, setAllWorkspaceTools] = useState([]);

  // File Upload states
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = React.useRef(null);
  const uploadDocMutation = useUploadDocument(selectedNode?.id);

  // Document view preview state
  const [previewContent, setPreviewContent] = useState('');
  const [loadingPreview, setLoadingPreview] = useState(false);

  const toggleKb = useCallback((agentId) => {
    setExpandedKbs((prev) => {
      const next = new Set(prev);
      if (next.has(agentId)) {
        next.delete(agentId);
      } else {
        next.add(agentId);
      }
      return next;
    });
  }, []);

  const {
    messages,
    loading,
    sendMessage,
    clearSandbox,
    pendingApproval,
    sendApprovalResponse
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

  // Listen for socket events to animate executing tools & RAG searches
  useEffect(() => {
    const handleToolStart = (e) => {
      const toolName = e.detail.tool_name;
      setActiveExecutingTools(prev => {
        const next = new Set(prev);
        next.add(toolName.toLowerCase().replace(/_/g, '').replace(/\s/g, ''));
        return next;
      });
    };
    const handleToolEnd = (e) => {
      const toolName = e.detail.tool_name;
      setActiveExecutingTools(prev => {
        const next = new Set(prev);
        next.delete(toolName.toLowerCase().replace(/_/g, '').replace(/\s/g, ''));
        return next;
      });
    };

    window.addEventListener('agent_tool_start', handleToolStart);
    window.addEventListener('agent_tool_end', handleToolEnd);
    return () => {
      window.removeEventListener('agent_tool_start', handleToolStart);
      window.removeEventListener('agent_tool_end', handleToolEnd);
    };
  }, []);

  // Fetch all workspace tools
  useEffect(() => {
    if (activeWorkspaceId) {
      getWorkspaceTools(activeWorkspaceId)
        .then(setAllWorkspaceTools)
        .catch(err => console.error("Failed to load workspace tools:", err));
    }
  }, [activeWorkspaceId]);

  // Fetch document preview contents when document node is selected
  useEffect(() => {
    if (selectedNode?.type === 'doc') {
      setLoadingPreview(true);
      setPreviewContent('');
      const token = localStorage.getItem("access_token");
      fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/api/documents/${selectedNode.rawItem.id}/view`, {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      })
      .then(r => r.text())
      .then(t => {
        setPreviewContent(t);
      })
      .catch(() => {
        setPreviewContent("Failed to load document text contents.");
      })
      .finally(() => {
        setLoadingPreview(false);
      });
    }
  }, [selectedNode]);

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

  useEffect(() => {
    if (!subAgents.length) return;
    const loadExtras = async () => {
      setLoadingExtras(true);
      try {
        const toolsMap = {};
        const agentIds = subAgents.map(a => a.id);

        // Fetch documents for all agents in one batch call, and fetch tools for all agents in parallel
        const [batchDocsResponse, ...toolsResults] = await Promise.all([
          getBatchDocuments(agentIds).catch(err => {
            console.error("Failed to fetch batch documents:", err);
            return {};
          }),
          ...subAgents.map(agent =>
            getAgentAttachedTools(agent.id).catch(err => {
              console.error(`Failed to load tools for agent ${agent.id}:`, err);
              return [];
            })
          )
        ]);

        // Map tools results back to respective agents
        subAgents.forEach((agent, index) => {
          toolsMap[agent.id] = toolsResults[index] || [];
        });

        setAgentsTools(toolsMap);
        setAgentsDocs(batchDocsResponse || {});
      } catch (err) {
        console.error("Failed to load agents extra details:", err);
      } finally {
        setLoadingExtras(false);
      }
    };
    loadExtras();
  }, [subAgents]);

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

      // Add attached tools as nodes
      const tools = agentsTools[agent.id] || [];
      tools.forEach((tool) => {
        const normalizedToolName = tool.name.toLowerCase().replace(/_/g, '').replace(/\s/g, '');
        const isExecuting = activeExecutingTools.has(normalizedToolName);
        
        nodes.push({
          id: `tool:${agent.id}:${tool.id}`,
          type: 'toolNode',
          position: { x: 0, y: 0 },
          data: {
            name: tool.name,
            isExecuting,
          }
        });
      });

      // Add Knowledge Base node if agent has documents
      const docs = agentsDocs[agent.id] || [];
      const isKbExecuting = activeExecutingTools.has('searchknowledgebase');
      if (docs.length > 0) {
        nodes.push({
          id: `kb:${agent.id}`,
          type: 'kbNode',
          position: { x: 0, y: 0 },
          data: {
            docCount: docs.length,
            isExpanded: expandedKbs.has(agent.id),
            isExecuting: isKbExecuting && (activeRoutingAgentId === agent.id),
            onClick: () => toggleKb(agent.id),
          }
        });

        if (expandedKbs.has(agent.id)) {
          docs.forEach((doc) => {
            nodes.push({
              id: `doc:${agent.id}:${doc.id}`,
              type: 'docNode',
              position: { x: 0, y: 0 },
              data: {
                name: doc.filename,
                status: doc.status || 'completed',
              }
            });
          });
        }
      }
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

    // Add edges for tools and KBs
    subAgents.forEach((agent) => {
      const tools = agentsTools[agent.id] || [];
      tools.forEach((tool) => {
        dynamicEdges.push({
          id: `e-tool-${agent.id}-${tool.id}`,
          source: agent.id,
          target: `tool:${agent.id}:${tool.id}`,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#f59e0b', strokeWidth: 1.5, strokeDasharray: '5,5' }
        });
      });

      const docs = agentsDocs[agent.id] || [];
      if (docs.length > 0) {
        dynamicEdges.push({
          id: `e-kb-${agent.id}`,
          source: agent.id,
          target: `kb:${agent.id}`,
          type: 'smoothstep',
          animated: false,
          style: { stroke: '#14b8a6', strokeWidth: 1.5, strokeDasharray: '5,5' }
        });

        if (expandedKbs.has(agent.id)) {
          docs.forEach((doc) => {
            dynamicEdges.push({
              id: `e-doc-${agent.id}-${doc.id}`,
              source: `kb:${agent.id}`,
              target: `doc:${agent.id}:${doc.id}`,
              type: 'smoothstep',
              animated: false,
              style: { stroke: '#0ea5e9', strokeWidth: 1 }
            });
          });
        }
      }
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
    const layout = getLayoutedElements(rawNodes, rawEdges, layoutDirection);
    setNodes(layout.nodes);
    setEdges(layout.edges);
  }, [subAgents, activeRoutingAgentId, updateAgentMutation.isPending, agentsTools, agentsDocs, expandedKbs, layoutDirection]);

  // Handle single node click to open details/actions drawer
  const onNodeClick = useCallback((event, node) => {
    if (node.type === 'agentNode' || node.type === 'masterNode') {
      const agent = subAgents.find(a => a.id === node.id);
      if (agent && (agent.name === 'Network Manager' || agent.name === 'General Assistant')) {
        setSelectedNode(null);
        return;
      }
      setSelectedNode({ type: 'agent', id: node.id, rawItem: agent });
    } else {
      setSelectedNode(null);
    }
  }, [subAgents]);

  // Handle quick tool toggling in Agent Drawer
  const handleToggleToolInDrawer = async (toolId, isCurrentlyAttached) => {
    if (!selectedNode || selectedNode.type !== 'agent' || updatingToolId) return;
    setUpdatingToolId(toolId);
    try {
      if (isCurrentlyAttached) {
        await detachToolFromAgent(selectedNode.id, toolId);
        setAgentsTools(prev => ({
          ...prev,
          [selectedNode.id]: (prev[selectedNode.id] || []).filter(t => t.id !== toolId)
        }));
        toast.success("Tool detached successfully");
      } else {
        await attachToolToAgent(selectedNode.id, toolId);
        const newlyAttachedTool = allWorkspaceTools.find(t => t.id === toolId);
        setAgentsTools(prev => ({
          ...prev,
          [selectedNode.id]: [...(prev[selectedNode.id] || []), newlyAttachedTool]
        }));
        toast.success("Tool attached successfully");
      }
    } catch (err) {
      toast.error(err.message || "Failed to update tool connection");
    } finally {
      setUpdatingToolId(null);
    }
  };

  // Handle document uploads from details drawer dropzone
  const handleFileUpload = async (files) => {
    if (!selectedNode || selectedNode.type !== 'agent') return;
    const fileList = Array.from(files);
    if (!fileList.length) return;
    
    toast.loading("Uploading and indexing documents...", { id: "graph-upload" });
    try {
      const promises = fileList.map(file => 
        uploadDocMutation.mutateAsync({ agentId: selectedNode.id, file })
      );
      await Promise.all(promises);
      toast.success(`${fileList.length} file(s) uploaded successfully!`, { id: "graph-upload" });
      
      const updatedDocs = await getDocuments(selectedNode.id);
      setAgentsDocs(prev => ({
        ...prev,
        [selectedNode.id]: updatedDocs
      }));
    } catch (err) {
      toast.error(err.message || "Failed to upload document", { id: "graph-upload" });
    }
  };

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
          {/* Floating Controls for Layout and Testing */}
          <div className="absolute top-4 left-4 z-10 flex items-center gap-2 bg-card/85 backdrop-blur border border-border/50 rounded-xl p-1.5 shadow-lg">
            <button
              onClick={() => setLayoutDirection('TB')}
              className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1 transition ${layoutDirection === 'TB' ? 'bg-indigo-600 text-white' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}
              title="Vertical Flow"
            >
              Vertical
            </button>
            <button
              onClick={() => setLayoutDirection('LR')}
              className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1 transition ${layoutDirection === 'LR' ? 'bg-indigo-600 text-white' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}
              title="Horizontal Flow"
            >
              Horizontal
            </button>
          </div>

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
              onNodeClick={onNodeClick}
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
              pendingApproval={pendingApproval}
              sendApprovalResponse={sendApprovalResponse}
            />
            <TracePanel onClose={() => {
              setIsSandboxOpen(false);
              clearSandbox();
            }} />
          </>
        )}

        {/* Info & Config Slide-over Drawer */}
        {selectedNode && (
          <div className="absolute top-0 right-0 h-full w-[400px] bg-card/95 backdrop-blur-md border-l border-border/50 shadow-2xl z-40 animate-in slide-in-from-right duration-300 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-border/50 bg-background/50 shrink-0">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-500 border border-indigo-500/20">
                  <Bot size={22} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-foreground leading-tight">Agent Configuration</h3>
                  <p className="text-xs text-muted-foreground mt-0.5">Manage behavior and connections</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedNode(null)}
                className="p-2 hover:bg-muted text-muted-foreground hover:text-foreground rounded-xl transition-all"
                title="Close drawer"
              >
                <X size={20} />
              </button>
            </div>

            {/* Content body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin">
              {selectedNode.type === 'agent' && (
                <>
                  {/* Premium Agent Profile Card */}
                  <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-primary/5 via-transparent to-transparent p-5">
                    <div className="absolute -top-10 -right-10 w-24 h-24 rounded-full bg-primary/10 blur-xl pointer-events-none" />
                    
                    <div className="flex items-center gap-4">
                      <div className="h-12 w-12 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-600/20 shrink-0">
                        <Bot size={26} />
                      </div>
                      <div className="overflow-hidden">
                        <h4 className="text-base font-bold text-foreground truncate">{selectedNode.rawItem?.name}</h4>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 text-[10px] font-bold uppercase tracking-wider">
                            {selectedNode.rawItem?.llm_provider}
                          </span>
                          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                          <span className="text-[11px] text-muted-foreground font-medium">Active Node</span>
                        </div>
                      </div>
                    </div>

                    {selectedNode.rawItem?.description && (
                      <p className="mt-4 text-xs text-muted-foreground leading-relaxed bg-background/40 rounded-xl p-3 border border-border/20">
                        {selectedNode.rawItem.description}
                      </p>
                    )}
                  </div>

                  {/* Model specifications Grid */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-muted/30 border border-border/30 rounded-xl p-3 space-y-1">
                      <div className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">LLM Model</div>
                      <div className="text-xs font-mono text-foreground truncate" title={selectedNode.rawItem?.llm_model}>
                        {selectedNode.rawItem?.llm_model}
                      </div>
                    </div>
                    <div className="bg-muted/30 border border-border/30 rounded-xl p-3 space-y-1">
                      <div className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider">Embedding</div>
                      <div className="text-xs font-mono text-foreground truncate" title={selectedNode.rawItem?.embedding_model || 'all-MiniLM-L6-v2'}>
                        {selectedNode.rawItem?.embedding_model || 'all-MiniLM-L6-v2'}
                      </div>
                    </div>
                  </div>

                  {/* Connected Tools Checklist */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                        <Wrench size={16} className="text-amber-500" /> Quick Attached Tools
                      </h4>
                      <span className="text-[10px] text-amber-500 font-bold px-2 py-0.5 bg-amber-500/10 rounded-full">
                        {(agentsTools[selectedNode.id] || []).length} active
                      </span>
                    </div>
                    <div className="border border-border/40 bg-background/50 rounded-2xl p-3 max-h-56 overflow-y-auto space-y-2 scrollbar-thin">
                      {allWorkspaceTools.length === 0 ? (
                        <p className="text-xs text-muted-foreground text-center py-6">No workspace tools configured.</p>
                      ) : (
                        allWorkspaceTools.map((t) => {
                          const isAttached = (agentsTools[selectedNode.id] || []).some(attached => attached.id === t.id);
                          const isUpdating = updatingToolId === t.id;
                          return (
                            <div 
                              key={t.id}
                              onClick={() => {
                                if (updatingToolId) return;
                                handleToggleToolInDrawer(t.id, isAttached);
                              }}
                              className={`flex items-center justify-between p-3 rounded-xl transition-all duration-300 border ${
                                isUpdating
                                  ? 'opacity-65 cursor-not-allowed border-amber-500/20 bg-amber-500/5'
                                  : updatingToolId
                                    ? 'opacity-50 cursor-not-allowed border-border/30'
                                    : isAttached 
                                      ? 'border-amber-500/40 bg-amber-500/5 shadow-sm shadow-amber-500/5 cursor-pointer' 
                                      : 'border-border/30 hover:border-border/60 hover:bg-muted/40 cursor-pointer'
                              }`}
                            >
                              <div className="flex items-center gap-2.5 overflow-hidden">
                                <Wrench size={14} className={isAttached ? 'text-amber-500' : 'text-foreground/60'} />
                                <span className={`truncate max-w-[260px] text-sm font-semibold ${isAttached ? 'text-foreground font-bold' : 'text-foreground/80 font-medium'}`} title={t.name}>
                                  {t.name}
                                </span>
                              </div>
                              <div className={`w-5 h-5 rounded-md border flex items-center justify-center transition-all ${
                                isAttached 
                                  ? 'bg-amber-500 border-transparent text-white shadow-sm' 
                                  : 'border-border/60 bg-background'
                              }`}>
                                {isUpdating ? (
                                  <Loader2 size={10} className="animate-spin text-amber-500" />
                                ) : isAttached ? (
                                  <span className="text-[11px] font-bold">✓</span>
                                ) : null}
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>

                  {/* Document upload drop zone */}
                  <div className="space-y-3">
                    <h4 className="text-sm font-bold text-foreground flex items-center gap-1.5">
                      <Database size={16} className="text-indigo-500" /> Vector Documents Ingestion
                    </h4>
                    <div
                      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                      onDragLeave={() => setIsDragOver(false)}
                      onDrop={(e) => {
                        e.preventDefault();
                        setIsDragOver(false);
                        handleFileUpload(e.dataTransfer.files);
                      }}
                      onClick={() => fileInputRef.current?.click()}
                      className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all duration-300 ${
                        isDragOver 
                          ? 'border-indigo-500 bg-indigo-500/5 shadow-lg shadow-indigo-500/10 scale-[0.99]' 
                          : 'border-border/60 hover:border-indigo-500/50 hover:bg-muted/30'
                      }`}
                    >
                      <input 
                        type="file" 
                        ref={fileInputRef} 
                        className="hidden" 
                        multiple 
                        onChange={(e) => handleFileUpload(e.target.files)} 
                      />
                      <div className="h-10 w-10 rounded-full bg-indigo-500/10 flex items-center justify-center text-indigo-500 mx-auto mb-3 border border-indigo-500/20">
                        <Database size={20} />
                      </div>
                      <p className="text-xs font-bold text-foreground">Drag & drop files here</p>
                      <p className="text-[10px] text-muted-foreground mt-1">Supports PDF, TXT, CSV (click to browse)</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
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
