import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Webhook, 
  Database as DbIcon, 
  Key, 
  Terminal, 
  Plus, 
  Trash2, 
  Pencil, 
  FileCode, 
  AlertCircle,
  Activity,
  CheckCircle,
  HelpCircle
} from "lucide-react";
import { useUIStore } from "../store/useUIStore";
import { 
  createWorkspaceTool, 
  updateWorkspaceTool, 
  deleteWorkspaceTool 
} from "../services/workspaceToolsService";
import { getAuthHeaders } from "../lib/api";
import { toast } from "sonner";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";

// ==========================================
// MAIN COMPONENT
// ==========================================

export default function WorkspaceToolsPage() {
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const navigate = useNavigate();

  // Zustand State Management selectors
  const tools = useUIStore((state) => state.tools);
  const storeTemplates = useUIStore((state) => state.storeTemplates);
  const loading = useUIStore((state) => state.loadingTools);
  const fetchTools = useUIStore((state) => state.fetchTools);
  const fetchStoreTemplates = useUIStore((state) => state.fetchStoreTemplates);

  // Tab State: 'store' or 'custom'
  const [activeTab, setActiveTab] = useState("store");

  // Global Search State
  const [searchQuery, setSearchQuery] = useState("");

  // Independent Filters
  const [storeFilter, setStoreFilter] = useState("all");
  const [customFilter, setCustomFilter] = useState("all");

  useEffect(() => {
    fetchTools(activeWorkspaceId);
    fetchStoreTemplates();
  }, [activeWorkspaceId]);

  const handleDelete = async (toolId) => {
    if (!confirm("Are you sure you want to delete this tool? Any agents subscribed to this tool will lose access.")) {
      return;
    }
    try {
      await deleteWorkspaceTool(activeWorkspaceId, toolId);
      toast.success("Tool deleted successfully");
      fetchTools(activeWorkspaceId);
    } catch (err) {
      toast.error(err.message || "Failed to delete tool");
    }
  };

  const handleEnableStoreTool = async (templateId, toolName) => {
    try {
      const targetTool = storeTemplates.find(t => t.id === templateId);
      let apiKey = null;
      if (targetTool?.requires_auth) {
        apiKey = prompt(`Please enter your API Key/Token for ${toolName}:`);
        if (!apiKey) {
          toast.error(`API key is required to provision the ${toolName} capability.`);
          return;
        }
      }

      const API_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
      const headers = getAuthHeaders();
      
      const res = await fetch(`${API_URL}/api/tools/provision`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          template_id: templateId,
          workspace_id: activeWorkspaceId,
          api_key: apiKey
        })
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to provision tool");
      }
      
      toast.success(`${toolName} has been successfully added to your workspace!`);
      fetchTools(activeWorkspaceId);
    } catch (err) {
      toast.error(err.message || "Failed to provision tool");
    }
  };

  const getToolIcon = (type) => {
    switch (type) {
      case "api_webhook":
        return <Webhook className="text-primary" size={20} />;
      case "database":
        return <DbIcon className="text-emerald-500" size={20} />;
      case "oauth":
        return <Key className="text-purple-500" size={20} />;
      case "python_code":
        return <FileCode className="text-indigo-500" size={20} />;
      default:
        return <Terminal className="text-muted-foreground" size={20} />;
    }
  };

  const getToolTypeName = (type) => {
    switch (type) {
      case "api_webhook":
        return "REST Webhook API";
      case "database":
        return "Database Connector";
      case "oauth":
        return "OAuth Native Connection";
      case "python_code":
        return "Custom Python Script (BYOC)";
      default:
        return type;
    }
  };

  // Split system vs custom tools
  const customTools = tools.filter(t => !t.is_system);

  const activeList = activeTab === "store" ? storeTemplates : customTools;
  const activeFilter = activeTab === "store" ? storeFilter : customFilter;

  // Filter tools using global search and independent local tab type filters
  const filteredTools = activeList.filter((tool) => {
    if (searchQuery.trim() && !tool.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (activeFilter !== "all" && tool.tool_type !== activeFilter) {
      return false;
    }
    return true;
  });

  if (loading) {
    return <LoadingSkeleton count={3} className="h-40 mb-4" />;
  }

  return (
    <div className="w-full px-4 sm:px-8 space-y-6 pb-12 animate-in fade-in duration-200">
      {/* Header Section */}
      <div className="flex flex-row justify-between items-center gap-4 border-b border-border/40 pb-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground">Workspace Tool Library</h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1 hidden sm:block">
            Configure integrations, API hooks, and database connectors globally, and attach them to any Agent in this workspace.
          </p>
        </div>

        {/* Tab Navigation Switcher (Larger Buttons) */}
        <div className="flex bg-card/60 border border-border/60 p-1.5 rounded-xl gap-1 shrink-0">
          <button
            onClick={() => setActiveTab("store")}
            className={`px-6 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 ${activeTab === "store" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
          >
            Tool Store
          </button>
          <button
            onClick={() => setActiveTab("custom")}
            className={`px-6 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 ${activeTab === "custom" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
          >
            My Custom Tools
          </button>
        </div>
      </div>

      {/* Global Search Bar */}
      <div className="relative w-full bg-card/20 border border-border/40 p-3 rounded-2xl shrink-0">
        <input
          type="text"
          placeholder="Search workspace tools by name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-11 pr-4 py-3 bg-background border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary font-medium"
        />
        <svg className="absolute left-7 top-6.5 w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>

      {/* Tab Content 1: Tool Store */}
      {activeTab === "store" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Local Tab Header & Separate Filter Option */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="text-xl font-bold text-foreground">Pre-defined Store Tools</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Enable template and system capabilities on this workspace instantly.</p>
            </div>
            
            {/* Filter by Type for Store */}
            <div className="flex items-center gap-2 w-full sm:w-auto shrink-0 bg-card/25 border border-border/40 px-3 py-1.5 rounded-xl">
              <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider whitespace-nowrap">Filter By Type:</label>
              <select
                value={storeFilter}
                onChange={(e) => setStoreFilter(e.target.value)}
                className="border-none bg-transparent text-foreground text-xs focus:outline-none cursor-pointer font-bold uppercase tracking-wide"
              >
                <option value="all" className="bg-card">All Types</option>
                <option value="api_webhook" className="bg-card">Webhooks</option>
                <option value="database" className="bg-card">Database</option>
                <option value="oauth" className="bg-card">OAuth App</option>
                <option value="python_code" className="bg-card">Python BYOC</option>
              </select>
            </div>
          </div>

          {filteredTools.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-border bg-card p-12 text-center flex flex-col items-center justify-center space-y-4">
              <Terminal size={32} className="text-muted-foreground" />
              <div>
                <h3 className="font-bold text-base text-foreground">No pre-defined tools match your search</h3>
                <p className="text-xs text-muted-foreground mt-1">Try clearing your filters or search criteria.</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTools.map((tool) => {
                // Check if this template tool or global tool is already enabled in active workspace list
                const isEnabled = tool.is_global
                  ? tools.some(t => t.is_global && t.tool_key === tool.tool_key)
                  : tools.some(t => t.name === tool.name);
                
                const activeTool = tool.is_global
                  ? tools.find(t => t.is_global && t.tool_key === tool.tool_key)
                  : tools.find(t => t.name === tool.name);
                
                return (
                  <div key={tool.id} className="glass-card p-6 flex flex-col justify-between h-64 transition-all duration-200 hover:shadow-md border border-border/50 gap-y-4">
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 bg-muted rounded-xl">
                            {getToolIcon(tool.tool_type)}
                          </div>
                          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                            {getToolTypeName(tool.tool_type)}
                          </span>
                        </div>
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                          {tool.is_global ? "Global" : "Template"}
                        </span>
                      </div>

                      <div>
                        <h3 className="font-bold text-lg text-foreground truncate">{tool.name}</h3>
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-1.5 leading-relaxed">
                          {tool.description || "Default platform tool integration."}
                        </p>
                      </div>
                    </div>

                    {/* Enable / Remove Actions */}
                    <div className="pt-3.5 border-t border-border/20 flex items-center justify-between mt-auto">
                      <span className="text-xs text-muted-foreground font-mono">Status: {isEnabled ? "Active" : "Available"}</span>
                      {isEnabled ? (
                        <button
                          type="button"
                          onClick={() => handleDelete(activeTool.id)}
                          className="px-4 py-2 border border-red-500/30 bg-red-500/5 hover:bg-red-500/10 text-red-400 font-bold text-xs rounded-xl shadow transition"
                        >
                          Remove from Workspace
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleEnableStoreTool(tool.id, tool.name)}
                          className="px-4 py-2 bg-primary hover:bg-primary/95 text-primary-foreground font-bold text-xs rounded-xl shadow transition"
                        >
                          Add to Workspace
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab Content 2: My Custom Tools */}
      {activeTab === "custom" && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Local Tab Header & Separate Filter Option */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div className="flex-1">
              <h2 className="text-xl font-bold text-foreground">Custom Integrations</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Manage your user-created REST APIs, DB connectors, and scripts.</p>
            </div>
            
            <div className="flex items-center gap-3 w-full sm:w-auto shrink-0 flex-wrap sm:flex-nowrap">
              {/* Filter by Type for Custom */}
              <div className="flex items-center gap-2 bg-card/25 border border-border/40 px-3 py-1.5 rounded-xl">
                <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider whitespace-nowrap">Filter By Type:</label>
                <select
                  value={customFilter}
                  onChange={(e) => setCustomFilter(e.target.value)}
                  className="border-none bg-transparent text-foreground text-xs focus:outline-none cursor-pointer font-bold uppercase tracking-wide"
                >
                  <option value="all" className="bg-card">All Types</option>
                  <option value="api_webhook" className="bg-card">Webhooks</option>
                  <option value="database" className="bg-card">Database</option>
                  <option value="oauth" className="bg-card">OAuth App</option>
                  <option value="python_code" className="bg-card">Python BYOC</option>
                </select>
              </div>
              
              <button
                onClick={() => navigate("/tools/new")}
                className="h-10 px-4 btn-primary rounded-xl flex items-center justify-center gap-2 font-semibold shadow-md text-sm shrink-0"
              >
                <Plus size={16} /> Create Custom Tool
              </button>
            </div>
          </div>

          {filteredTools.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-border bg-card p-12 text-center flex flex-col items-center justify-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
                <Terminal size={32} />
              </div>
              <div>
                <h3 className="font-bold text-lg text-foreground">No custom tools configured yet</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                  Create database connectors or API webhooks to allow your AI agents to query production data and run external actions.
                </p>
              </div>
              <button
                onClick={() => navigate("/tools/new")}
                className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground transition rounded-xl text-sm font-semibold"
              >
                Create Custom Tool
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredTools.map((tool) => (
                <div key={tool.id} className="glass-card p-6 flex flex-col justify-between h-60 transition-all duration-200 hover:shadow-md border border-border/50 gap-y-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 bg-muted rounded-xl">
                          {getToolIcon(tool.tool_type)}
                        </div>
                        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          {getToolTypeName(tool.tool_type)}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => navigate(`/tools/new?edit=${tool.id}`)}
                          className="p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground rounded-lg transition"
                          title="Edit tool details"
                        >
                          <Pencil size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(tool.id)}
                          className="p-1.5 hover:bg-red-500/10 text-muted-foreground hover:text-red-500 rounded-lg transition"
                          title="Delete tool"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </div>

                    <div>
                      <h3 className="font-bold text-lg text-foreground truncate">{tool.name}</h3>
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-1.5 leading-relaxed">
                        {tool.tool_type === "api_webhook" && (
                          tool.configuration?.description 
                            ? tool.configuration.description 
                            : (tool.configuration?.method && tool.configuration?.path 
                                ? `Triggers: ${tool.configuration.method} ${tool.configuration.path}` 
                                : "REST API: Not configured")
                        )}
                        {tool.tool_type === "database" && (
                          tool.configuration?.connection_string 
                            ? `SQL Connection to: ${tool.configuration.connection_string.split("@").pop()}` 
                            : "SQL Connection: Not configured"
                        )}
                        {tool.tool_type === "oauth" && (
                          tool.configuration?.provider 
                            ? `OAuth access authorized via ${tool.configuration.provider}` 
                            : "OAuth: Not configured"
                        )}
                        {tool.tool_type === "python_code" && `Custom sandboxed Python code: ${tool.name}`}
                      </p>
                    </div>
                  </div>

                  {/* Unified Card Footer */}
                  <div className="flex items-center gap-2 pt-3.5 border-t border-border/20 mt-auto shrink-0">
                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                      tool.tool_type === "api_webhook" ? "bg-blue-500/10 text-blue-500 border border-blue-500/20" :
                      tool.tool_type === "database" ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20" :
                      tool.tool_type === "oauth" ? "bg-purple-500/10 text-purple-500 border border-purple-500/20" :
                      "bg-indigo-500/10 text-indigo-500 border border-indigo-500/20"
                    }`}>
                      {tool.tool_type === "api_webhook" ? (tool.configuration?.method || "API") :
                       tool.tool_type === "database" ? "SQL" :
                       tool.tool_type === "oauth" ? "OAuth" : "Python"}
                    </span>
                    <span className="text-xs font-mono text-muted-foreground truncate flex-1">
                      {tool.tool_type === "api_webhook" ? (tool.configuration?.path || "Not configured") :
                       tool.tool_type === "database" ? "Read-only sandbox active" :
                       tool.tool_type === "oauth" ? "Authorized application scope" : "E2B VM execution ready"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
