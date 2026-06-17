import React, { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAgentProjects, useProjectSubAgents } from '../hooks/useAgents';
import { useUIStore } from '../store/useUIStore';
import { ArrowLeft, Settings, Database, Bot } from 'lucide-react';
import AgentSettingsModal from '../components/agents/AgentSettingsModal';
import ApiToolsModal from '../components/agents/ApiToolsModal';
import { ReactFlow, MiniMap, Controls, Background, useNodesState, useEdgesState } from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';
import LoadingSkeleton from '../components/shared/LoadingSkeleton';

const getLayoutedElements = (nodes, edges, direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    // node dimensions are approximately 200x110
    dagreGraph.setNode(node.id, { width: 220, height: 130 });
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
      x: nodeWithPosition.x - 220 / 2,
      y: nodeWithPosition.y - 130 / 2,
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

  const { data: projects = [], isLoading: isProjectsLoading } = useAgentProjects(activeWorkspaceId);
  const { data: subAgents = [], isLoading: isAgentsLoading } = useProjectSubAgents(projectId);

  const project = projects.find(p => p.id === projectId);

  const createInitialNodes = () => {
    if (!subAgents.length) return [];
    
    // Create a central Master Node
    const nodes = [
      {
        id: 'master',
        position: { x: 400, y: 50 },
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
            <div className="flex flex-col items-center">
              <div className="h-10 w-10 rounded-full bg-purple-500/20 flex items-center justify-center mb-2">
                <Bot className="text-purple-500" size={20} />
              </div>
              <strong className="text-sm font-semibold">Master Coordinator</strong>
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
        style: {
          backgroundColor: 'var(--card)',
          color: 'var(--text)',
          borderColor: 'var(--border)',
          borderRadius: '0.75rem',
          padding: '0.75rem',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          width: 200,
          height: 110,
        },
        data: {
          label: (
            <div className="flex flex-col h-full text-left">
              <strong className="text-sm font-semibold truncate mb-1" title={agent.name}>{agent.name}</strong>
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider mb-3">{agent.llm_model}</span>
              <div className="flex gap-2 mt-auto">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setAgentToEdit(agent);
                  }}
                  className="flex items-center justify-center p-1.5 rounded-lg flex-1 transition"
                  style={{ backgroundColor: 'var(--border)' }}
                  title="Settings"
                >
                  <Settings size={14} />
                </button>
                <Link
                  to="/knowledge"
                  className="flex items-center justify-center p-1.5 rounded-lg flex-1 transition"
                  style={{ backgroundColor: 'var(--border)' }}
                  title="Knowledge Base"
                  onClick={(e) => e.stopPropagation()}
                >
                  <Database size={14} />
                </Link>
              </div>
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
  }, [subAgents]);

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
          <Link to="/playground" className="p-2 bg-muted hover:bg-muted/80 text-foreground rounded-xl transition">
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
        
        <button 
          onClick={() => setIsToolsModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 transition shadow-sm"
        >
          API Tools Manager
        </button>
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
    </div>
  );
}
