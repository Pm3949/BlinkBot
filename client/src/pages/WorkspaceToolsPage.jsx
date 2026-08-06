import React, { useState, useEffect } from "react";
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
  Activity 
} from "lucide-react";
import { useUIStore } from "../store/useUIStore";
import { 
  getWorkspaceTools, 
  createWorkspaceTool, 
  updateWorkspaceTool, 
  deleteWorkspaceTool 
} from "../services/workspaceToolsService";
import { toast } from "sonner";
import LoadingSkeleton from "../components/shared/LoadingSkeleton";

// ==========================================
// BOILERPLATE TEMPLATE
// ==========================================

const PYTHON_BOILERPLATE = `from langchain_core.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Describe what this tool does so the agent knows when to use it."""
    # Write your custom logic here
    return "Result"`;

// ==========================================
// FORM SUB-COMPONENTS
// ==========================================

function ApiConfigurationForm({
  method, setMethod,
  baseUrl, setBaseUrl,
  path, setPath,
  apiKey, setApiKey,
  headers, setHeaders,
  description, setDescription,
  payloadFormat, setPayloadFormat,
  expectedOutput, setExpectedOutput,
  requiresApproval, setRequiresApproval
}) {
  return (
    <div className="space-y-4 pt-2 border-t border-border/40">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="sm:col-span-1">
          <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">HTTP Method</label>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
            <option value="PATCH">PATCH</option>
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Base URL</label>
          <input
            required
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="https://api.stripe.com"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Endpoint Path</label>
        <input
          required
          value={path}
          onChange={(e) => setPath(e.target.value)}
          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="/v1/charges"
        />
      </div>

      <div>
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">API Key / Token (Header Auth)</label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="Bearer sk_live_..."
        />
      </div>

      <div>
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Custom Headers (JSON)</label>
        <textarea
          value={headers}
          onChange={(e) => setHeaders(e.target.value)}
          rows={3}
          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder='{ "Content-Type": "application/json" }'
        />
      </div>

      <div>
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Tool Description (Instruction for LLM)</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="Use this tool to query billing charges. E.g., 'Allows retrieving Stripe billing logs'."
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Payload JSON Format</label>
          <input
            value={payloadFormat}
            onChange={(e) => setPayloadFormat(e.target.value)}
            className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder='{"limit": 10}'
          />
        </div>
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Expected JSON Response</label>
          <input
            value={expectedOutput}
            onChange={(e) => setExpectedOutput(e.target.value)}
            className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder='{"data": []}'
          />
        </div>
      </div>

      <div className="flex items-center gap-2 pt-2">
        <input
          type="checkbox"
          id="requiresApproval"
          checked={requiresApproval}
          onChange={(e) => setRequiresApproval(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary/30"
        />
        <label htmlFor="requiresApproval" className="text-xs font-semibold text-foreground select-none cursor-pointer">
          Require human approval in chat before execution (Human-in-the-loop)
        </label>
      </div>
    </div>
  );
}

function DatabaseConfigurationForm({ connectionString, setConnectionString }) {
  return (
    <div className="space-y-4 pt-2 border-t border-border/40">
      <div>
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">PostgreSQL Database Connection URI</label>
        <input
          required
          type="password"
          value={connectionString}
          onChange={(e) => setConnectionString(e.target.value)}
          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="postgresql://user:password@localhost:5432/db_name"
        />
        <p className="text-[10px] text-muted-foreground mt-1">
          Credentials are stored securely. Agents will have read-only SQL queries access to tables.
        </p>
      </div>
    </div>
  );
}

function OAuthConfigurationForm({ oauthProvider, setOauthProvider }) {
  return (
    <div className="space-y-4 pt-2 border-t border-border/40">
      <div>
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">OAuth Application Provider</label>
        <select
          value={oauthProvider}
          onChange={(e) => setOauthProvider(e.target.value)}
          className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="github">GitHub</option>
          <option value="slack">Slack Workspace</option>
        </select>
        <p className="text-[10px] text-muted-foreground mt-1.5 flex items-center gap-1">
          <AlertCircle size={12} className="text-amber-500 shrink-0" />
          Make sure users connect their OAuth tokens in their main dashboard account integrations.
        </p>
      </div>
    </div>
  );
}

function PythonConfigurationForm({ codeContent, setCodeContent }) {
  return (
    <div className="space-y-4 pt-2 border-t border-border/40">
      <div>
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Python Tool Script</label>
        <textarea
          required
          value={codeContent}
          onChange={(e) => setCodeContent(e.target.value)}
          rows={12}
          className="w-full border border-border rounded-xl p-4 bg-background text-foreground text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary leading-relaxed whitespace-pre"
          placeholder="def my_tool(): ..."
        />
        <div className="mt-2.5 p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs flex items-center gap-2">
          <AlertCircle size={14} className="shrink-0" />
          <span>Code runs in a secure, isolated cloud sandbox. System and network libraries are disabled.</span>
        </div>
      </div>
    </div>
  );
}

// ==========================================
// MAIN COMPONENT
// ==========================================

export default function WorkspaceToolsPage() {
  const activeWorkspaceId = useUIStore((state) => state.activeWorkspaceId);
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTool, setEditingTool] = useState(null);

  // Progressive selection state
  const [selectedToolType, setSelectedToolType] = useState(null); // 'api_webhook', 'database', 'oauth', 'python_code' or null

  // Form State
  const [toolName, setToolName] = useState("");
  const [toolType, setToolType] = useState("api_webhook");
  
  // API Webhook config
  const [baseUrl, setBaseUrl] = useState("");
  const [path, setPath] = useState("");
  const [method, setMethod] = useState("GET");
  const [apiKey, setApiKey] = useState("");
  const [headers, setHeaders] = useState("{}");
  const [description, setDescription] = useState("");
  const [payloadFormat, setPayloadFormat] = useState("");
  const [expectedOutput, setExpectedOutput] = useState("");
  const [requiresApproval, setRequiresApproval] = useState(false);

  // Database config
  const [connectionString, setConnectionString] = useState("");

  // OAuth config
  const [oauthProvider, setOauthProvider] = useState("github"); // 'github', 'slack'

  // Python Script config
  const [codeContent, setCodeContent] = useState("");

  const fetchTools = async () => {
    if (!activeWorkspaceId) return;
    setLoading(true);
    try {
      const data = await getWorkspaceTools(activeWorkspaceId);
      setTools(data);
    } catch (e) {
      toast.error("Failed to load workspace tools");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTools();
  }, [activeWorkspaceId]);

  const resetForm = () => {
    setEditingTool(null);
    setSelectedToolType(null);
    setToolName("");
    setToolType("api_webhook");
    setBaseUrl("");
    setPath("");
    setMethod("GET");
    setApiKey("");
    setHeaders("{}");
    setDescription("");
    setPayloadFormat("");
    setExpectedOutput("");
    setRequiresApproval(false);
    setConnectionString("");
    setOauthProvider("github");
    setCodeContent(PYTHON_BOILERPLATE);
  };

  const handleOpenCreateModal = () => {
    resetForm();
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (tool) => {
    setEditingTool(tool);
    setToolName(tool.name);
    setToolType(tool.tool_type);
    setSelectedToolType(tool.tool_type);
    
    const config = tool.configuration || {};
    if (tool.tool_type === "api_webhook") {
      setBaseUrl(config.base_url || "");
      setPath(config.path || "");
      setMethod(config.method || "GET");
      setApiKey(config.api_key || "");
      setHeaders(typeof config.headers === "object" ? JSON.stringify(config.headers, null, 2) : config.headers || "{}");
      setDescription(config.description || "");
      setPayloadFormat(config.payload_format || "");
      setExpectedOutput(config.expected_output || "");
      setRequiresApproval(config.requires_approval || false);
    } else if (tool.tool_type === "database") {
      setConnectionString(config.connection_string || "");
    } else if (tool.tool_type === "oauth") {
      setOauthProvider(config.provider || "github");
    } else if (tool.tool_type === "python_code") {
      setCodeContent(tool.code_content || "");
    }
    
    setIsModalOpen(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!toolName.trim()) {
      toast.error("Tool name is required");
      return;
    }

    // Format configuration based on tool type
    let configuration = {};
    if (toolType === "api_webhook") {
      let parsedHeaders = {};
      try {
        parsedHeaders = JSON.parse(headers);
      } catch (err) {
        toast.error("Headers must be valid JSON");
        return;
      }
      configuration = {
        base_url: baseUrl,
        path: path,
        method: method,
        api_key: apiKey,
        headers: parsedHeaders,
        description: description,
        payload_format: payloadFormat,
        expected_output: expectedOutput,
        requires_approval: requiresApproval
      };
    } else if (toolType === "database") {
      if (!connectionString.trim()) {
        toast.error("Database connection URI is required");
        return;
      }
      configuration = { connection_string: connectionString };
    } else if (toolType === "oauth") {
      configuration = { provider: oauthProvider };
    } else if (toolType === "python_code") {
      configuration = { description: "Custom sandboxed Python code tool execution." };
    }

    try {
      if (editingTool) {
        await updateWorkspaceTool(activeWorkspaceId, editingTool.id, {
          name: toolName,
          configuration,
          code_content: toolType === "python_code" ? codeContent : null
        });
        toast.success("Tool updated successfully");
      } else {
        await createWorkspaceTool(activeWorkspaceId, {
          name: toolName,
          tool_type: toolType,
          configuration,
          code_content: toolType === "python_code" ? codeContent : null
        });
        toast.success("Tool created successfully");
      }
      setIsModalOpen(false);
      fetchTools();
    } catch (err) {
      toast.error(err.message || "Failed to save tool");
    }
  };

  const handleDelete = async (toolId) => {
    if (!confirm("Are you sure you want to delete this tool? Any agents subscribed to this tool will lose access.")) {
      return;
    }
    try {
      await deleteWorkspaceTool(activeWorkspaceId, toolId);
      toast.success("Tool deleted successfully");
      fetchTools();
    } catch (err) {
      toast.error(err.message || "Failed to delete tool");
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

  if (loading) {
    return <LoadingSkeleton count={3} className="h-40 mb-4" />;
  }

  return (
    <div className="max-w-6xl space-y-8 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Workspace Tool Library</h1>
          <p className="text-muted-foreground mt-1">
            Configure integrations, API hooks, and database connectors globally, and attach them to any Agent in this workspace.
          </p>
        </div>
        <button
          onClick={handleOpenCreateModal}
          className="px-5 py-3 btn-primary rounded-xl flex items-center gap-2 font-semibold shadow-md self-start"
        >
          <Plus size={18} /> Create Workspace Tool
        </button>
      </div>

      {/* Grid of Tools */}
      {tools.length === 0 ? (
        <div className="rounded-3xl border-2 border-dashed border-border bg-card p-12 text-center flex flex-col items-center justify-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
            <Terminal size={32} />
          </div>
          <div>
            <h3 className="font-bold text-lg text-foreground">No tools configured yet</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm">
              Create database connectors or API webhooks to allow your AI agents to query production data and run external actions.
            </p>
          </div>
          <button
            onClick={handleOpenCreateModal}
            className="px-4 py-2 bg-muted hover:bg-muted/80 text-foreground transition rounded-xl text-sm font-semibold"
          >
            Create Your First Tool
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tools.map((tool) => (
            <div key={tool.id} className="glass-card p-6 flex flex-col justify-between h-56 transition-all duration-200 hover:shadow-md border border-border/50">
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
                  {tool.is_system ? (
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                      System
                    </span>
                  ) : (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleOpenEditModal(tool)}
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
                  )}
                </div>

                <div>
                  <h3 className="font-bold text-base text-foreground truncate">{tool.name}</h3>
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1 leading-relaxed">
                    {tool.tool_type === "api_webhook" && (tool.configuration?.description || `Triggers: ${tool.configuration?.method} ${tool.configuration?.path}`)}
                    {tool.tool_type === "database" && `SQL Connection to: ${tool.configuration?.connection_string?.split("@")?.pop()}`}
                    {tool.tool_type === "oauth" && `OAuth access authorized via ${tool.configuration?.provider}`}
                    {tool.tool_type === "python_code" && `Custom sandboxed Python code: ${tool.name}`}
                  </p>
                </div>
              </div>

              {tool.tool_type === "api_webhook" && (
                <div className="flex items-center gap-2 pt-4 border-t border-border/40">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20">
                    {tool.configuration?.method}
                  </span>
                  <span className="text-xs font-mono text-muted-foreground truncate flex-1">
                    {tool.configuration?.path}
                  </span>
                </div>
              )}
              {tool.tool_type === "database" && (
                <div className="flex items-center gap-2 pt-4 border-t border-border/40">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    SQL
                  </span>
                  <span className="text-xs font-mono text-muted-foreground truncate flex-1">
                    Read-only sandbox enabled
                  </span>
                </div>
              )}
              {tool.tool_type === "oauth" && (
                <div className="flex items-center gap-2 pt-4 border-t border-border/40">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-purple-500/10 text-purple-500 border border-purple-500/20">
                    Active
                  </span>
                  <span className="text-xs font-mono text-muted-foreground truncate flex-1">
                    Authorized app scope
                  </span>
                </div>
              )}
              {tool.tool_type === "python_code" && (
                <div className="flex items-center gap-2 pt-4 border-t border-border/40">
                  <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-500 border border-indigo-500/20">
                    PYTHON
                  </span>
                  <span className="text-xs font-mono text-muted-foreground truncate flex-1">
                    E2B VM execution ready
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Creation/Edit Modal Dialog */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4 animate-in fade-in duration-200">
          <div className="bg-card border border-border p-8 rounded-3xl max-w-2xl w-full shadow-2xl space-y-6 max-h-[90vh] overflow-y-auto">
            <div>
              <h3 className="font-bold text-xl text-foreground">
                {editingTool ? "Edit Workspace Tool" : "Create Workspace Tool"}
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Configure connection settings. Once saved, this tool will be available to all agents inside the workspace.
              </p>
            </div>

            {selectedToolType === null ? (
              <div className="space-y-4">
                <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-1">
                  Select Integration Type
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* Card 1: REST API Webhook */}
                  <div
                    onClick={() => {
                      setSelectedToolType("api_webhook");
                      setToolType("api_webhook");
                    }}
                    className="border border-border/80 bg-background/50 hover:bg-card/85 hover:border-primary/60 rounded-2xl p-4 cursor-pointer transition duration-200 flex flex-col items-center text-center gap-3.5 h-full group"
                  >
                    <div className="p-2.5 bg-blue-500/10 text-blue-500 rounded-xl group-hover:scale-110 transition-transform duration-200">
                      <Webhook size={24} />
                    </div>
                    <div>
                      <h4 className="font-bold text-xs text-foreground">REST API Webhook</h4>
                      <p className="text-[10px] text-muted-foreground mt-1.5 leading-relaxed">
                        Connect external APIs with custom headers and payloads.
                      </p>
                    </div>
                  </div>

                  {/* Card 2: Database Connector */}
                  <div
                    onClick={() => {
                      setSelectedToolType("database");
                      setToolType("database");
                    }}
                    className="border border-border/80 bg-background/50 hover:bg-card/85 hover:border-emerald-500/60 rounded-2xl p-4 cursor-pointer transition duration-200 flex flex-col items-center text-center gap-3.5 h-full group"
                  >
                    <div className="p-2.5 bg-emerald-500/10 text-emerald-500 rounded-xl group-hover:scale-110 transition-transform duration-200">
                      <DbIcon size={24} />
                    </div>
                    <div>
                      <h4 className="font-bold text-xs text-foreground">Database Connector</h4>
                      <p className="text-[10px] text-muted-foreground mt-1.5 leading-relaxed">
                        Give your agent secure SQL access to a database.
                      </p>
                    </div>
                  </div>

                  {/* Card 3: App Connector (OAuth) */}
                  <div
                    onClick={() => {
                      setSelectedToolType("oauth");
                      setToolType("oauth");
                    }}
                    className="border border-border/80 bg-background/50 hover:bg-card/85 hover:border-purple-500/60 rounded-2xl p-4 cursor-pointer transition duration-200 flex flex-col items-center text-center gap-3.5 h-full group"
                  >
                    <div className="p-2.5 bg-purple-500/10 text-purple-500 rounded-xl group-hover:scale-110 transition-transform duration-200">
                      <Key size={24} />
                    </div>
                    <div>
                      <h4 className="font-bold text-xs text-foreground">App Connector</h4>
                      <p className="text-[10px] text-muted-foreground mt-1.5 leading-relaxed">
                        Authenticate with services like Slack, GitHub, or Jira.
                      </p>
                    </div>
                  </div>

                  {/* Card 4: Custom Python Script */}
                  <div
                    onClick={() => {
                      setSelectedToolType("python_code");
                      setToolType("python_code");
                    }}
                    className="border border-border/80 bg-background/50 hover:bg-card/85 hover:border-indigo-500/60 rounded-2xl p-4 cursor-pointer transition duration-200 flex flex-col items-center text-center gap-3.5 h-full group"
                  >
                    <div className="p-2.5 bg-indigo-500/10 text-indigo-500 rounded-xl group-hover:scale-110 transition-transform duration-200">
                      <FileCode size={24} />
                    </div>
                    <div>
                      <h4 className="font-bold text-xs text-foreground">Custom Python</h4>
                      <p className="text-[10px] text-muted-foreground mt-1.5 leading-relaxed">
                        Write sandboxed Python script decorated with @tool.
                      </p>
                    </div>
                  </div>
                </div>
                {/* Cancel action */}
                <div className="pt-4 border-t border-border flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-5 py-2.5 bg-muted hover:bg-muted/80 text-foreground transition text-xs font-bold rounded-xl"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSave} className="space-y-5">
                {/* Back to selection (Only show when creating a new tool) */}
                {!editingTool && (
                  <button
                    type="button"
                    onClick={() => setSelectedToolType(null)}
                    className="flex items-center gap-1.5 text-xs font-bold text-primary hover:text-primary/80 transition-colors bg-transparent border-none cursor-pointer self-start"
                  >
                    &larr; Back to tool types
                  </button>
                )}

                {/* Common Name Field */}
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">Tool Name</label>
                  <input
                    required
                    value={toolName}
                    onChange={(e) => setToolName(e.target.value)}
                    className="w-full border border-border rounded-xl p-3 bg-background text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="e.g., Stripe API, Custom Calculator Script"
                  />
                </div>

                {/* Integration Type Display */}
                <div className="bg-muted/30 border border-border/40 p-3 rounded-xl flex items-center gap-2">
                  {getToolIcon(selectedToolType)}
                  <span className="text-xs text-muted-foreground font-semibold">
                    Configuring {getToolTypeName(selectedToolType)}
                  </span>
                </div>

                {/* Sub Forms */}
                {selectedToolType === "api_webhook" && (
                  <ApiConfigurationForm
                    method={method} setMethod={setMethod}
                    baseUrl={baseUrl} setBaseUrl={setBaseUrl}
                    path={path} setPath={setPath}
                    apiKey={apiKey} setApiKey={setApiKey}
                    headers={headers} setHeaders={setHeaders}
                    description={description} setDescription={setDescription}
                    payloadFormat={payloadFormat} setPayloadFormat={setPayloadFormat}
                    expectedOutput={expectedOutput} setExpectedOutput={setExpectedOutput}
                    requiresApproval={requiresApproval} setRequiresApproval={setRequiresApproval}
                  />
                )}

                {selectedToolType === "database" && (
                  <DatabaseConfigurationForm
                    connectionString={connectionString}
                    setConnectionString={setConnectionString}
                  />
                )}

                {selectedToolType === "oauth" && (
                  <OAuthConfigurationForm
                    oauthProvider={oauthProvider}
                    setOauthProvider={setOauthProvider}
                  />
                )}

                {selectedToolType === "python_code" && (
                  <PythonConfigurationForm
                    codeContent={codeContent}
                    setCodeContent={setCodeContent}
                  />
                )}

                {/* Action Buttons */}
                <div className="pt-4 border-t border-border flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-5 py-2.5 bg-muted hover:bg-muted/80 text-foreground transition text-xs font-bold rounded-xl"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2.5 btn-primary text-white transition text-xs font-bold rounded-xl shadow-md"
                  >
                    {editingTool ? "Save Changes" : "Create Tool"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
